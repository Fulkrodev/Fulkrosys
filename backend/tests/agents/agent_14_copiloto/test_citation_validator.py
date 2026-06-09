"""Tests for Agent 14 citation validator — sync, no DB required."""
from backend.app.agents.agent_14_copiloto.citation_validator import (
    assess_grounding,
    extract_citations,
    is_not_in_corpus,
)


class TestExtractCitations:
    """Extract bracketed citations from LLM responses."""

    def test_extracts_rd_citation(self):
        text = "Segun [RD 311/2022 medida op.acc.6], el acceso debe controlarse."
        citations = extract_citations(text)
        assert len(citations) == 1
        assert "RD 311/2022 medida op.acc.6" in citations[0]

    def test_extracts_ccn_citation(self):
        text = "La guia [CCN-STIC 804 seccion 5.2] establece las categorias."
        citations = extract_citations(text)
        assert len(citations) == 1
        assert "CCN-STIC 804" in citations[0]

    def test_extracts_multiple_citations(self):
        text = (
            "Como indica [RD 311/2022 art. 12], y complementado por "
            "[CCN-STIC 804 seccion 3.1], la seguridad es integral."
        )
        citations = extract_citations(text)
        assert len(citations) == 2

    def test_no_citations_returns_empty(self):
        text = "No hay referencias en este texto."
        citations = extract_citations(text)
        assert citations == []


class TestIsNotInCorpus:
    """Detect 'not found in corpus' responses."""

    def test_detects_standard_phrase(self):
        text = "No encontrado en el corpus oficial."
        assert is_not_in_corpus(text) is True

    def test_detects_variant_phrase(self):
        text = "La informacion no se encuentra en el corpus disponible."
        assert is_not_in_corpus(text) is True

    def test_normal_answer_is_false(self):
        text = "La medida op.acc.6 exige control de acceso logico."
        assert is_not_in_corpus(text) is False


class TestAssessGrounding:
    """Evaluate grounding confidence of LLM responses."""

    def test_not_in_corpus_is_grounded(self):
        answer = "No encontrado en el corpus oficial."
        assert assess_grounding(answer, []) is False

    def test_long_answer_no_citations_is_low_confidence(self):
        answer = "A" * 200  # Long answer with no citations
        assert assess_grounding(answer, ["chunk1"]) is True

    def test_answer_with_citations_is_grounded(self):
        answer = "Segun [RD 311/2022 medida op.acc.6], se requiere control de acceso."
        assert assess_grounding(answer, ["chunk1"]) is False

    def test_no_chunks_with_answer_is_low_confidence(self):
        answer = "La seguridad es importante en todas las organizaciones."
        assert assess_grounding(answer, []) is True
