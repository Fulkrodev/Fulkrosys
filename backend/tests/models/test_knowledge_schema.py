"""Tests for the knowledge corpus schema: sources, documents, chunks, links, LLM log."""
import uuid

import pytest
from sqlalchemy import text

from backend.app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeLink,
    KnowledgeSource,
    LLMInteractionLog,
)


# ── KnowledgeSource ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_insert_knowledge_source(db):
    code = f"TEST_{uuid.uuid4().hex[:8]}"
    src = KnowledgeSource(code=code, title="RD 311/2022 (ENS)", publisher="BOE")
    db.add(src)
    await db.flush()
    assert src.id is not None
    assert src.language == "es"


@pytest.mark.asyncio
async def test_knowledge_source_unique_code(db):
    code = f"UNQ_{uuid.uuid4().hex[:8]}"
    db.add(KnowledgeSource(code=code, title="A", publisher="X"))
    await db.flush()
    db.add(KnowledgeSource(code=code, title="B", publisher="Y"))
    with pytest.raises(Exception):
        await db.flush()


# ── KnowledgeDocument (extended) ──────────────────────────────────

@pytest.mark.asyncio
async def test_insert_knowledge_document_with_source(db):
    src = KnowledgeSource(
        code=f"SRC_{uuid.uuid4().hex[:8]}", title="Test Source", publisher="TEST",
    )
    db.add(src)
    await db.flush()

    doc = KnowledgeDocument(
        title="Articulo 1 - Objeto",
        source_id=src.id,
        mime_type="text/html",
    )
    db.add(doc)
    await db.flush()
    assert doc.id is not None
    assert doc.source_id == src.id
    assert doc.chunk_count == 0


# ── KnowledgeChunk (extended) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_insert_knowledge_chunk_with_new_fields(db):
    doc = KnowledgeDocument(title="Chunk test doc")
    db.add(doc)
    await db.flush()

    chunk = KnowledgeChunk(
        document_id=doc.id,
        seccion="Anexo II",
        content="Medidas de seguridad del ENS aplicables a sistemas.",
        chunk_index=0,
        heading_path="Anexo II > mp.info.1",
        measure_code="mp.info.1",
        article_ref="Articulo 12",
        token_count=42,
    )
    db.add(chunk)
    await db.flush()
    assert chunk.id is not None
    assert chunk.measure_code == "mp.info.1"
    assert chunk.chunk_index == 0


@pytest.mark.asyncio
async def test_chunk_embedding_vector(db):
    doc = KnowledgeDocument(title="Embedding test doc")
    db.add(doc)
    await db.flush()

    vec = [0.01] * 1024
    chunk = KnowledgeChunk(
        document_id=doc.id,
        content="Vector de prueba para embeddings.",
        embedding=vec,
    )
    db.add(chunk)
    await db.flush()
    assert chunk.id is not None


@pytest.mark.asyncio
async def test_tsvector_column_populated(db):
    doc = KnowledgeDocument(title="Tsvector test doc")
    db.add(doc)
    await db.flush()

    chunk = KnowledgeChunk(
        document_id=doc.id,
        content="Las medidas de seguridad protegen los sistemas de informacion.",
    )
    db.add(chunk)
    await db.flush()

    row = await db.execute(
        text("SELECT content_tsvector IS NOT NULL FROM knowledge_chunks WHERE id = :id"),
        {"id": str(chunk.id)},
    )
    assert row.scalar() is True


@pytest.mark.asyncio
async def test_fulltext_search(db):
    doc = KnowledgeDocument(title="FTS test doc")
    db.add(doc)
    await db.flush()

    chunk = KnowledgeChunk(
        document_id=doc.id,
        content="La autenticacion multifactor protege contra accesos no autorizados.",
    )
    db.add(chunk)
    await db.flush()

    row = await db.execute(
        text(
            "SELECT id FROM knowledge_chunks "
            "WHERE content_tsvector @@ plainto_tsquery('spanish', 'autenticacion') "
            "AND id = :id"
        ),
        {"id": str(chunk.id)},
    )
    assert row.scalar() is not None


@pytest.mark.asyncio
async def test_vector_cosine_search(db):
    doc = KnowledgeDocument(title="Vector search doc")
    db.add(doc)
    await db.flush()

    vec = [0.5] * 1024
    chunk = KnowledgeChunk(
        document_id=doc.id,
        content="Seguridad perimetral.",
        embedding=vec,
    )
    db.add(chunk)
    await db.flush()

    query_vec = "[" + ",".join(["0.5"] * 1024) + "]"
    row = await db.execute(
        text(
            f"SELECT id, embedding <=> '{query_vec}'::vector AS dist "
            "FROM knowledge_chunks WHERE id = :id"
        ),
        {"id": str(chunk.id)},
    )
    result = row.one()
    assert float(result.dist) < 0.01


# ── KnowledgeLink ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_insert_knowledge_link(db):
    doc = KnowledgeDocument(title="Link test doc")
    db.add(doc)
    await db.flush()

    c1 = KnowledgeChunk(document_id=doc.id, content="Chunk A")
    c2 = KnowledgeChunk(document_id=doc.id, content="Chunk B")
    db.add_all([c1, c2])
    await db.flush()

    link = KnowledgeLink(
        source_chunk_id=c1.id,
        target_chunk_id=c2.id,
        link_type="implements",
        confidence=0.95,
    )
    db.add(link)
    await db.flush()
    assert link.id is not None


# ── LLMInteractionLog ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_insert_llm_interaction_log(db):
    log = LLMInteractionLog(
        feature="m19_risk",
        model="claude-sonnet-4-20250514",
        prompt_hash="abc123def456",
        prompt_tokens=100,
        completion_tokens=200,
        total_tokens=300,
        latency_ms=1500,
    )
    db.add(log)
    await db.flush()
    assert log.id is not None
    assert log.status == "success"


@pytest.mark.asyncio
async def test_llm_log_with_error(db):
    log = LLMInteractionLog(
        feature="corpus_ingest",
        model="text-embedding-3-large",
        prompt_hash="err_hash_001",
        prompt_tokens=50,
        completion_tokens=0,
        total_tokens=50,
        latency_ms=3000,
        status="error",
        error_message="Rate limit exceeded",
    )
    db.add(log)
    await db.flush()
    assert log.status == "error"
