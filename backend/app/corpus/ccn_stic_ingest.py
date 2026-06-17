"""Ingest + embed de guías CCN-STIC (markdown) en el corpus de conocimiento.

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
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path("/home/usuario/fulkro/.env"))

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
    source_url: str,
    publication_date: datetime,
    metadata: dict | None = None,
) -> dict:
    """Ingesta + embebe una guía CCN-STIC markdown. Idempotente por `code`."""
    raw = md_path.read_bytes()
    content_hash = hashlib.sha256(raw).hexdigest()
    parsed = chunk_markdown(raw.decode("utf-8"))
    if not parsed:
        raise RuntimeError(f"0 chunks parseados de {md_path}")

    # 1. Idempotencia: borrar source previa con el mismo code (cascade).
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

    # 2. KnowledgeSource + Document
    source = KnowledgeSource(
        code=code,
        title=title,
        publisher="Centro Criptológico Nacional (CCN)",
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
            seccion="guideline",
            metadata_extra={"source_code": code},
            token_count=len(pc["content"].split()),
        ))
    session.add_all(chunk_objs)
    await session.flush()

    # 4. Embeddings e5-large (passage: prefix + L2 normalize)
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

    await session.commit()
    return {
        "source_id": str(source.id),
        "document_id": str(doc.id),
        "chunks": len(chunk_objs),
        "model": provider.model_name,
        "content_hash": content_hash,
    }


# --- 809 concreto -----------------------------------------------------------

CCN_STIC_809 = {
    "code": "CCN_STIC_809",
    "title": (
        "CCN-STIC-809 · Declaración, Certificación y Aprobación Provisional de "
        "conformidad con el ENS y Distintivos de cumplimiento"
    ),
    # Texto curado versionado en el repo (var/corpus está gitignored).
    "md_path": Path(__file__).resolve().parent / "data" / "CCN_STIC_809.md",
    "source_url": "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad.html",
    "publication_date": datetime(2026, 4, 28, tzinfo=timezone.utc),
    "metadata": {"serie": "CCN-STIC", "numero": "809", "edicion": "abril 2026"},
}


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    async with async_session() as session:
        result = await ingest_ccn_stic_guide(session, **CCN_STIC_809)
    print("\n=== INGEST CCN-STIC-809 ===")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
