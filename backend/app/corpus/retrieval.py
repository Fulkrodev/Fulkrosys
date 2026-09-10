"""Hybrid retrieval: BM25 + vector + Reciprocal Rank Fusion (RRF).

Implements the official RAG strategy from ENS Platform Master Spec sec 4.5:
1. BM25 (PostgreSQL ts_rank over content_tsvector) -> top N1
2. Vector (pgvector cosine similarity) -> top N2
3. Reciprocal Rank Fusion -> top K unique results
4. Rerank cross-encoder -> top K (TODO-M11-G1 cerrado · disparador
   corpus >=500 chunks o A14 grounding pobre · ver backlog_formal.md).
   Pipeline RAG actual 3-etapas (BM25+vector+RRF) operativo · suficiente
   para corpus actual (~127 chunks).

Consumed by Motor 11 Copiloto and any agent needing grounded RAG.

Refs:
- Cormack, Clarke, Buettcher (2009) "Reciprocal Rank Fusion outperforms
  Condorcet and individual Rank Learning Methods"
- ENS_PLATFORM_MASTER_SPEC_v2.1 sec 4.5
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from time import perf_counter as _perf_counter
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.ai.embeddings import get_default_embedding_provider
from backend.app.motors.m_observability.metricas import (
    observar_recuperacion as _observar_recuperacion,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# 60 es la constante del articulo de Cormack et al., pero desde 2026-09-10 ya no
# esta aqui por eso: esta MEDIDA. Barrido de k en {1,5,10,20,30,60,100,200} sobre
# 49 consultas etiquetadas -> acierto@5 IDENTICO en los ocho valores (0,898) y el
# MRR se mueve una milesima. Se conserva el 60 por parsimonia, no porque gane.
# El motivo de que k sea irrelevante da mas miedo que el valor de k: 27 de las 49
# consultas se quedan sin candidatos BM25 (plainto_tsquery une los terminos con
# AND), asi que en mas de la mitad de los casos la "fusion" es la lista vectorial
# con otro nombre. Medido tambien: la fusion NO gana a la rama vectorial sola en
# ninguna metrica. Ver docs/EVAL_RECUPERACION.md y `make eval-recuperacion`.
RRF_K = 60
DEFAULT_BM25_TOP = 30
DEFAULT_VECTOR_TOP = 30
DEFAULT_FINAL_TOP = 5
E5_QUERY_PREFIX = "query: "


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class HybridResult:
    """A single result from hybrid search with provenance info."""

    chunk_id: str
    content: str
    measure_code: Optional[str]
    document_title: str
    source_code: Optional[str]
    heading_path: Optional[str]
    article_ref: Optional[str]
    bm25_rank: Optional[int]  # 1-indexed; None if not in BM25 results
    vector_rank: Optional[int]  # 1-indexed; None if not in vector results
    rrf_score: float
    # Max cosine similarity of the best vector hit BEFORE RRF fusion.
    # Range 0..1 (e5 + L2 normalized). Same value across all results in a
    # single query — global signal "how close is the corpus to this query".
    # Used by NEW8 corpus_gap fallback (threshold 0.45 in A14 service).
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _l2_normalize(vec: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in vec))
    return [x / n for x in vec] if n > 0 else vec


async def _bm25_search(
    session: AsyncSession,
    query: str,
    top_n: int,
    only_with_measure_code: bool,
    source_codes: Optional[list[str]],
    measure_codes: Optional[list[str]] = None,
    sector_aplicacion: Optional[list[str]] = None,
) -> list[tuple[str, int]]:
    """BM25 search. Returns [(chunk_id, rank)] with rank 1-indexed."""
    where = ["content_tsvector @@ plainto_tsquery('spanish', :q)"]
    params: dict = {"q": query, "k": top_n}

    if measure_codes:
        where.append("LOWER(c.measure_code) = ANY(:measure_codes)")
        params["measure_codes"] = [m.lower() for m in measure_codes]
    elif only_with_measure_code:
        where.append("c.measure_code IS NOT NULL")
    if source_codes:
        where.append("s.code = ANY(:source_codes)")
        params["source_codes"] = source_codes
    if sector_aplicacion:
        # ARRAY overlap operator · returns true si algun elemento coincide
        where.append("d.sector_aplicacion && CAST(:sector_aplicacion AS TEXT[])")
        params["sector_aplicacion"] = sector_aplicacion

    sql = (
        "SELECT c.id::text, "
        "ts_rank_cd(c.content_tsvector, plainto_tsquery('spanish', :q)) AS rank "
        "FROM knowledge_chunks c "
        "JOIN knowledge_documents d ON d.id = c.document_id "
        "LEFT JOIN knowledge_sources s ON s.id = d.source_id "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY rank DESC LIMIT :k"
    )
    result = await session.execute(text(sql), params)
    return [(row[0], idx + 1) for idx, row in enumerate(result)]


async def _vector_search(
    session: AsyncSession,
    query: str,
    top_n: int,
    only_with_measure_code: bool,
    source_codes: Optional[list[str]],
    measure_codes: Optional[list[str]] = None,
    sector_aplicacion: Optional[list[str]] = None,
) -> tuple[list[tuple[str, int]], float]:
    """Vector cosine search. Returns ([(chunk_id, rank)], top_cosine_sim).

    The second element is the cosine similarity (1 - cosine distance, range
    0..1) of the best vector hit BEFORE any fusion. 0.0 if no hits.
    """
    provider = get_default_embedding_provider()
    raw_emb = provider.embed_query(E5_QUERY_PREFIX + query)
    query_emb = _l2_normalize(raw_emb)

    where = ["c.embedding IS NOT NULL"]
    params: dict = {"qemb": str(query_emb), "k": top_n}

    if measure_codes:
        where.append("LOWER(c.measure_code) = ANY(:measure_codes)")
        params["measure_codes"] = [m.lower() for m in measure_codes]
    elif only_with_measure_code:
        where.append("c.measure_code IS NOT NULL")
    if source_codes:
        where.append("s.code = ANY(:source_codes)")
        params["source_codes"] = source_codes
    if sector_aplicacion:
        where.append("d.sector_aplicacion && CAST(:sector_aplicacion AS TEXT[])")
        params["sector_aplicacion"] = sector_aplicacion

    sql = (
        "SELECT c.id::text, "
        "1 - (c.embedding <=> CAST(:qemb AS vector)) AS cos_sim "
        "FROM knowledge_chunks c "
        "JOIN knowledge_documents d ON d.id = c.document_id "
        "LEFT JOIN knowledge_sources s ON s.id = d.source_id "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY c.embedding <=> CAST(:qemb AS vector) LIMIT :k"
    )
    result = await session.execute(text(sql), params)
    rows = list(result)
    ranked = [(row[0], idx + 1) for idx, row in enumerate(rows)]
    top_cos = float(rows[0][1]) if rows else 0.0
    return ranked, top_cos


def _rrf_fuse(
    bm25_ranks: dict[str, int],
    vector_ranks: dict[str, int],
    k: int = RRF_K,
) -> dict[str, float]:
    """RRF fusion: score(d) = sum(1/(k + rank_i(d))) across all lists."""
    all_chunks = set(bm25_ranks) | set(vector_ranks)
    scores = {}
    for cid in all_chunks:
        score = 0.0
        if cid in bm25_ranks:
            score += 1.0 / (k + bm25_ranks[cid])
        if cid in vector_ranks:
            score += 1.0 / (k + vector_ranks[cid])
        scores[cid] = score
    return scores


async def _hydrate_results(
    session: AsyncSession,
    chunk_ids: list[str],
    bm25_ranks: dict[str, int],
    vector_ranks: dict[str, int],
    rrf_scores: dict[str, float],
    confidence: float,
) -> list[HybridResult]:
    """Load full chunk data and build HybridResult list in RRF order."""
    if not chunk_ids:
        return []

    sql = (
        "SELECT c.id::text, c.content, c.measure_code, c.heading_path, "
        "c.article_ref, d.title AS doc_title, s.code AS source_code "
        "FROM knowledge_chunks c "
        "JOIN knowledge_documents d ON d.id = c.document_id "
        "LEFT JOIN knowledge_sources s ON s.id = d.source_id "
        "WHERE c.id::text = ANY(:ids)"
    )
    result = await session.execute(text(sql), {"ids": chunk_ids})
    rows_by_id = {row[0]: row for row in result}

    output = []
    for cid in chunk_ids:
        row = rows_by_id.get(cid)
        if row is None:
            continue
        output.append(
            HybridResult(
                chunk_id=row[0],
                content=row[1] or "",
                measure_code=row[2],
                document_title=row[5] or "",
                source_code=row[6],
                heading_path=row[3],
                article_ref=row[4],
                bm25_rank=bm25_ranks.get(cid),
                vector_rank=vector_ranks.get(cid),
                rrf_score=rrf_scores[cid],
                confidence=confidence,
            )
        )
    return output


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def hybrid_search(
    session: AsyncSession,
    query: str,
    top_k: int = DEFAULT_FINAL_TOP,
    bm25_top: int = DEFAULT_BM25_TOP,
    vector_top: int = DEFAULT_VECTOR_TOP,
    only_with_measure_code: bool = False,
    source_codes: Optional[list[str]] = None,
    measure_codes: Optional[list[str]] = None,
    sector_aplicacion: Optional[list[str]] = None,
) -> list[HybridResult]:
    """Hybrid BM25 + vector + RRF search over the knowledge corpus.

    Args:
        session: AsyncSession connected to the corpus DB.
        query: User question in Spanish.
        top_k: Number of final results (default 5).
        bm25_top: BM25 candidates before fusion (default 30).
        vector_top: Vector candidates before fusion (default 30).
        only_with_measure_code: Restrict to ENS measure chunks.
        source_codes: Restrict to specific knowledge sources.
        measure_codes: Restrict to specific ENS measure codes (e.g. ["op.acc.6"]).
        sector_aplicacion: Restrict to docs with at least one of these sectors
            (PostgreSQL array overlap). Example: ["privado"] excluye docs
            etiquetados solo ["publico"]. None = sin filtro (backward compat).
            Sub-lote 1.B.5.2 · ADR-CORPUS-001 Decision 7 · AMEND-012.

    Returns:
        List of HybridResult sorted by rrf_score descending.
    """
    # Cada etapa se cronometra por separado (BLOQUE G). Se mide POR ETAPA y no
    # sólo el total porque el total no dice dónde está el problema: si la
    # búsqueda tarda un segundo, importa mucho saber si se fue en embeber la
    # consulta, en Postgres o en la fusión. La fusión debería ser
    # microsegundos; si algún día no lo es, se verá aquí.
    _t = _perf_counter()
    bm25_results = await _bm25_search(
        session, query, bm25_top, only_with_measure_code, source_codes,
        measure_codes, sector_aplicacion,
    )
    _observar_recuperacion("bm25", _perf_counter() - _t)

    _t = _perf_counter()
    vector_results, top_cosine = await _vector_search(
        session, query, vector_top, only_with_measure_code, source_codes,
        measure_codes, sector_aplicacion,
    )
    # Ojo al leer esta serie: incluye el embebido de la consulta, que es lo que
    # suele dominar. `_vector_search` llama al proveedor de embeddings dentro.
    _observar_recuperacion("vectorial_con_embebido", _perf_counter() - _t)

    # 2. Build rank dicts
    bm25_ranks = dict(bm25_results)
    vector_ranks = dict(vector_results)

    # 3. RRF fusion
    _t = _perf_counter()
    rrf_scores = _rrf_fuse(bm25_ranks, vector_ranks)

    # 4. Top K by RRF score
    top_ids = sorted(rrf_scores, key=lambda c: rrf_scores[c], reverse=True)[:top_k]
    _observar_recuperacion("fusion", _perf_counter() - _t)

    # 5. Hydrate with full data
    _t = _perf_counter()
    salida = await _hydrate_results(
        session, top_ids, bm25_ranks, vector_ranks, rrf_scores, top_cosine
    )
    _observar_recuperacion("hidratado", _perf_counter() - _t)
    return salida
