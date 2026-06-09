"""Tests sub-bloque 11.D — NEW8 corpus fallback branch.

Verifica que cuando ``confidence < 0.45``:
1. El frame ``done`` lleva ``corpus_gap=True``.
2. El system prompt enviado al LLM incluye la INSTRUCCIÓN CRÍTICA del
   fallback (no inventa, sugiere fuentes externas).
3. El path inverso (confidence >= 0.45) NO incluye la instrucción y el
   ``corpus_gap`` queda en ``False``.

Los tests usan un mock del LLM router para no requerir ANTHROPIC_API_KEY
ni la marca ``llm`` y poder correr en la suite default.
"""
from __future__ import annotations

import json
from typing import Iterator

import pytest

from backend.app.agents.agent_14_copiloto import service as a14_service
from backend.app.corpus.retrieval import HybridResult


class _CapturingFakeLLMResponse:
    def __init__(self, content: str):
        self.content = content
        self.model = "fake-model"
        self.prompt_tokens = 1
        self.completion_tokens = 1
        self.total_tokens = 2
        self.latency_ms = 1.0


class _CapturingFakeRouter:
    """Captures the full ``messages`` payload sent to the LLM for assertions."""

    def __init__(self, tokens: list[str]):
        self._tokens = tokens
        self.last_messages: list[dict] | None = None

    def stream_complete(self, **kwargs) -> Iterator[str]:
        self.last_messages = kwargs.get("messages")
        for tok in self._tokens:
            yield tok

    def complete(self, **kwargs) -> _CapturingFakeLLMResponse:
        self.last_messages = kwargs.get("messages")
        return _CapturingFakeLLMResponse("".join(self._tokens))


def _stub_chunk(confidence: float) -> HybridResult:
    return HybridResult(
        chunk_id="00000000-0000-0000-0000-000000000001",
        content="contenido stub para test",
        measure_code="op.acc.6",
        document_title="RD 311/2022",
        source_code="RD-311-2022",
        heading_path=None,
        article_ref=None,
        bm25_rank=1,
        vector_rank=1,
        rrf_score=0.05,
        confidence=confidence,
    )


async def _stub_hybrid_search_low(*_args, **_kwargs):
    return [_stub_chunk(0.30)]


async def _stub_hybrid_search_high(*_args, **_kwargs):
    return [_stub_chunk(0.85)]


async def _stub_hybrid_search_empty(*_args, **_kwargs):
    return []


def _collect_frames(text: str) -> list[dict]:
    frames: list[dict] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s.startswith("data:"):
            continue
        frames.append(json.loads(s[len("data:"):].strip()))
    return frames


@pytest.mark.asyncio
async def test_corpus_gap_branch_active_when_low_confidence(
    async_client, db, monkeypatch,
):
    """Query con baja confidence → done.corpus_gap=True + system prompt enriquecido."""
    fake_router = _CapturingFakeRouter([
        "Esta consulta requiere fuentes que aún no están disponibles ",
        "en el corpus de FULKRO. Te recomiendo consultar ",
        "https://www.ccn-cert.cni.es/series-ccn-stic.html",
    ])
    monkeypatch.setattr(
        a14_service, "get_default_llm_router", lambda: fake_router,
    )
    monkeypatch.setattr(
        a14_service, "hybrid_search", _stub_hybrid_search_low,
    )

    payload = {"question": "pregunta off-corpus de prueba"}
    async with async_client.stream(
        "POST", "/api/v1/copilot/chat/stream", json=payload,
    ) as resp:
        assert resp.status_code == 200, await resp.aread()
        body = (await resp.aread()).decode()

    frames = _collect_frames(body)
    start = next(f for f in frames if f["type"] == "start")
    done = next(f for f in frames if f["type"] == "done")["data"]
    assert start["corpus_gap"] is True
    assert start["confidence"] < a14_service.CORPUS_GAP_CONFIDENCE_THRESHOLD
    assert done["corpus_gap"] is True
    assert done["confidence"] < a14_service.CORPUS_GAP_CONFIDENCE_THRESHOLD

    assert fake_router.last_messages is not None
    system_prompt = fake_router.last_messages[0]["content"]
    assert "INSTRUCCIÓN CRÍTICA" in system_prompt
    assert "corpus de FULKRO" in system_prompt
    assert "ccn-cert.cni.es" in system_prompt


