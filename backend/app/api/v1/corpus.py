"""Corpus search API endpoint.

Single source of truth: corpus/retrieval.py (BM25 + vector + RRF spec sec 4.5).
Refactored from rag/search.py legacy implementation (schema mismatch · roto).
"""
from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.corpus.retrieval import hybrid_search
from backend.app.database import get_db

router = APIRouter(
    prefix="/corpus", tags=["Corpus & RAG"],
    # Marcos-only · evita que una sesión cliente liste el corpus/stats (clase w2p
    # · mirror mcps.py/projects.py). El copiloto usa corpus.retrieval server-side,
    # no este endpoint HTTP → restringirlo no rompe consumidores.
    dependencies=[Depends(require_owner)],
)


@router.get("/search")
async def search_corpus(
    q: str = Query(..., min_length=3, description="Search query in natural language"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Hybrid search over the normative corpus.

    BM25 (PostgreSQL ts_rank over content_tsvector) + pgvector cosine + RRF
    (Reciprocal Rank Fusion) per ENS Platform Master Spec sec 4.5.
    """
    results = await hybrid_search(db, query=q, top_k=limit)
    return {
        "query": q,
        "results_count": len(results),
        "results": [asdict(r) for r in results],
    }


@router.get("/stats")
async def corpus_stats(db: AsyncSession = Depends(get_db)):
    """Get corpus ingestion statistics."""
    from sqlalchemy import text

    docs_row = await db.execute(text("SELECT count(*) FROM knowledge_documents"))
    docs = docs_row.scalar()

    chunks_row = await db.execute(text("SELECT count(*) FROM knowledge_chunks"))
    chunks = chunks_row.scalar()

    emb_row = await db.execute(text(
        "SELECT count(*) FROM knowledge_chunks WHERE embedding IS NOT NULL"
    ))
    with_embeddings = emb_row.scalar()

    return {
        "documents": docs,
        "chunks": chunks,
        "chunks_with_embeddings": with_embeddings,
    }
