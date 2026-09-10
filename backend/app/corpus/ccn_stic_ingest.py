"""Ingest + embed de textos markdown propios en el corpus de conocimiento.

OJO CON EL NOMBRE DEL MODULO. Se llama `ccn_stic_ingest` por historia, pero lo
unico que ingiere es un RESUMEN PROPIO de FULKRO
(`data/resumen_fulkro_conformidad_ens.md`). Las guias CCN-STIC de verdad las
ingiere `ccn_pdf_ingest` a partir de los PDF que el operador descarga a
`var/corpus/`, que NO esta versionado — y ahi el editor CCN si es correcto,
porque el texto es suyo.

I5 (campaña auditoría 2026-06-17): el pipeline de corpus era genérico pero no
había un ingestor para las guías CCN-STIC. Este módulo ingesta una guía CCN-STIC
en formato markdown (chunking por secciones) y calcula sus embeddings e5-large,
reutilizando KnowledgeSource/Document/Chunk y el provider de embeddings (mismo
patrón que rd311_ingest + rd311_embed).

Idempotente: borra la KnowledgeSource con el mismo code antes de recrear.

Uso (DB en :5433 + .env cargado):
    python -m backend.app.corpus.ccn_stic_ingest
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Carga del `.env` de la raíz del repo. El helper vive en rd311_embed para no
# duplicarlo (OPS-026 DRY) y deriva la raíz del propio fichero, en lugar de
# cablear la ruta absoluta de una máquina concreta. Tiene que ejecutarse ANTES
# de importar el provider de embeddings y de abrir la sesión de base de datos.
from backend.app.corpus.rd311_embed import load_repo_dotenv

load_repo_dotenv()

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.ai.embeddings import get_default_embedding_provider
from backend.app.database import async_session
from backend.app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSource,
)

logger = logging.getLogger(__name__)

E5_PASSAGE_PREFIX = "passage: "
MAX_CHUNK_CHARS = 1400


def _l2_normalize(vec: list[float]) -> list[float]:
    arr = np.asarray(vec, dtype=np.float32)
    norm = float(np.linalg.norm(arr))
    return arr.tolist() if norm == 0 else (arr / norm).tolist()


def chunk_markdown(md_text: str) -> list[dict]:
    """Trocea markdown en chunks rastreando el heading_path (cadena de títulos).

    - Cada bloque separado por línea en blanco es un párrafo.
    - Los párrafos se empaquetan en chunks de hasta MAX_CHUNK_CHARS bajo el
      último heading visto (jerarquía #/##/###).
    """
    chunks: list[dict] = []
    heading_stack: list[str] = []
    buf: list[str] = []
    idx = 0

    def flush() -> None:
        nonlocal buf, idx
        text = "\n\n".join(buf).strip()
        if text:
            chunks.append({
                "chunk_index": idx,
                "heading_path": " > ".join(heading_stack) or None,
                "content": text,
            })
            idx += 1
        buf = []

    for block in md_text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("#"):
            flush()
            level = len(block) - len(block.lstrip("#"))
            title = block.lstrip("#").strip()
            # recorta la pila al nivel del nuevo header y lo apila
            heading_stack[:] = heading_stack[: level - 1]
            heading_stack.append(title)
            continue
        # acumula; si el chunk supera el tope, corta
        candidate = ("\n\n".join(buf + [block])).strip()
        if buf and len(candidate) > MAX_CHUNK_CHARS:
            flush()
        buf.append(block)
    flush()
    return chunks


async def ingest_ccn_stic_guide(
    session: AsyncSession,
    *,
    code: str,
    title: str,
    md_path: Path,
    publisher: str,
    publication_date: datetime,
    source_url: str | None = None,
    seccion: str = "guideline",
    codigos_heredados: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> dict:
    """Ingesta + embebe una guía en markdown. Idempotente por `code`.

    D-extra (2026-09-10) · qué cambió y por qué
    -------------------------------------------
    `publisher` era una constante cableada: ``"Centro Criptológico Nacional
    (CCN)"``. El único texto que se ingería con esta función es un RESUMEN
    PROPIO de FULKRO versionado en el repositorio, así que el corpus declaraba
    como editor a un tercero para un texto que ese tercero no ha escrito. El
    buscador del copiloto podía citar al CCN con contenido que puede no estar en
    su guía. Es el mismo defecto que D1 —fabricar algo y sellarlo como
    auténtico— una capa más abajo: allí era una respuesta del modelo, aquí es la
    procedencia de una fuente.

    Ahora `publisher` es obligatorio y explícito en cada llamada, y
    `source_url` es opcional: cuando el texto NO sale de esa URL, no se pone,
    y la URL viaja en `metadata` como referencia para consultar el original.

    `seccion` etiqueta los fragmentos para que la recuperación pueda distinguir
    norma de resumen (ver `_SECCION_RESUMEN_PROPIO`).

    `codigos_heredados` borra fuentes de ingestas anteriores con otro `code`,
    para que renombrar una fuente no deje la vieja —con su atribución falsa—
    viva en la base de datos de quien ya la había ingerido.
    """
    raw = md_path.read_bytes()
    content_hash = hashlib.sha256(raw).hexdigest()
    parsed = chunk_markdown(raw.decode("utf-8"))
    if not parsed:
        raise RuntimeError(f"0 chunks parseados de {md_path}")

    # 1. Idempotencia: borrar la fuente previa con el mismo code (cascade) y,
    #    además, las que quedaran de ingestas anteriores bajo otro nombre.
    a_borrar = [code, *codigos_heredados]
    for code_viejo in a_borrar:
        await _borrar_fuente(session, code_viejo)

    # 2. KnowledgeSource + Document
    source = KnowledgeSource(
        code=code,
        title=title,
        publisher=publisher,
        version="2026-04",
        publication_date=publication_date,
        source_url=source_url,
        language="es",
        metadata_=metadata or {},
    )
    session.add(source)
    await session.flush()

    doc = KnowledgeDocument(
        source_id=source.id,
        title=title,
        content_hash=content_hash,
        mime_type="text/markdown",
        chunk_count=len(parsed),
        metadata_={"parser": "ccn_stic_markdown", "chunk_count": len(parsed)},
    )
    session.add(doc)
    await session.flush()

    # 3. Chunks
    chunk_objs = []
    for pc in parsed:
        chunk_objs.append(KnowledgeChunk(
            document_id=doc.id,
            chunk_index=pc["chunk_index"],
            heading_path=pc["heading_path"],
            content=pc["content"],
            seccion=seccion,
            metadata_extra={"source_code": code},
            token_count=len(pc["content"].split()),
        ))
    session.add_all(chunk_objs)
    await session.flush()
    await _embeber(chunk_objs)
    await session.commit()
    return {
        "source_id": str(source.id),
        "document_id": str(doc.id),
        "chunks": len(chunk_objs),
        "content_hash": content_hash,
    }


async def _borrar_fuente(session: AsyncSession, code: str) -> None:
    """Borra una KnowledgeSource y todo lo suyo. No falla si no existe."""
    old = (await session.execute(
        select(KnowledgeSource).where(KnowledgeSource.code == code)
    )).scalar_one_or_none()
    if old is not None:
        # borrar chunks+docs explícito (por si el cascade no cubre)
        docs = (await session.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.source_id == old.id)
        )).scalars().all()
        for d in docs:
            await session.execute(
                delete(KnowledgeChunk).where(KnowledgeChunk.document_id == d.id)
            )
            await session.delete(d)
        await session.delete(old)
        await session.flush()


async def _embeber(chunk_objs: list) -> None:
    """Calcula los embeddings e5-large (prefijo `passage:` + normalizacion L2)."""
    provider = get_default_embedding_provider()
    texts = [E5_PASSAGE_PREFIX + c.content for c in chunk_objs]
    raw_embs = provider.embed_documents(texts)
    for chunk, raw_emb in zip(chunk_objs, raw_embs):
        emb = _l2_normalize(raw_emb)
        if len(emb) != 1024:
            raise ValueError(f"chunk {chunk.chunk_index}: {len(emb)} dims, esperado 1024")
        l2 = math.sqrt(sum(x * x for x in emb))
        if abs(l2 - 1.0) > 0.01:
            raise ValueError(f"chunk {chunk.chunk_index}: L2={l2:.4f}")
        chunk.embedding = emb


# --- 809 concreto -----------------------------------------------------------

#: Editor de todo lo que FULKRO escribe. Lo comprueba
#: `backend/tests/corpus/test_procedencia_corpus.py`: un texto versionado bajo
#: `backend/app/corpus/data/` NO puede declarar editor a un tercero.
PUBLISHER_PROPIO = "FULKRO · Marcos Mata García (resumen propio)"

#: Etiqueta de los fragmentos que NO son norma. La recuperacion puede filtrar
#: por `seccion` (`backend/app/corpus/retrieval.py`), asi que marcarlos aqui es
#: lo que permite distinguir norma de resumen al citar.
SECCION_RESUMEN_PROPIO = "resumen_secundario"

# ── Resumen propio sobre la conformidad con el ENS ──────────────────────────
# ANTES (hasta 2026-09-10) esto se llamaba `CCN_STIC_809`, se titulaba como la
# guia y declaraba `publisher="Centro Criptológico Nacional (CCN)"` con la URL
# oficial como origen del texto. Pero el fichero que ingiere son 103 lineas y
# 14,7 KB escritas aqui, y la guia real son decenas de paginas: no es una copia,
# es un RESUMEN que se presentaba como el original.
#
# El problema no era de derechos de copia; era de PROCEDENCIA. El buscador del
# copiloto podia devolver un fragmento de este resumen citando al CCN como
# editor, con un texto que puede no estar en esa guia. Es exactamente el defecto
# de D1 —fabricar y sellarlo como autentico— una capa mas abajo.
#
# Ahora: titulo que dice lo que es, editor propio, la URL oficial como
# REFERENCIA (en metadata) y no como origen, y los fragmentos etiquetados como
# fuente secundaria. `codigos_heredados` borra la fuente vieja de quien ya la
# hubiera ingerido, para que la atribucion falsa no sobreviva en su base.
RESUMEN_CONFORMIDAD_ENS = {
    "code": "FULKRO_RESUMEN_CONFORMIDAD_ENS",
    "title": (
        "Resumen propio de FULKRO · Declaración y Certificación de conformidad "
        "con el ENS (referencia: guía CCN-STIC-809)"
    ),
    "md_path": (
        Path(__file__).resolve().parent / "data"
        / "resumen_fulkro_conformidad_ens.md"
    ),
    "publisher": PUBLISHER_PROPIO,
    # NO se pone `source_url`: el texto no sale de esa URL. La referencia para
    # consultar el original viaja en metadata, que es lo que es.
    "source_url": None,
    "seccion": SECCION_RESUMEN_PROPIO,
    "codigos_heredados": ("CCN_STIC_809",),
    "publication_date": datetime(2026, 9, 10, tzinfo=timezone.utc),
    "metadata": {
        "tipo_fuente": "resumen_propio",
        "es_norma_oficial": False,
        "resume_a": {
            "guia": "CCN-STIC-809",
            "editor": "Centro Criptológico Nacional (CCN)",
            "url_oficial": (
                "https://www.ccn-cert.cni.es/series-ccn-stic/"
                "800-guia-esquema-nacional-de-seguridad.html"
            ),
            "nota": (
                "Referencia para consultar el original. NO es el origen de este "
                "texto: este texto lo ha escrito FULKRO."
            ),
        },
        "norma_aplicable": {
            "codigo": "RD_311_2022",
            "nota": (
                "La norma oficial y libremente reproducible es el RD 311/2022 "
                "(BOE-A-2022-7191), que se ingiere aparte con `rd311_ingest`."
            ),
        },
    },
}


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    async with async_session() as session:
        result = await ingest_ccn_stic_guide(session, **RESUMEN_CONFORMIDAD_ENS)
    print("\n=== INGEST resumen propio · conformidad ENS ===")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    # Como entrypoint el fallo tiene que ser duro y accionable, no silencioso.
    load_repo_dotenv(required=True)
    asyncio.run(main())
