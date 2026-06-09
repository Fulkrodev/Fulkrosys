"""Tests CopilotAdminLLMService swap-in + R30 boundary enforcement.

Sub-atom 1.D.B.2.1 v3.11.

Cobertura:
- check_r30_boundaries · detecta assume ENS knowledge patterns + jargon undefined
- enrich_response_defensive · agrega tip tutor footer cuando violations
- Service init · persona admin loaded · Sonnet 4.6 model
- generate_response: LLM disabled → stub directo
- generate_response: LLM enabled fail → graceful stub fallback
- generate_response: R30 violation → defensive enrich (NO full fallback)
- generate_response: clean LLM response → returned as-is
- _build_user_message · todos action_ids tutor cronológico tone
- Singleton getter
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from backend.app.agents.copilot_admin_service import (
    CopilotAdminLLMService,
    check_r30_boundaries,
    enrich_response_defensive,
    get_admin_llm_service,
)
from backend.tests.conftest import setup_test_project


# ════════════════════════════════════════════════════════════════════
# R30 boundary checks
# ════════════════════════════════════════════════════════════════════


def test_boundary_check_clean_admin_response_ok():
    text = (
        "Para este step necesitas crear el Documento de Aplicabilidad (DdA · "
        "es decir, el documento que define qué medidas ENS Anexo II aplicas a "
        "tu cliente). Empieza por listar las 73 medidas..."
    )
    is_clean, violations = check_r30_boundaries(text)
    assert is_clean is True
    assert violations == []


def test_boundary_check_detects_assume_ens_pattern():
    text = "Como ya sabes · el RD 311/2022 obliga a categorizar primero."
    is_clean, violations = check_r30_boundaries(text)
    assert is_clean is False
    assert any("assume_ens" in v for v in violations)


def test_boundary_check_detects_jargon_undefined():
    """Jargon ENS sin definition trigger en cercanía · violation."""
    text = "El siguiente paso es completar el DICAT y enviarlo al cliente."
    is_clean, violations = check_r30_boundaries(text)
    assert is_clean is False
    assert any("jargon_undefined" in v for v in violations)
    assert any("DICAT" in v for v in violations)


def test_boundary_check_jargon_with_definition_ok():
    """Jargon ENS con definition trigger nearby · NO violation."""
    text = (
        "El siguiente paso es completar el DICAT (que significa Declaración "
        "Inicial de Categorización) y enviarlo al cliente."
    )
    is_clean, violations = check_r30_boundaries(text)
    assert is_clean is True


def test_boundary_check_jargon_with_parenthesis_inline_definition():
    text = "MAGERIT (metodología análisis riesgos del Centro Criptológico)."
    is_clean, violations = check_r30_boundaries(text)
    assert is_clean is True


def test_boundary_check_combined_assume_and_jargon():
    text = "Como conoces · el ENAC valida la conformidad anualmente."
    is_clean, violations = check_r30_boundaries(text)
    assert is_clean is False
    # 1 assume violation detected · break optimization in code limits to 1
    assert len(violations) >= 1


def test_enrich_response_defensive_appends_tip():
    text = "Respuesta LLM original."
    enriched = enrich_response_defensive(text, ["assume_ens: 'como ya sabes'"])
    assert text in enriched
    assert "Tip tutor" in enriched
    assert "primer principios" in enriched


def test_enrich_response_defensive_no_violations_returns_original():
    text = "Respuesta limpia."
    enriched = enrich_response_defensive(text, [])
    assert enriched == text


# ════════════════════════════════════════════════════════════════════
# Service init + singleton
# ════════════════════════════════════════════════════════════════════


def test_service_init_loads_persona_admin():
    svc = CopilotAdminLLMService()
    assert svc.persona_service.role == "admin"
    assert svc.persona_service.citations_required is True
    assert svc.persona_service.model == "sonnet-4.6"


def test_get_admin_llm_service_singleton():
    svc1 = get_admin_llm_service()
    svc2 = get_admin_llm_service()
    assert svc1 is svc2


# ════════════════════════════════════════════════════════════════════
# User message building per action_id
# ════════════════════════════════════════════════════════════════════


def test_build_user_message_que_hago_admin():
    svc = CopilotAdminLLMService()
    msg = svc._build_user_message(
        "que_hago", None, "Fintech Plus", "DICAT", "dicat_categorizacion",
    )
    assert "Fintech Plus" in msg
    assert "DICAT" in msg
    assert "primer principios" in msg.lower()


def test_build_user_message_explica_paso_admin():
    svc = CopilotAdminLLMService()
    msg = svc._build_user_message(
        "explica_paso", None, "Cliente X", "PolÃticas firmadas", None,
    )
    assert "primer principios" in msg.lower()
    assert "RD 311/2022" in msg
    assert "CCN-STIC" in msg


def test_build_user_message_draft_email():
    svc = CopilotAdminLLMService()
    msg = svc._build_user_message(
        "draft_email", None, "ConsultorÃa TIC", "FormaciÃ³n G1", None,
    )
    assert "draft email" in msg.lower()
    assert "ConsultorÃa TIC" in msg
    assert "NO send" in msg or "solo draft" in msg.lower()


def test_build_user_message_briefing_reunion():
    svc = CopilotAdminLLMService()
    msg = svc._build_user_message(
        "briefing_reunion", None, "Cliente Z", "MAGERIT", "analisis_riesgos_dda",
    )
    assert "briefing" in msg.lower()
    assert "talking points" in msg.lower()


def test_build_user_message_chat_send_uses_question():
    svc = CopilotAdminLLMService()
    msg = svc._build_user_message(
        "chat_send", "¿Cómo gestiono retainer?", None, None, None,
    )
    assert msg == "¿Cómo gestiono retainer?"


# ════════════════════════════════════════════════════════════════════
# Generate response flow
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_generate_response_llm_disabled_fallback_stub(db):
    svc = CopilotAdminLLMService()

    with patch(
        "backend.app.agents.copilot_admin_service.llm_enabled",
        return_value=False,
    ):
        text, hint, is_stub = await svc.generate_response(
            db,
            "que_hago",
            project_id=None,
            project_nombre="Fintech Plus",
            question=None,
            step_template_id=None,
            step_title="DICAT",
            fase_actual=None,
        )

    assert is_stub is True
    assert "Fintech Plus" in text
    assert "DICAT" in text


@pytest.mark.asyncio
async def test_generate_response_llm_error_graceful_fallback(db):
    svc = CopilotAdminLLMService()

    with patch(
        "backend.app.agents.copilot_admin_service.llm_enabled",
        return_value=True,
    ), patch.object(
        svc, "_call_llm", side_effect=Exception("Mock LLM failure"),
    ):
        text, hint, is_stub = await svc.generate_response(
            db,
            "explica_paso",
            project_id=None,
            project_nombre="Cliente X",
            question=None,
            step_template_id=None,
            step_title="MAGERIT",
            fase_actual=None,
        )

    assert is_stub is True
    assert "MAGERIT" in text


@pytest.mark.asyncio
async def test_generate_response_r30_violation_defensive_enrich(db):
    """R30 violation → enrich con tip tutor footer (NO full stub fallback)."""
    svc = CopilotAdminLLMService()
    violating_response = (
        "Como ya sabes el ENS Anexo II requiere medidas específicas..."
    )

    with patch(
        "backend.app.agents.copilot_admin_service.llm_enabled",
        return_value=True,
    ), patch.object(
        svc, "_call_llm", return_value=violating_response,
    ):
        text, hint, is_stub = await svc.generate_response(
            db,
            "explica_paso",
            project_id=None,
            project_nombre=None,
            question=None,
            step_template_id=None,
            step_title="DdA",
            fase_actual=None,
        )

    # Defensive enrich · is_stub=False (admin sostiene latency) · footer tutor
    assert is_stub is False
    assert "Como ya sabes" in text  # original preserved
    assert "Tip tutor" in text  # footer enriched
    assert "primer principios" in text.lower()


@pytest.mark.asyncio
async def test_generate_response_llm_success_clean_response(db):
    """Clean LLM response (no R30 violations) · returned as-is."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    svc = CopilotAdminLLMService()
    clean_response = (
        "El siguiente paso del cliente es el DdA · que significa "
        "Declaración de Aplicabilidad · es decir el documento donde "
        "definimos qué medidas de seguridad aplican al proyecto."
    )

    with patch(
        "backend.app.agents.copilot_admin_service.llm_enabled",
        return_value=True,
    ), patch.object(
        svc, "_call_llm", return_value=clean_response,
    ):
        text, hint, is_stub = await svc.generate_response(
            db,
            "explica_paso",
            project_id=pid,
            project_nombre="Test Cliente",
            question=None,
            step_template_id=None,
            step_title="DdA",
            fase_actual="analisis_riesgos_dda",
        )

    assert is_stub is False
    assert "DdA" in text
    assert "Tip tutor" not in text  # NO enrich · response was already clean
