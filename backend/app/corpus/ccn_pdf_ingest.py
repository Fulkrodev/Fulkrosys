"""Sub-lote 1.B.5.2 · ingest PDF normativo a knowledge_documents + knowledge_chunks.

Wrapper sobre el pipeline existing (rd311_embed._l2_normalize +
get_default_embedding_provider) adaptado para PDFs en lugar de HTML.

NO migra rd311_ingest.py (mantiene scope HTML RD-311).

Catalogo embebido: 14 docs del batch 1.B.5.2 (CCN-STIC 800-808 + UE DORA/NIS2/
RGPD/eIDAS + AEPD gestion-riesgo+EIPD). Sector aplicacion por defecto
['publico','privado'] (LECCION-OPS-024) excepto DORA solo 'privado' (sector
financiero ambito).

Parser primary: pdfplumber 0.11.9. Fallback: pypdf 6.10.2 si pdfplumber falla.
Chunking: paragraph-based · target 800-1200 chars · respeta saltos de seccion.
Embedding: FastEmbed multilingual-e5-large 1024 dims + L2 norm.

Usage:
    PYTHONPATH=. .venv/bin/python -m backend.app.corpus.ccn_pdf_ingest --all
    PYTHONPATH=. .venv/bin/python -m backend.app.corpus.ccn_pdf_ingest --only CCN-STIC-802
    PYTHONPATH=. .venv/bin/python -m backend.app.corpus.ccn_pdf_ingest --all --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

# Carga del `.env` de la raíz del repo. El helper vive en rd311_embed para no
# duplicarlo (OPS-026 DRY) y deriva la raíz del propio fichero, en lugar de
# cablear la ruta absoluta de una máquina concreta. Tiene que ejecutarse ANTES
# de importar el provider de embeddings y de crear el engine.
from backend.app.corpus.rd311_embed import load_repo_dotenv

load_repo_dotenv()

import os

import pdfplumber
import pypdf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.corpus.rd311_embed import (
    BATCH_SIZE,
    E5_PASSAGE_PREFIX,
    _l2_normalize,
)
from backend.app.core.ai.embeddings import get_default_embedding_provider
from backend.app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSource,
)


logger = logging.getLogger(__name__)


# Raíz del repo por traversal desde este fichero (mismo patrón que
# backend/app/startup_checks.py:22): backend/app/corpus/ccn_pdf_ingest.py →
# parents[3] == raíz del repo.
REPO_ROOT = Path(__file__).resolve().parents[3]
# Directorio de los PDF normativos. NO están versionados en el repo (son
# descargas manuales), así que se admite override por entorno para apuntar a un
# caché fuera del árbol: FULKRO_CORPUS_PDF_DIR.
PDF_ROOT = Path(
    os.environ.get("FULKRO_CORPUS_PDF_DIR")
    or (REPO_ROOT / "_incoming" / "corpus_cache" / "manual")
)
# Manifiesto de salida de la ingesta. Override: FULKRO_CORPUS_MANIFEST.
MANIFEST_PATH = Path(
    os.environ.get("FULKRO_CORPUS_MANIFEST")
    or (REPO_ROOT / "progress" / "fulkro-1.0" / "corpus_manifest.json")
)

CHUNK_TARGET_CHARS = 1000
CHUNK_MIN_CHARS = 300

Category = Literal["ccn_stic", "eu", "aepd"]


@dataclass
class CorpusBatchEntry:
    """Una entrada del catalogo embebido del batch 1.B.5.2."""

    code: str
    title: str
    publisher: str
    category: Category
    pdf_relative: str  # path bajo PDF_ROOT
    sector_aplicacion: list[str]
    version_label: str
    source_url: str
    publication_date: datetime | None = None
    measure_hints: list[str] = field(default_factory=list)


# Catalogo del batch 1.B.5.2 · 14 PDFs canonicos.
CORPUS_BATCH_1B5_2: list[CorpusBatchEntry] = [
    CorpusBatchEntry(
        code="CCN-STIC-800",
        title="CCN-STIC-800 · Glosario de terminos y abreviaturas ENS",
        publisher="CCN - Centro Criptologico Nacional",
        category="ccn_stic",
        pdf_relative="ccn/stic_serie_800/ccn_stic_800_glosario.pdf",
        sector_aplicacion=["publico", "privado"],
        version_label="2011-03",
        source_url="https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
    ),
    CorpusBatchEntry(
        code="CCN-STIC-801",
        title="CCN-STIC-801 · Responsabilidades y funciones ENS",
        publisher="CCN - Centro Criptologico Nacional",
        category="ccn_stic",
        pdf_relative="ccn/stic_serie_800/ccn_stic_801_responsabilidades.pdf",
        sector_aplicacion=["publico", "privado"],
        version_label="2025-06-17",
        source_url="https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
        measure_hints=["org.2", "org.3", "org.4"],
    ),
    CorpusBatchEntry(
        code="CCN-STIC-802",
        title="CCN-STIC-802 · Auditoria del ENS",
        publisher="CCN - Centro Criptologico Nacional",
        category="ccn_stic",
        pdf_relative="ccn/stic_serie_800/ccn_stic_802_auditoria.pdf",
        sector_aplicacion=["publico", "privado"],
        version_label="2025-06-17",
        source_url="https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
        measure_hints=["mp.aud.1", "mp.aud.2", "mp.aud.3", "mp.aud.4"],
    ),
    CorpusBatchEntry(
        code="CCN-STIC-803",
        title="CCN-STIC-803 · Valoracion de sistemas ENS",
        publisher="CCN - Centro Criptologico Nacional",
        category="ccn_stic",
        pdf_relative="ccn/stic_serie_800/ccn_stic_803_valoracion.pdf",
        sector_aplicacion=["publico", "privado"],
        version_label="2025-06-17",
        source_url="https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
    ),
    CorpusBatchEntry(
        code="CCN-STIC-804",
        title="CCN-STIC-804 · Medidas de implantacion ENS",
        publisher="CCN - Centro Criptologico Nacional",
        category="ccn_stic",
        pdf_relative="ccn/stic_serie_800/ccn_stic_804_medidas.pdf",
        sector_aplicacion=["publico", "privado"],
        version_label="2010-03",
        source_url="https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
    ),
    CorpusBatchEntry(
        code="CCN-STIC-805",
        title="CCN-STIC-805 · Politica de Seguridad de la Informacion ENS",
        publisher="CCN - Centro Criptologico Nacional",
        category="ccn_stic",
        pdf_relative="ccn/stic_serie_800/ccn_stic_805_politica.pdf",
        sector_aplicacion=["publico", "privado"],
        version_label="2025-06-17",
        source_url="https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
        measure_hints=["org.1"],
    ),
    CorpusBatchEntry(
        code="CCN-STIC-806",
        title="CCN-STIC-806 · Plan de Adecuacion ENS",
        publisher="CCN - Centro Criptologico Nacional",
        category="ccn_stic",
        pdf_relative="ccn/stic_serie_800/ccn_stic_806_plan_adecuacion.pdf",
        sector_aplicacion=["publico", "privado"],
        version_label="2010-08",
        source_url="https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
    ),
    CorpusBatchEntry(
        code="CCN-STIC-807",
        title="CCN-STIC-807 · Criptologia en el ENS",
        publisher="CCN - Centro Criptologico Nacional",
        category="ccn_stic",
        pdf_relative="ccn/stic_serie_800/ccn_stic_807_criptologia.pdf",
        sector_aplicacion=["publico", "privado"],
        version_label="2011-07",
        source_url="https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
        measure_hints=["mp.info.3", "mp.com.2"],
    ),
    CorpusBatchEntry(
        code="CCN-STIC-808",
        title="CCN-STIC-808 · Verificacion del cumplimiento ENS",
        publisher="CCN - Centro Criptologico Nacional",
        category="ccn_stic",
        pdf_relative="ccn/stic_serie_800/ccn_stic_808_verificacion.pdf",
        sector_aplicacion=["publico", "privado"],
        version_label="2025-06-17",
        source_url="https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
    ),
    CorpusBatchEntry(
        code="UE-DORA",
        title="Reglamento (UE) 2022/2554 (DORA) · Resiliencia operativa digital sector financiero",
        publisher="Parlamento Europeo y Consejo de la UE",
        category="eu",
        pdf_relative="eur_lex/dora_2022_2554.pdf",
        sector_aplicacion=["privado"],
        version_label="2022-12-14",
        source_url="https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554",
        publication_date=datetime(2022, 12, 14, tzinfo=timezone.utc),
        measure_hints=["op.cont.1", "op.cont.2", "op.ext.2"],
    ),
    CorpusBatchEntry(
        code="UE-NIS2",
        title="Directiva (UE) 2022/2555 (NIS2) · Seguridad redes y sistemas informacion",
        publisher="Parlamento Europeo y Consejo de la UE",
        category="eu",
        pdf_relative="eur_lex/nis2_2022_2555.pdf",
        sector_aplicacion=["publico", "privado"],
        version_label="2022-12-14",
        source_url="https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022L2555",
        publication_date=datetime(2022, 12, 14, tzinfo=timezone.utc),
        measure_hints=["op.exp.7", "op.mon.3"],
    ),
    CorpusBatchEntry(
        code="UE-RGPD",
        title="Reglamento (UE) 2016/679 (RGPD) · Proteccion de datos personales",
        publisher="Parlamento Europeo y Consejo de la UE",
        category="eu",
        pdf_relative="eur_lex/rgpd_2016_679.pdf",
        sector_aplicacion=["publico", "privado"],
        version_label="2016-04-27",
        source_url="https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32016R0679",
        publication_date=datetime(2016, 4, 27, tzinfo=timezone.utc),
    ),
    CorpusBatchEntry(
        code="UE-EIDAS",
        title="Reglamento (UE) 910/2014 (eIDAS) · Identificacion electronica y servicios de confianza",
        publisher="Parlamento Europeo y Consejo de la UE",
        category="eu",
        pdf_relative="eur_lex/eidas_910_2014.pdf",
        sector_aplicacion=["publico", "privado"],
        version_label="2014-07-23",
        source_url="https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014R0910",
        publication_date=datetime(2014, 7, 23, tzinfo=timezone.utc),
        measure_hints=["mp.info.4", "mp.info.5"],
    ),
    CorpusBatchEntry(
        code="AEPD-RIESGO-EIPD",
        title="Guia AEPD · Gestion de riesgo y evaluacion de impacto en tratamientos de datos personales",
        publisher="AEPD - Agencia Espanola de Proteccion de Datos",
        category="aepd",
        pdf_relative="aepd/gestion-riesgo-y-evaluacion-impacto-en-tratamientos-datos-personales.pdf",
        sector_aplicacion=["publico", "privado"],
        version_label="2021-06",
        source_url="https://www.aepd.es/guias/gestion-riesgo-y-evaluacion-impacto-en-tratamientos-datos-personales.pdf",
    ),
]


# ---------------------------------------------------------------------------
# PDF parsing
# ---------------------------------------------------------------------------

HEADING_PATTERNS = [
    re.compile(r"^\s*(Artículo|Articulo|Article|Art\.)\s+\d+", re.IGNORECASE),
    re.compile(r"^\s*(Capítulo|Capitulo|Chapter|Cap\.)\s+[IVX0-9]+", re.IGNORECASE),
    re.compile(r"^\s*(Anexo|Annex)\s+[IVX0-9A-Z]+", re.IGNORECASE),
    re.compile(r"^\s*(Sección|Seccion|Section)\s+[IVX0-9]+", re.IGNORECASE),
    re.compile(r"^\s*\d+(\.\d+){0,3}\s+[A-ZÁÉÍÓÚÑ]"),
]

MEASURE_CODE_RE = re.compile(
    r"\b(org|op|mp)\.[a-z]+(?:\.\d+)?\b", re.IGNORECASE
)
ARTICLE_REF_RE = re.compile(r"\b(?:Art\.|Articulo|Artículo|Article)\s+(\d+)", re.IGNORECASE)


def _extract_pdf_text(pdf_path: Path) -> list[tuple[int, str]]:
    """Extract text per page. Returns list of (page_number, text).

    Uses pdfplumber primary; falls back to pypdf if pdfplumber raises.
    """
    pages: list[tuple[int, str]] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append((i, text))
        return pages
    except Exception as exc:
        logger.warning("pdfplumber failed for %s: %s · fallback pypdf", pdf_path.name, exc)

    reader = pypdf.PdfReader(str(pdf_path))
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append((i, text))
    return pages


def _detect_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return False
    return any(p.match(stripped) for p in HEADING_PATTERNS)


@dataclass
class PdfChunk:
    chunk_index: int
    content: str
    page_number: int
    heading_path: str | None
    measure_code: str | None
    article_ref: str | None


def _chunk_pdf_text(pages: list[tuple[int, str]]) -> list[PdfChunk]:
    """Paragraph-based chunking · target ~1000 chars · respeta headings.

    Acumula parrafos hasta CHUNK_TARGET_CHARS. Cierra chunk al detectar
    heading o tras alcanzar el limite. Conserva page_number del inicio
    del chunk y heading_path del ultimo heading visto.
    """
    chunks: list[PdfChunk] = []
    buffer: list[str] = []
    buffer_len = 0
    current_heading: str | None = None
    chunk_page: int | None = None
    chunk_index = 0

    def flush():
        nonlocal buffer, buffer_len, chunk_page, chunk_index
        if not buffer:
            return
        text = "\n".join(buffer).strip()
        if len(text) < CHUNK_MIN_CHARS and chunks:
            # Append to previous chunk if too small
            chunks[-1] = PdfChunk(
                chunk_index=chunks[-1].chunk_index,
                content=(chunks[-1].content + "\n\n" + text).strip(),
                page_number=chunks[-1].page_number,
                heading_path=chunks[-1].heading_path,
                measure_code=chunks[-1].measure_code,
                article_ref=chunks[-1].article_ref,
            )
        elif len(text) >= 80:
            measure = None
            m = MEASURE_CODE_RE.search(text)
            if m:
                measure = m.group(0).lower()
            article = None
            am = ARTICLE_REF_RE.search(text)
            if am:
                article = am.group(1)
            chunks.append(PdfChunk(
                chunk_index=chunk_index,
                content=text,
                page_number=chunk_page or 1,
                heading_path=current_heading,
                measure_code=measure,
                article_ref=article,
            ))
            chunk_index += 1
        buffer = []
        buffer_len = 0
        chunk_page = None

    for page_num, page_text in pages:
        for raw_line in page_text.splitlines():
            line = raw_line.rstrip()
            if not line.strip():
                # Blank line: paragraph boundary; flush if buffer is big enough
                if buffer_len >= CHUNK_TARGET_CHARS:
                    flush()
                continue
            if _detect_heading(line):
                flush()
                current_heading = line.strip()[:200]
                continue
            if chunk_page is None:
                chunk_page = page_num
            buffer.append(line)
            buffer_len += len(line) + 1
            if buffer_len >= CHUNK_TARGET_CHARS * 1.5:
                flush()

    flush()
    return chunks


# ---------------------------------------------------------------------------
# Ingest pipeline
# ---------------------------------------------------------------------------

async def _delete_existing_source(session: AsyncSession, code: str) -> None:
    existing = await session.execute(
        select(KnowledgeSource).where(KnowledgeSource.code == code)
    )
    src = existing.scalar_one_or_none()
    if src is not None:
        logger.info("Deleting existing source %s (id=%s)", code, src.id)
        await session.delete(src)
        await session.flush()


async def ingest_one(
    session: AsyncSession,
    entry: CorpusBatchEntry,
    dry_run: bool = False,
) -> dict:
    pdf_path = PDF_ROOT / entry.pdf_relative
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF no encontrado: {pdf_path}. Los PDF normativos no están "
            "versionados en el repo; descárgalos a ese directorio o apunta "
            "FULKRO_CORPUS_PDF_DIR a donde los tengas."
        )

    raw = pdf_path.read_bytes()
    content_hash = hashlib.sha256(raw).hexdigest()

    pages = _extract_pdf_text(pdf_path)
    chunks = _chunk_pdf_text(pages)

    logger.info(
        "[%s] extracted %d pages → %d chunks (sha256=%s)",
        entry.code, len(pages), len(chunks), content_hash[:12],
    )

    if dry_run:
        return {
            "code": entry.code,
            "pages": len(pages),
            "chunks": len(chunks),
            "sha256": content_hash,
            "dry_run": True,
        }

    await _delete_existing_source(session, entry.code)

    source = KnowledgeSource(
        code=entry.code,
        title=entry.title,
        publisher=entry.publisher,
        version=entry.version_label,
        publication_date=entry.publication_date,
        source_url=entry.source_url,
        language="es",
        metadata_={
            "batch": "1.B.5.2",
            "category": entry.category,
            "measure_hints": entry.measure_hints,
        },
    )
    session.add(source)
    await session.flush()

    doc = KnowledgeDocument(
        source_id=source.id,
        title=entry.title,
        content_hash=content_hash,
        mime_type="application/pdf",
        chunk_count=len(chunks),
        sector_aplicacion=entry.sector_aplicacion,
        version_label=entry.version_label,
        metadata_={
            "parser": "pdfplumber+pypdf",
            "category": entry.category,
            "pdf_relative": entry.pdf_relative,
            "minio_object_key": f"corpus/{entry.category}/{Path(entry.pdf_relative).name}",
            "pages": len(pages),
        },
    )
    session.add(doc)
    await session.flush()

    # Embed in batches
    provider = get_default_embedding_provider()
    chunk_objs: list[KnowledgeChunk] = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [E5_PASSAGE_PREFIX + c.content for c in batch]
        raw_embeddings = provider.embed_documents(texts)
        for pc, raw_emb in zip(batch, raw_embeddings):
            emb = _l2_normalize(raw_emb)
            if len(emb) != 1024:
                raise ValueError(f"[{entry.code}] chunk {pc.chunk_index} got {len(emb)} dims")
            chunk_objs.append(KnowledgeChunk(
                document_id=doc.id,
                chunk_index=pc.chunk_index,
                heading_path=pc.heading_path,
                article_ref=pc.article_ref,
                measure_code=pc.measure_code,
                content=pc.content,
                seccion=pc.heading_path[:255] if pc.heading_path else None,
                embedding=emb,
                token_count=len(pc.content.split()),
                metadata_extra={
                    "page_number": pc.page_number,
                    "source_code": entry.code,
                    "category": entry.category,
                },
            ))

    session.add_all(chunk_objs)
    await session.flush()
    await session.commit()

    return {
        "code": entry.code,
        "source_id": str(source.id),
        "document_id": str(doc.id),
        "pages": len(pages),
        "chunks": len(chunk_objs),
        "sha256": content_hash,
        "sector_aplicacion": entry.sector_aplicacion,
        "version_label": entry.version_label,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

async def main_async(args) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    selected: list[CorpusBatchEntry]
    if args.only:
        selected = [e for e in CORPUS_BATCH_1B5_2 if e.code == args.only]
        if not selected:
            logger.error("Code no encontrado: %s", args.only)
            return 1
    elif args.all:
        selected = list(CORPUS_BATCH_1B5_2)
    else:
        logger.error("Debe especificar --all o --only CODE")
        return 1

    url = os.environ.get("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL no definido")
        return 1

    engine = create_async_engine(url)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    manifest = {
        "batch": "1.B.5.2",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "results": [],
    }

    started = time.monotonic()
    for entry in selected:
        try:
            async with SessionLocal() as session:
                result = await ingest_one(session, entry, dry_run=args.dry_run)
                manifest["results"].append(result)
                logger.info("[%s] OK · %d chunks", entry.code, result["chunks"])
        except Exception as exc:
            logger.error("[%s] FAIL: %s", entry.code, exc, exc_info=True)
            manifest["results"].append({"code": entry.code, "error": str(exc)})

    await engine.dispose()

    elapsed = time.monotonic() - started
    manifest["elapsed_seconds"] = round(elapsed, 1)
    total_chunks = sum(r.get("chunks", 0) for r in manifest["results"])
    manifest["total_chunks"] = total_chunks

    if not args.dry_run:
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        logger.info("Manifest escrito: %s", MANIFEST_PATH)

    print("\n=== INGEST SUMMARY ===")
    print(f"  docs procesados: {len(selected)}")
    print(f"  total chunks:    {total_chunks}")
    print(f"  elapsed:         {elapsed:.1f}s")
    if args.dry_run:
        print("  (DRY-RUN · sin INSERT)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest 14 PDFs sub-lote 1.B.5.2 a knowledge_*")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true", help="Ingerir todos los 14 docs")
    g.add_argument("--only", type=str, help="Solo este code (ej: CCN-STIC-802)")
    parser.add_argument("--dry-run", action="store_true", help="Parsear sin INSERT")
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    # Como entrypoint el fallo tiene que ser duro y accionable, no silencioso.
    load_repo_dotenv(required=True)
    raise SystemExit(main())
