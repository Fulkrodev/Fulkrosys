"""Calculate embeddings for RD 311/2022 chunks using FastEmbed e5-large.

Processes ONLY chunks from the RD 311/2022 new ingestion (source_id IS NOT NULL,
source.code = 'RD_311_2022'). Does NOT touch the 6196 legacy chunks.

Uses intfloat/multilingual-e5-large via FastEmbed 0.6.1.
Applies 'passage: ' prefix (e5 training convention for documents).
Normalizes L2 to 1.0 (consistency with legacy embeddings).
Idempotent: overwrites existing embeddings on re-run.

Usage:
    python -m backend.app.corpus.rd311_embed
"""
from __future__ import annotations

import asyncio
import logging
import math
import os
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path("/home/usuario/fulkro/.env"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.ai.embeddings import get_default_embedding_provider
from backend.app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSource,
)

logger = logging.getLogger(__name__)

SOURCE_CODE = "RD_311_2022"
BATCH_SIZE = 32
E5_PASSAGE_PREFIX = "passage: "


def _l2_normalize(vec: list[float]) -> list[float]:
    """Normalize vector to L2 norm = 1.0."""
    arr = np.asarray(vec, dtype=np.float32)
    norm = float(np.linalg.norm(arr))
    if norm == 0:
        return arr.tolist()
    return (arr / norm).tolist()


async def embed_rd311_chunks(session: AsyncSession) -> dict:
    """Calculate embeddings for all RD 311/2022 chunks."""
    # 1. Find source
    source_q = await session.execute(
        select(KnowledgeSource).where(KnowledgeSource.code == SOURCE_CODE)
    )
    source = source_q.scalar_one_or_none()
    if source is None:
        raise RuntimeError(
            f"KnowledgeSource '{SOURCE_CODE}' not found. Run rd311_ingest first."
        )

    # 2. Get all chunks for this source's documents
    chunks_q = await session.execute(
        select(KnowledgeChunk)
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .where(KnowledgeDocument.source_id == source.id)
        .order_by(KnowledgeChunk.chunk_index)
    )
    chunks = list(chunks_q.scalars().all())
    total = len(chunks)

    if total == 0:
        return {"error": "No chunks found for RD 311/2022"}

    logger.info("Embedding %d chunks in batches of %d...", total, BATCH_SIZE)

    # 3. Load embedding provider
    provider = get_default_embedding_provider()
    logger.info("Model: %s (%d dims)", provider.model_name, provider.dimensions)

    # 4. Process in batches
    start = time.monotonic()
    processed = 0

    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        # Prefix with 'passage: ' for e5 model convention
        texts = [E5_PASSAGE_PREFIX + (c.content or "") for c in batch]

        # Embed batch (sync call — FastEmbed is sync)
        raw_embeddings = provider.embed_documents(texts)

        for chunk, raw_emb in zip(batch, raw_embeddings):
            # L2 normalize for consistency with legacy
            emb = _l2_normalize(raw_emb)

            # Sanity checks
            if len(emb) != 1024:
                raise ValueError(
                    f"Chunk {chunk.id} got {len(emb)} dims, expected 1024"
                )
            l2 = math.sqrt(sum(x * x for x in emb))
            if abs(l2 - 1.0) > 0.01:
                raise ValueError(
                    f"Chunk {chunk.id} L2={l2:.4f}, expected ~1.0 after normalization"
                )

            chunk.embedding = emb

        processed += len(batch)
        logger.info("  [%d/%d] batch done", processed, total)
        await session.flush()

    await session.commit()
    elapsed = time.monotonic() - start

    return {
        "source_id": str(source.id),
        "chunks_embedded": processed,
        "model": provider.model_name,
        "dims": provider.dimensions,
        "elapsed_seconds": round(elapsed, 1),
    }


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    engine = create_async_engine(os.getenv("DATABASE_URL"))
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        result = await embed_rd311_chunks(session)
        print(f"\n=== EMBED SUMMARY ===")
        for k, v in result.items():
            print(f"  {k}: {v}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
