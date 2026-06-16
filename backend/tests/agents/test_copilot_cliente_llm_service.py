"""Tests CopilotClienteLLMService swap-in + R29 boundary enforcement.

Sub-atom 1.D.B.1.1 v3.11.

Cobertura:
- check_r29_boundaries · detecta patrones coercitivos + admin lingo
- llm_enabled · respeta config api_key
- Service init · persona cliente loaded
- generate_response: LLM disabled → stub directo
- generate_response: LLM enabled fail → graceful stub fallback (mock router)
- generate_response: boundary violation → fallback stub defensive
- _build_user_message · todos action_ids friendly cliente tono
- Singleton getter · same instance
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from backend.app.agents.copilot_cliente_service import (
    CopilotClienteLLMService,
    check_r29_boundaries,
    get_cliente_llm_service,
    llm_enabled,
)
from backend.tests.conftest import setup_test_project


# ════════════════════════════════════════════════════════════════════
# R29 boundary checks
# ════════════════════════════════════════════════════════════════════


def test_boundary_check_clean_response_ok():
    text = "Tu siguiente paso es Categorización. Sin prisa · a tu ritmo."
    ok, violation = check_r29_boundaries(text)
    assert ok is True
    assert violation is None


def test_boundary_check_detects_coercitive_llevas():
    text = "Llevas 3 días sin completar este paso · debes apurarte."
    ok, violation = check_r29_boundaries(text)
    assert ok is False
    assert violation is not None
    assert "llevas" in violation.lower()


def test_boundary_check_llevas_razon_is_not_coercitive():
    """'llevas razón' es benigno · NO debe disparar R29 (§4.5 tracker:384)."""
    text = "Tienes toda la razón, llevas razón en tu apreciación · buena observación."
    ok, violation = check_r29_boundaries(text)
    assert ok is True
    assert violation is None


def test_boundary_check_llevas_dias_sin_flags():
    """El reproche temporal 'llevas N días sin...' SÍ es coercitivo R29."""
    text = "Recuerda que llevas 5 días sin subir la evidencia."
    ok, violation = check_r29_boundaries(text)
    assert ok is False
    assert violation is not None
    assert "llevas" in violation.lower()


def test_boundary_check_detects_deadline_urgente():
    text = "Atención · deadline urgente este viernes."
    ok, violation = check_r29_boundaries(text)
    assert ok is False
    assert "deadline" in violation.lower()


def test_boundary_check_detects_admin_lingo():
    text = "Sube la evidencia con evidence_type_id correcto · luego audit trail valida."
    ok, violation = check_r29_boundaries(text)
    assert ok is False
    assert "admin lingo" in violation.lower()


def test_boundary_check_friendly_cliente_response_passes():
    text = (
        "¡Hola! Tu próximo paso es completar la categorización de tu empresa. "
        "Es la primera pieza del puzle ENS. Si tienes dudas · pregúntame "
        "lo que sea · estoy aquí cuando me necesites."
    )
    ok, violation = check_r29_boundaries(text)
    assert ok is True
    assert violation is None


# ════════════════════════════════════════════════════════════════════
# LLM enabled flag
# ════════════════════════════════════════════════════════════════════


def test_llm_enabled_returns_bool():
    """Returns boolean reflecting config · NO crash."""
    result = llm_enabled()
    assert isinstance(result, bool)


# ════════════════════════════════════════════════════════════════════
# Service init + singleton
# ════════════════════════════════════════════════════════════════════


def test_service_init_loads_persona_cliente():
    svc = CopilotClienteLLMService()
    assert svc.persona_service.role == "cliente"
    assert svc.persona_service.citations_required is False


def test_get_cliente_llm_service_singleton():
    svc1 = get_cliente_llm_service()
    svc2 = get_cliente_llm_service()
    assert svc1 is svc2


# ════════════════════════════════════════════════════════════════════
# User message building per action_id
# ════════════════════════════════════════════════════════════════════


def test_build_user_message_que_hago():
    svc = CopilotClienteLLMService()
    msg = svc._build_user_message(
        "que_hago", None, "Categorización inicial", None,
    )
    assert "Categorización inicial" in msg
    assert "amable" in msg.lower() or "sin jerga" in msg.lower()


def test_build_user_message_porque_importa():
    svc = CopilotClienteLLMService()
    msg = svc._build_user_message(
        "porque_importa", None, "DdA", None,
    )
    assert "DdA" in msg
    assert "primer principios" in msg.lower() or "sencillos" in msg.lower()


def test_build_user_message_explica_concepto():
    svc = CopilotClienteLLMService()
    msg = svc._build_user_message(
        "explica_concepto", None, None, "MAGERIT",
    )
    assert "MAGERIT" in msg
    assert "jerga" in msg.lower()


def test_build_user_message_chat_send_uses_question():
    svc = CopilotClienteLLMService()
    msg = svc._build_user_message(
        "chat_send", "¿Qué es ENS Anexo II?", None, None,
    )
    assert msg == "¿Qué es ENS Anexo II?"


# ════════════════════════════════════════════════════════════════════
# Generate response flow
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_generate_response_llm_disabled_fallback_stub(db):
    """LLM disabled · respond via stub service directly."""
    svc = CopilotClienteLLMService()

    with patch(
        "backend.app.agents.copilot_cliente_service.llm_enabled",
        return_value=False,
    ):
        text, hint, is_stub = await svc.generate_response(
            db,
            "que_hago",
            project_id=None,
            question=None,
            step_template_id=None,
            step_title="Categorización",
            fase_actual=None,
            concepto=None,
        )

    assert is_stub is True
    assert "Categorización" in text
    assert hint == "Cuando termines · márcalo como hecho"


@pytest.mark.asyncio
async def test_generate_response_llm_error_graceful_fallback(db):
    """LLM call raises exception · fallback to stub gracefully."""
    svc = CopilotClienteLLMService()

    with patch(
        "backend.app.agents.copilot_cliente_service.llm_enabled",
        return_value=True,
    ), patch.object(
        svc, "_call_llm", side_effect=Exception("Mock LLM failure"),
    ):
        text, hint, is_stub = await svc.generate_response(
            db,
            "porque_importa",
            project_id=None,
            question=None,
            step_template_id=None,
            step_title="MAGERIT",
            fase_actual=None,
            concepto=None,
        )

    assert is_stub is True
    assert "MAGERIT" in text


@pytest.mark.asyncio
async def test_generate_response_boundary_violation_fallback(db):
    """LLM returns coercitive response · R29 detect + fallback stub."""
    svc = CopilotClienteLLMService()
    mock_llm_response = (
        "Llevas demasiados días sin completar este paso · es urgente que "
        "lo termines hoy mismo."
    )

    with patch(
        "backend.app.agents.copilot_cliente_service.llm_enabled",
        return_value=True,
    ), patch.object(
        svc, "_call_llm", return_value=mock_llm_response,
    ):
        text, hint, is_stub = await svc.generate_response(
            db,
            "que_hago",
            project_id=None,
            question=None,
            step_template_id=None,
            step_title="Categorización",
            fase_actual=None,
            concepto=None,
        )

    # Fallback stub triggered · NO coercitive text returned
    assert is_stub is True
    assert "Llevas" not in text
    assert "urgente" not in text.lower()
    assert "Categorización" in text


@pytest.mark.asyncio
async def test_generate_response_llm_success_clean_response(db):
    """LLM returns clean friendly response · R29 OK · is_stub=False."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    svc = CopilotClienteLLMService()
    mock_clean_response = (
        "¡Hola! Tu próximo paso es la categorización. Es como el DNI de tu "
        "proyecto ENS. Si tienes dudas · pregúntame · sin prisa · a tu ritmo."
    )

    with patch(
        "backend.app.agents.copilot_cliente_service.llm_enabled",
        return_value=True,
    ), patch.object(
        svc, "_call_llm", return_value=mock_clean_response,
    ):
        text, hint, is_stub = await svc.generate_response(
            db,
            "que_hago",
            project_id=pid,
            question=None,
            step_template_id=None,
            step_title="Categorización",
            fase_actual="dicat_categorizacion",
            concepto=None,
        )

    assert is_stub is False
    assert "DNI de tu proyecto ENS" in text
    assert hint == "Cuando termines · márcalo como hecho"
