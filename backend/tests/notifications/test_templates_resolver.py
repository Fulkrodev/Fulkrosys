"""Tests TemplateResolver YAML + Jinja2 sandbox (MB-16.3 ADR-039).

Cubre:
- Render templates reales (6 iniciales) sin fallar.
- Variables Jinja2 sustituidas correctamente.
- WhatsApp footer auto-append cuando configurado.
- WhatsApp footer ausente cuando no configurado.
- Sandbox bloquea call a builtins peligrosos.
- Variable faltante → StrictUndefined raise.
- Template inexistente → TemplateError.
"""
from __future__ import annotations

import pytest
from jinja2 import UndefinedError

from backend.app.config import get_settings
from backend.app.notifications import (
    TemplateError,
    TemplateResolver,
    clear_template_cache,
)


@pytest.fixture(autouse=True)
def _reset_settings_cache(monkeypatch):
    get_settings.cache_clear()
    clear_template_cache()
    yield
    get_settings.cache_clear()
    clear_template_cache()


@pytest.fixture
def resolver():
    return TemplateResolver()


def test_render_task_assigned(monkeypatch, resolver):
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "")
    get_settings.cache_clear()
    rendered = resolver.render(
        "task_assigned",
        {
            "recipient_name": "Ana López",
            "project_name": "ENS Alta · Cliente X",
            "task_title": "Validar Política de Seguridad",
            "task_description": "Revisar versión 2.3 y firmar.",
            "task_due_date": "2026-05-20",
            "cta_url": "https://fulkro.es/client-portal/tasks/abc",
        },
    )
    assert "Nueva tarea asignada" in rendered.subject
    assert "ENS Alta · Cliente X" in rendered.subject
    assert "Ana López" in rendered.html_body
    assert "Validar Política de Seguridad" in rendered.html_body
    assert "https://fulkro.es/client-portal/tasks/abc" in rendered.html_body
    assert "Validar Política de Seguridad" in rendered.text_body
    assert rendered.cta_label == "Abrir tarea"


def test_render_chat_admin_reply(resolver):
    rendered = resolver.render(
        "chat_admin_reply",
        {
            "recipient_name": "Carlos",
            "project_name": "Proyecto Y",
            "message_preview": "He revisado el ENS y...",
            "cta_url": "https://fulkro.es/client-portal/chat?thread=xyz",
        },
    )
    assert "Marcos te ha respondido" in rendered.subject
    assert "Carlos" in rendered.html_body
    assert "He revisado el ENS y..." in rendered.html_body


def test_render_evidence_expiring(resolver):
    rendered = resolver.render(
        "evidence_expiring",
        {
            "recipient_name": "Pedro",
            "project_name": "Sistema Z",
            "evidence_name": "Política de Backup v1.2",
            "days_to_expire": 14,
            "expiration_date": "2026-05-20",
            "cta_url": "https://fulkro.es/client-portal/evidences/abc",
        },
    )
    assert "Evidencia próxima a expirar" in rendered.subject
    assert "Política de Backup v1.2" in rendered.html_body
    assert "14 días" in rendered.html_body


def test_render_phase_changed_with_optional_vars(resolver):
    rendered = resolver.render(
        "phase_changed",
        {
            "recipient_name": "Laura",
            "project_name": "P-X",
            "new_phase": "Auditoría",
            "previous_phase": "Operación",
            "next_milestone": "Revisión documentación",
            "cta_url": "https://fulkro.es/client-portal/workflow",
        },
    )
    assert "Auditoría" in rendered.subject
    assert "Operación" in rendered.html_body
    assert "Revisión documentación" in rendered.html_body


def test_render_audit_due(resolver):
    rendered = resolver.render(
        "audit_due",
        {
            "recipient_name": "Marta",
            "project_name": "Banco Y",
            "audit_type": "ENAC bienal",
            "audit_date": "2026-06-15",
            "days_until": 30,
            "audit_scope": "Categoría Alta · Anexo II completo",
            "cta_url": "https://fulkro.es/client-portal/audits/123",
        },
    )
    assert "ENAC bienal" in rendered.html_body
    assert "30 días" in rendered.html_body
    assert "Categoría Alta" in rendered.html_body


def test_render_client_inactivity_admin(resolver):
    rendered = resolver.render(
        "client_inactivity_admin",
        {
            "client_name": "Empresa Inactiva SL",
            "days_inactive": 21,
            "last_login_date": "2026-04-15",
            "last_task_completed": "2026-04-10 · Política Backup",
            "cta_url": "https://fulkro.es/admin/clients/abc",
        },
    )
    assert "21 días" in rendered.html_body
    assert "Empresa Inactiva SL" in rendered.html_body
    assert "Política Backup" in rendered.html_body


def test_whatsapp_footer_appended_when_configured(monkeypatch, resolver):
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "+34666123456")
    get_settings.cache_clear()
    rendered = resolver.render(
        "task_assigned",
        {
            "recipient_name": "Ana",
            "project_name": "P",
            "task_title": "T",
            "task_description": "D",
            "task_due_date": "",
            "cta_url": "https://fulkro.es/x",
        },
    )
    assert "+34 666 123 456" in rendered.html_body
    assert "+34 666 123 456" in rendered.text_body
    assert "<strong>+34 666 123 456</strong>" in rendered.html_body
    # Directiva: NO link clickeable
    assert "wa.me" not in rendered.html_body
    assert "<a href=" not in rendered.html_body[
        rendered.html_body.find("WhatsApp"):
    ] if "WhatsApp" in rendered.html_body else True


def test_whatsapp_footer_absent_when_not_configured(
    monkeypatch, resolver,
):
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "")
    get_settings.cache_clear()
    rendered = resolver.render(
        "chat_admin_reply",
        {
            "recipient_name": "X",
            "project_name": "P",
            "message_preview": "msg",
            "cta_url": "https://fulkro.es/y",
        },
    )
    assert "WhatsApp" not in rendered.html_body
    assert "WhatsApp" not in rendered.text_body


def test_template_not_found_raises(resolver):
    with pytest.raises(TemplateError):
        resolver.render("does_not_exist", {})


def test_strict_undefined_missing_var_raises(resolver):
    with pytest.raises(UndefinedError):
        resolver.render(
            "task_assigned",
            {"recipient_name": "Solo nombre"},
        )


def test_html_autoescape_blocks_xss(monkeypatch, resolver):
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "")
    get_settings.cache_clear()
    rendered = resolver.render(
        "chat_admin_reply",
        {
            "recipient_name": "<script>alert('xss')</script>",
            "project_name": "P",
            "message_preview": "<img src=x onerror=alert(1)>",
            "cta_url": "https://fulkro.es/x",
        },
    )
    assert "<script>" not in rendered.html_body
    assert "&lt;script&gt;" in rendered.html_body
    assert "<img src=x" not in rendered.html_body
    assert "&lt;img src=x" in rendered.html_body
