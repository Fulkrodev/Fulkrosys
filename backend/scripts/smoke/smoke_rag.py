"""Sub-lote 1.B.5.2 PASO 7 · smoke RAG sobre el corpus ingerido.

6 queries representativas que cubren los 14 PDFs del batch 1.B.5.2.
Valida que hybrid_search devuelve resultados relevantes con citation.

Q6 es BASELINE NO-PRESENTE intencionado (MAGERIT no esta en este batch ·
debe disparar corpus_gap con confidence < 0.45).

Usage:
    PYTHONPATH=. .venv/bin/python backend/scripts/smoke/smoke_rag.py
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import NamedTuple

from dotenv import load_dotenv

# W9-2: .env relativo al repo-root (backend/scripts/smoke/ → parents[3]).
load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / ".env")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.corpus.retrieval import hybrid_search


CORPUS_GAP_THRESHOLD = 0.45  # alineado con A14 Copiloto fallback


class Query(NamedTuple):
    qid: str
    text: str
    expects_results: bool  # True · esperar chunks · False · esperar corpus_gap
    expect_sources_any: list[str]  # source codes that should appear if results


QUERIES: list[Query] = [
    Query(
        qid="Q1",
        text="Que exige CCN-STIC-802 para auditoria del ENS categoria MEDIA",
        expects_results=True,
        expect_sources_any=["CCN-STIC-802", "CCN-STIC-808"],
    ),
    Query(
        qid="Q2",
        text="Plazos legales notificacion incidente bajo NIS2 y RGPD",
        expects_results=True,
        expect_sources_any=["UE-NIS2", "UE-RGPD"],
    ),
    Query(
        qid="Q3",
        text="Diferencia entre auditoria interna y externa del ENS",
        expects_results=True,
        expect_sources_any=["CCN-STIC-802", "CCN-STIC-808"],
    ),
    Query(
        qid="Q4",
        text="Articulo 32 RGPD medidas tecnicas y organizativas",
        expects_results=True,
        expect_sources_any=["UE-RGPD", "AEPD-RIESGO-EIPD"],
    ),
    Query(
        qid="Q5",
        text="DORA framework testing resiliencia operativa digital sector financiero",
        expects_results=True,
        expect_sources_any=["UE-DORA"],
    ),
    Query(
        qid="Q6",
        text="MAGERIT v3 catalogo de amenazas operacionales A.5 A.6",
        expects_results=False,  # MAGERIT NO esta en este batch · gap esperado
        expect_sources_any=[],
    ),
]


async def run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    url = os.environ["DATABASE_URL"]
    engine = create_async_engine(url)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    passed = 0
    failed = 0

    async with SessionLocal() as session:
        for q in QUERIES:
            print(f"\n=== {q.qid} · {q.text!r} ===")
            try:
                results = await hybrid_search(
                    session=session,
                    query=q.text,
                    top_k=5,
                    sector_aplicacion=["publico", "privado"],
                )
            except Exception as exc:
                print(f"  ✗ hybrid_search raised: {type(exc).__name__}: {exc}")
                failed += 1
                continue

            confidence = results[0].confidence if results else 0.0
            sources_seen = {r.source_code for r in results if r.source_code}

            print(f"  results: {len(results)}  confidence: {confidence:.3f}  sources: {sorted(sources_seen)}")
            for r in results[:3]:
                citation = f"{r.source_code} · {r.heading_path or '-'} · article {r.article_ref or '-'}"
                print(f"    [rrf={r.rrf_score:.4f}] {citation}")

            if q.expects_results:
                # Esperamos chunks relevantes Y confidence sobre threshold
                cond_chunks = len(results) >= 3
                cond_conf = confidence >= CORPUS_GAP_THRESHOLD
                cond_source = (not q.expect_sources_any) or bool(sources_seen & set(q.expect_sources_any))
                if cond_chunks and cond_conf and cond_source:
                    print(f"  ✓ PASS · ≥3 chunks · confidence ≥ {CORPUS_GAP_THRESHOLD} · source match")
                    passed += 1
                else:
                    miss = []
                    if not cond_chunks: miss.append(f"chunks={len(results)}<3")
                    if not cond_conf: miss.append(f"conf={confidence:.3f}<{CORPUS_GAP_THRESHOLD}")
                    if not cond_source: miss.append(f"sources {sources_seen} ∩ {q.expect_sources_any} = ∅")
                    print(f"  ✗ FAIL · {', '.join(miss)}")
                    failed += 1
            else:
                # Baseline NO-presente: esperamos corpus_gap (confidence baja)
                if confidence < CORPUS_GAP_THRESHOLD:
                    print(f"  ✓ PASS · corpus_gap correcto · confidence {confidence:.3f} < {CORPUS_GAP_THRESHOLD}")
                    passed += 1
                else:
                    print(f"  ✗ FAIL · confidence {confidence:.3f} ≥ {CORPUS_GAP_THRESHOLD} (esperaba gap)")
                    failed += 1

    await engine.dispose()

    print("\n=== SMOKE RAG SUMMARY ===")
    print(f"  passed: {passed}/{len(QUERIES)}")
    print(f"  failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