@pytest.mark.asyncio
@pytest.mark.llm
async def test_corpus_gap_real_llm_does_not_hallucinate(
    async_client, db, monkeypatch,
):
    """End-to-end real-LLM call con corpus_gap forzado.

    Valida que la INSTRUCCIÓN CRÍTICA del fallback se respeta a nivel de
    comportamiento: el modelo (a) sugiere al menos una URL oficial, (b)
    NO usa frases de pre-training fallback, (c) menciona explícitamente
    que la fuente no está disponible en el corpus.

    Por qué se fuerza corpus_gap (no se deriva de threshold real): los
    embeddings ``intfloat/multilingual-e5-large`` producen cosine sim
    >0.6 incluso para queries semánticamente off-topic cuando comparten
    vocabulario regulatorio (cualquier query con "certificación", "nivel",
    "norma" cae sobre documentos ENS aunque hablen de otra normativa).
    El threshold 0.45 captura solo casos extremos de query absurda. Para
    validar el comportamiento del LLM ante el branch fallback, forzamos
    chunks con confidence=0.30 vía monkeypatch — el LLM real recibe el
    system prompt corpus_gap y debe respetar las 5 reglas estrictas.

    Marca ``llm`` para excluir de CI default (requiere ANTHROPIC_API_KEY).
    """

    async def _stub_low_confidence(*_args, **_kwargs):
        return [_stub_chunk(0.30)]

    monkeypatch.setattr(
        a14_service, "hybrid_search", _stub_low_confidence,
    )

    full_text = ""
    corpus_gap_seen: bool | None = None
    confidence_seen: float | None = None
    model_seen: str | None = None

    payload = {
        "question": (
            "Cuál es el procedimiento detallado de notificación a la AEPD "
            "para una brecha de datos personales con afectación masiva "
            "(>10000 sujetos) bajo el RGPD artículo 33 según la última "
            "circular AEPD 2025."
        ),
    }
    async with async_client.stream(
        "POST", "/api/v1/copilot/chat/stream", json=payload,
    ) as resp:
        assert resp.status_code == 200, await resp.aread()
        async for raw_line in resp.aiter_lines():
            line = raw_line.strip()
            if not line.startswith("data:"):
                continue
            event = json.loads(line[len("data:"):].strip())
            if event["type"] == "delta":
                full_text += event.get("text", "")
            elif event["type"] == "done":
                done = event["data"]
                full_text = done.get("answer", full_text)
                corpus_gap_seen = done.get("corpus_gap")
                confidence_seen = done.get("confidence")
                model_seen = done.get("model_used")

    assert corpus_gap_seen is True, (
        f"Esperado corpus_gap=True con stub · confidence={confidence_seen}"
    )
    assert model_seen and "claude" in model_seen.lower(), (
        f"Modelo usado debe ser claude-* · got: {model_seen}"
    )

    answer_lower = full_text.lower()
    urls_oficiales = [
        "ccn-cert.cni.es",
        "boe.es",
        "aepd.es",
        "eur-lex.europa.eu",
    ]
    assert any(u in answer_lower for u in urls_oficiales), (
        f"Esperado al menos 1 URL oficial sugerida · respuesta inicio: "
        f"{full_text[:400]}"
    )

    assert "corpus" in answer_lower and (
        "fulkro" in answer_lower or "no" in answer_lower
    ), (
        f"Esperado mención explícita de corpus/no-disponible · respuesta "
        f"inicio: {full_text[:400]}"
    )

    forbidden = [
        "según mi conocimiento general",
        "en general la normativa",
        "típicamente este tipo de",
    ]
    for phrase in forbidden:
        assert phrase not in answer_lower, (
            f"Phrase prohibida detectada: '{phrase}'"
        )


@pytest.mark.asyncio
async def test_corpus_gap_branch_inactive_when_high_confidence(
    async_client, db, monkeypatch,
):
    """Query con info clara en corpus → corpus_gap=False, NO fallback en system prompt."""
    fake_router = _CapturingFakeRouter([
        "La medida [RD 311/2022 medida op.acc.6] exige autenticación robusta.",
    ])
    monkeypatch.setattr(
        a14_service, "get_default_llm_router", lambda: fake_router,
    )
    monkeypatch.setattr(
        a14_service, "hybrid_search", _stub_hybrid_search_high,
    )

    payload = {"question": "qué exige op.acc.6"}
    async with async_client.stream(
        "POST", "/api/v1/copilot/chat/stream", json=payload,
    ) as resp:
        assert resp.status_code == 200, await resp.aread()
        body = (await resp.aread()).decode()

    frames = _collect_frames(body)
    start = next(f for f in frames if f["type"] == "start")
    done = next(f for f in frames if f["type"] == "done")["data"]
    assert start["corpus_gap"] is False
    assert start["confidence"] >= a14_service.CORPUS_GAP_CONFIDENCE_THRESHOLD
    assert done["corpus_gap"] is False

    assert fake_router.last_messages is not None
    system_prompt = fake_router.last_messages[0]["content"]
    assert "INSTRUCCIÓN CRÍTICA" not in system_prompt
    assert "ccn-cert.cni.es" not in system_prompt


@pytest.mark.asyncio
async def test_corpus_gap_prompt_contains_official_urls(
    async_client, db, monkeypatch,
):
    """corpus_gap=True (sin chunks RAG) → system prompt contiene las 4 URLs oficiales.

    Edge case adicional: sin chunks → confidence=0 también dispara el branch.
    Valida que el bloque CORPUS_GAP_FALLBACK_PROMPT incluye explícitamente
    los 4 dominios oficiales (CCN-STIC, BOE, AEPD, eIDAS UE) y los marcadores
    de la INSTRUCCIÓN CRÍTICA.
    """
    fake_router = _CapturingFakeRouter([
        "Esta consulta requiere fuentes externas: ",
        "https://www.boe.es/buscar/",
    ])
    monkeypatch.setattr(
        a14_service, "get_default_llm_router", lambda: fake_router,
    )
    monkeypatch.setattr(
        a14_service, "hybrid_search", _stub_hybrid_search_empty,
    )

    payload = {"question": "pregunta sin chunks en absoluto"}
    async with async_client.stream(
        "POST", "/api/v1/copilot/chat/stream", json=payload,
    ) as resp:
        assert resp.status_code == 200, await resp.aread()
        body = (await resp.aread()).decode()

    frames = _collect_frames(body)
    start = next(f for f in frames if f["type"] == "start")
    done = next(f for f in frames if f["type"] == "done")["data"]
    assert start["corpus_gap"] is True
    assert start["confidence"] == 0.0
    assert done["corpus_gap"] is True
    assert done["chunks_used"] == []

    assert fake_router.last_messages is not None
    system_prompt = fake_router.last_messages[0]["content"]
    assert "INSTRUCCIÓN CRÍTICA" in system_prompt
    for url in (
        "ccn-cert.cni.es",
        "boe.es",
        "aepd.es",
        "eur-lex.europa.eu",
    ):
        assert url in system_prompt, (
            f"URL oficial '{url}' debe estar en el bloque fallback del system prompt"
        )
