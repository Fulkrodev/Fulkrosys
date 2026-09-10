"""Ingest RD 311/2022 parsed chunks into the knowledge base.

Creates:
- 1 KnowledgeSource  (code='RD_311_2022')
- 1 KnowledgeDocument
- N KnowledgeChunks   (one per ParsedChunk)

Idempotent: deletes existing source with the same code before re-creating.

Usage (requires running DB on port 5433):
    python -m backend.app.corpus.rd311_ingest
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import async_session
from backend.app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSource,
)
from backend.app.corpus.rd311_parser import parse_rd311

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOURCE_CODE = "RD_311_2022"

# Raíz del repo por traversal desde este fichero (mismo patrón que
# backend/app/startup_checks.py:22): backend/app/corpus/rd311_ingest.py →
# parents[3] == raíz del repo.
_REPO_ROOT = Path(__file__).resolve().parents[3]
# Directorio del corpus descargado. NO está versionado (el HTML consolidado del
# BOE se descarga aparte), así que se admite override: FULKRO_CORPUS_DIR.
CORPUS_DIR = Path(os.environ.get("FULKRO_CORPUS_DIR") or (_REPO_ROOT / "var" / "corpus"))
HTML_PATH = CORPUS_DIR / "boe" / "RD_311_2022_consolidado.html"

SOURCE_METADATA = {
    "boe_id": "BOE-A-2022-7191",
    "tipo": "Real Decreto",
    "numero": "311/2022",
    "fecha": "2022-05-03",
    "titulo_corto": "Esquema Nacional de Seguridad",
}


# ---------------------------------------------------------------------------
# Ingest logic
# ---------------------------------------------------------------------------

async def ingest_rd311(
    session: AsyncSession,
    html_path: Path = HTML_PATH,
) -> dict:
    """Parse and ingest RD 311/2022 into the knowledge base.

    Returns a summary dict with counts.
    """
    # 1. Parse the HTML
    logger.info("Parsing %s ...", html_path)
    chunks = parse_rd311(html_path)
    logger.info("Parsed %d chunks", len(chunks))

    # 2. Compute content hash
    raw = html_path.read_bytes()
    content_hash = hashlib.sha256(raw).hexdigest()

    # 3. Delete existing source (cascade deletes documents and chunks)
    existing = await session.execute(
        select(KnowledgeSource).where(KnowledgeSource.code == SOURCE_CODE)
    )
    old_source = existing.scalar_one_or_none()
    if old_source:
        logger.info("Deleting existing source %s (id=%s)", SOURCE_CODE, old_source.id)
        await session.delete(old_source)
        await session.flush()

    # 3b. Delete legacy RD 311/2022 document (pre-existing, without KnowledgeSource)
    legacy_docs = await session.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.source_id.is_(None),
            KnowledgeDocument.title.ilike("%Rd 311 2022%"),
        )
    )
    for legacy_doc in legacy_docs.scalars().all():
        # Delete associated chunks first
        await session.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id == legacy_doc.id)
        )
        await session.delete(legacy_doc)
        logger.info(
            "Deleted legacy document '%s' (id=%s)",
            legacy_doc.title,
            legacy_doc.id,
        )
    await session.flush()

    # 4. Create KnowledgeSource
    source = KnowledgeSource(
        code=SOURCE_CODE,
        title="Real Decreto 311/2022, de 3 de mayo, por el que se regula "
              "el Esquema Nacional de Seguridad",
        publisher="BOE - Ministerio de Asuntos Económicos y Transformación Digital",
        version="consolidado",
        publication_date=datetime(2022, 5, 4, tzinfo=timezone.utc),
        source_url="https://www.boe.es/buscar/act.php?id=BOE-A-2022-7191",
        language="es",
        metadata_=SOURCE_METADATA,
    )
    session.add(source)
    await session.flush()  # get source.id
    logger.info("Created KnowledgeSource id=%s", source.id)

    # 5. Create KnowledgeDocument · schema consolidado SAN-B.MB-2.2.
    # Datos legacy sin equivalente new (version, fecha_publicacion,
    # contenido_path) viven en metadata JSONB (consultar
    # KnowledgeSource.publication_date para fecha pub estructurada).
    doc = KnowledgeDocument(
        source_id=source.id,
        title="RD 311/2022 - Esquema Nacional de Seguridad (consolidado)",
        content_hash=content_hash,
        mime_type="text/html",
        chunk_count=len(chunks),
        metadata_={
            "parser": "rd311_parser",
            "chunk_count": len(chunks),
            "legacy_version": "consolidado",
            "legacy_publication_date": "2022-05-04",
            "legacy_content_path": str(html_path),
        },
    )
    session.add(doc)
    await session.flush()  # get doc.id
    logger.info("Created KnowledgeDocument id=%s", doc.id)

    # 6. Create KnowledgeChunks
    chunk_objs = []
    for pc in chunks:
        chunk = KnowledgeChunk(
            document_id=doc.id,
            chunk_index=pc.chunk_index,
            heading_path=pc.heading_path,
            article_ref=pc.article_ref,
            measure_code=pc.measure_code,
            content=pc.content,
            seccion=pc.chunk_type,
            metadata_extra={
                "chunk_type": pc.chunk_type,
                **pc.metadata,
            },
            token_count=len(pc.content.split()),  # rough word count
        )
        chunk_objs.append(chunk)

    session.add_all(chunk_objs)
    await session.flush()
    logger.info("Created %d KnowledgeChunks", len(chunk_objs))

    # 7. Commit
    await session.commit()
    logger.info("Ingest complete.")

    return {
        "source_id": str(source.id),
        "document_id": str(doc.id),
        "total_chunks": len(chunk_objs),
        "measure_chunks": sum(1 for c in chunks if c.chunk_type == "measure"),
        "article_chunks": sum(1 for c in chunks if c.chunk_type == "article"),
        "disposition_chunks": sum(1 for c in chunks if c.chunk_type == "disposition"),
        "annex_chunks": sum(1 for c in chunks if c.chunk_type == "annex_intro"),
        "content_hash": content_hash,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    """Run the ingest as a standalone script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not HTML_PATH.exists():
        logger.error("HTML file not found: %s", HTML_PATH)
        logger.error("Run the download script first.")
        return

    async with async_session() as session:
        result = ingest_rd311(session, HTML_PATH)
        summary = await result
        print("\n=== INGEST SUMMARY ===")
        for k, v in summary.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
