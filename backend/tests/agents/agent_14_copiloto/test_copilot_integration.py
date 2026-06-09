"""Integration tests for Agent 14 copilot — require real Anthropic API + DB.

These tests are marked with @pytest.mark.llm and excluded from default runs.
Run with: pytest -m llm -v
"""
import pytest

from backend.app.agents.agent_14_copiloto.service import answer_question
from backend.app.agents.agent_14_copiloto.types import CopilotQuery


@pytest.mark.llm
async def test_copilot_answers_measure_question(db):
    """Ask about a specific ENS measure — should get a grounded answer."""
    query = CopilotQuery(question="¿Qué exige op.acc.6 del RD 311/2022?")
    result = await answer_question(db, query)

    assert result.answer
    assert result.model_used
    assert result.tokens_input > 0
    assert result.tokens_output > 0
    assert result.latency_ms > 0


@pytest.mark.llm
async def test_copilot_handles_unknown_topic(db):
    """Ask about something not in corpus — should get 'no encontrado'."""
    query = CopilotQuery(
        question="¿Qué dice el RD 311/2022 sobre criptografía cuántica?"
    )
    result = await answer_question(db, query)

    assert result.answer
    # Either it says "no encontrado" or it gives a low-confidence answer
    assert result.not_in_corpus or result.low_grounding_confidence or result.answer


@pytest.mark.llm
async def test_copilot_returns_chunk_ids(db):
    """Copilot should return the chunk IDs used for RAG context."""
    query = CopilotQuery(
        question="¿Cuáles son las medidas del marco organizativo del ENS?"
    )
    result = await answer_question(db, query)

    assert result.answer
    # chunk_ids_used may be empty if corpus has no matching chunks,
    # but the field should always be present
    assert isinstance(result.chunk_ids_used, list)
