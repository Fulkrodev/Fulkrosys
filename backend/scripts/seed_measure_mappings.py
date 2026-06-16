"""Sub-lote 1.B.5.2 PASO 6 · seed knowledge_measure_mappings desde corpus indexado.

Para cada medida ENS (73 del Anexo II RD 311/2022):
  query = "{codigo} {nombre}"
  results = hybrid_search(query, top_k=5, sector_aplicacion=['publico','privado'])
  if confidence > THRESHOLD:
    group by document_id
    INSERT ON CONFLICT DO NOTHING (ens_medida_id, document_id, chunk_ids[], relevance_score, curated_by='auto-rag')

curated_by='auto-rag' permite distinguir mappings automaticos de los curados
manualmente por Marcos en sesion separada (curated_by='marcos').

Usage:
    PYTHONPATH=. .venv/bin/python backend/scripts/seed_measure_mappings.py
    PYTHONPATH=. .venv/bin/python backend/scripts/seed_measure_mappings.py --threshold 0.4 --top-k 10
    PYTHONPATH=. .venv/bin/python backend/scripts/seed_measure_mappings.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time
from collections import defaultdict
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv

# W9-2: .env relativo al repo-root (backend/scripts/ → parents[2]).
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.corpus.retrieval import hybrid_search


logger = logging.getLogger(__name__)


DEFAULT_THRESHOLD = 0.50  # confidence (top cosine) per query · PDF noise tolerant
DEFAULT_TOP_K = 5


async def seed_all(
    threshold: float, top_k: int, dry_run: bool,
) -> dict:
    # Seed scripts usan fulkro_migrate superuser · fulkro_app NOSUPERUSER
    # solo tiene SELECT en knowledge_measure_mappings (read-only consumer
    # A14/A15/A24). Convencion repo: DATABASE_MIGRATE_URL para INSERT/seed.
    # DATABASE_MIGRATE_URL es sync (psycopg) · convertir a asyncpg.
    sync_url = os.environ.get("DATABASE_MIGRATE_URL") or os.environ["DATABASE_URL"]
    url = sync_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(url)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    started = time.monotonic()
    inserted = 0
    skipped_low_confidence = 0
    medidas_with_mapping = 0
    medidas_no_match = 0

    async with SessionLocal() as session:
        # 1. Carga 73 medidas ENS
        medidas_res = await session.execute(text(
            "SELECT codigo, nombre FROM ens_measures "
            "WHERE deleted_at IS NULL ORDER BY codigo"
        ))
        medidas = list(medidas_res)
        logger.info("Procesando %d medidas ENS", len(medidas))

        for codigo, nombre in medidas:
            query = f"{codigo} {nombre}"
            try:
                results = await hybrid_search(
                    session=session,
                    query=query,
                    top_k=top_k,
                    sector_aplicacion=["publico", "privado"],
                )
            except Exception as exc:
                logger.warning("[%s] hybrid_search FAIL: %s", codigo, exc)
                continue

            if not results:
                medidas_no_match += 1
                continue

            confidence = results[0].confidence
            if confidence < threshold:
                skipped_low_confidence += 1
                logger.debug(
                    "[%s] confidence %.3f < %.2f · skip", codigo, confidence, threshold,
                )
                continue

            # 2. Lookup document_id per chunk_id
            chunk_ids = [UUID(r.chunk_id) for r in results]
            doc_lookup = await session.execute(text(
                "SELECT id, document_id FROM knowledge_chunks "
                "WHERE id = ANY(CAST(:ids AS uuid[]))"
            ), {"ids": [str(cid) for cid in chunk_ids]})
            chunk_to_doc: dict[UUID, UUID] = {
                row.id: row.document_id for row in doc_lookup
            }

            # 3. Agrupar chunks por document_id
            doc_chunks: dict[UUID, list[UUID]] = defaultdict(list)
            for cid in chunk_ids:
                doc_id = chunk_to_doc.get(cid)
                if doc_id is not None:
                    doc_chunks[doc_id].append(cid)

            for doc_id, doc_chunk_ids in doc_chunks.items():
                if dry_run:
                    inserted += 1
                    continue
                # ON CONFLICT (ens_medida_id, document_id) DO NOTHING (idempotente)
                await session.execute(text(
                    "INSERT INTO knowledge_measure_mappings "
                    "(ens_medida_id, document_id, chunk_ids, relevance_score, curated_by) "
                    "VALUES (:m, :d, CAST(:ids AS uuid[]), :s, :by) "
                    "ON CONFLICT (ens_medida_id, document_id) DO NOTHING"
                ), {
                    "m": codigo,
                    "d": doc_id,
                    "ids": [str(c) for c in doc_chunk_ids],
                    "s": round(confidence, 4),
                    "by": "auto-rag",
                })
                inserted += 1

            medidas_with_mapping += 1

        if not dry_run:
            await session.commit()

    await engine.dispose()

    elapsed = time.monotonic() - started
    return {
        "medidas_total": len(medidas),
        "medidas_with_mapping": medidas_with_mapping,
        "medidas_no_match": medidas_no_match,
        "skipped_low_confidence": skipped_low_confidence,
        "mappings_inserted": inserted,
        "threshold": threshold,
        "top_k": top_k,
        "elapsed_seconds": round(elapsed, 1),
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed knowledge_measure_mappings auto-rag")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help=f"Min cosine confidence (default {DEFAULT_THRESHOLD})")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K,
                        help=f"Top-K resultados por medida (default {DEFAULT_TOP_K})")
    parser.add_argument("--dry-run", action="store_true", help="Sin INSERT")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    summary = asyncio.run(seed_all(args.threshold, args.top_k, args.dry_run))
    print("\n=== SEED SUMMARY ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
