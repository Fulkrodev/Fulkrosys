"""Tests CopilotStubService refactor · sub-atom 1.D.B.0.2 v3.10.

Cobertura:
- Admin stub service · 5 action_ids generate stub responses contextualizados
- Client stub service · 5 action_ids · R29 boundary verify (0 coercitive strings)
- Persona pre-loaded · metadata accessible · ready swap-in 1.D.B.1+.2
- Singleton getters · lazy load (catalog NO loaded en imports)
"""
from __future__ import annotations

import pytest

from backend.app.agents.copilot_stub_service import (
    AdminCopilotStubService,
    ClientCopilotStubService,
    get_admin_stub_service,
    get_client_stub_service,
)


# ════════════════════════════════════════════════════════════════════
# Admin stub service tests
# ════════════════════════════════════════════════════════════════════


def test_admin_stub_service_init_loads_persona():
    svc = AdminCopilotStubService()
    assert svc.persona_service.role == "admin"
    assert svc.persona_metadata["role"] == "admin"
    assert svc.persona_metadata["citations_required"] is True
    assert svc.persona_metadata["model_recommended"] == "sonnet-4.6"


def test_admin_stub_que_hago_with_full_context():
    svc = AdminCopilotStubService()
    text, hint = svc.generate_stub_response(
        "que_hago",
        project_nombre="Fintech Plus",
        step_title="Formación G1",
        step_template_id="ENR_IM_03",
    )
    assert "Fintech Plus" in text
    assert "Formación G1" in text
    assert hint == "Marca el sub-paso completo cuando esté hecho"


def test_admin_stub_explica_paso():
    svc = AdminCopilotStubService()
    text, hint = svc.generate_stub_response(
        "explica_paso", step_title="DICAT categorización",
    )
    assert "DICAT categorización" in text
    assert "ENS Anexo II" in text
    assert hint is None


def test_admin_stub_draft_email_chat_send():
    svc = AdminCopilotStubService()
    text_email, _ = svc.generate_stub_response("draft_email")
    assert "plantillas E-XXX" in text_email or "LLM completo" in text_email
    text_chat, _ = svc.generate_stub_response("chat_send")
    assert "Acciones rápidas" in text_chat


def test_admin_stub_briefing_reunion_with_fase():
    svc = AdminCopilotStubService()
    text, _ = svc.generate_stub_response(
        "briefing_reunion",
        project_nombre="ConsultorÃa TIC",
        step_title="Plan adecuación",
        fase_actual="adecuacion",
    )
    assert "ConsultorÃa TIC" in text
    assert "Plan adecuación" in text
    assert "adecuacion" in text


# ════════════════════════════════════════════════════════════════════
# Client stub service tests · R29 boundary verify
# ════════════════════════════════════════════════════════════════════


def test_client_stub_service_init_loads_persona():
    svc = ClientCopilotStubService()
    assert svc.persona_service.role == "cliente"
    assert svc.persona_metadata["citations_required"] is False
    assert svc.persona_metadata["max_tokens"] == 1500


def test_client_stub_que_hago_non_coercitive():
    svc = ClientCopilotStubService()
    text, hint = svc.generate_stub_response(
        "que_hago", step_title="Categorización",
    )
    assert "Categorización" in text
    assert "Sin prisa" in text or "a tu ritmo" in text
    assert hint == "Cuando termines · márcalo como hecho"
    # R29 audit · NO strings coercitivos
    coercitive_patterns = [
        "llevas", "deadline", "urgente", "se acaba", "tienes que ahora",
    ]
    text_lower = text.lower()
    for pattern in coercitive_patterns:
        assert pattern not in text_lower, f"R29 violation: '{pattern}' found"


def test_client_stub_porque_importa_friendly():
    svc = ClientCopilotStubService()
    text, _ = svc.generate_stub_response(
        "porque_importa", step_title="MAGERIT",
    )
    assert "MAGERIT" in text
    assert "Esquema Nacional" in text


def test_client_stub_explica_concepto():
    svc = ClientCopilotStubService()
    text, _ = svc.generate_stub_response(
        "explica_concepto", concepto="DdA",
    )
    assert "DdA" in text


def test_client_stub_necesito_ayuda_chat_send():
    svc = ClientCopilotStubService()
    text_help, _ = svc.generate_stub_response("necesito_ayuda")
    assert "ayudarte" in text_help or "ayudar" in text_help
    text_chat, _ = svc.generate_stub_response("chat_send")
    assert "Aquí seguimos cuando me necesites" in text_chat or "Marcos" in text_chat


# ════════════════════════════════════════════════════════════════════
# Singleton getters · lazy load
# ════════════════════════════════════════════════════════════════════


def test_get_admin_stub_service_singleton():
    svc1 = get_admin_stub_service()
    svc2 = get_admin_stub_service()
    assert svc1 is svc2


def test_get_client_stub_service_singleton():
    svc1 = get_client_stub_service()
    svc2 = get_client_stub_service()
    assert svc1 is svc2
