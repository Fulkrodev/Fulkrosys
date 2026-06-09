"""Tests copilot personas loader + service · sub-atom 1.D.B.0.1 v3.10.

Cobertura:
- Loader · YAML parse + schema validation + cache singleton
- Get persona · cliente · admin · invalid role
- Build system prompt · placeholders rendered correctly · safe defaults
- Service · context builders cliente + admin
- Boundary checks · R29 (cliente sin coercitive) + R30 (admin asume cero ENS)
  visible en system_prompt rendered (audit empírico template)
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.agents.copilot_persona_service import CopilotPersonaService
from backend.app.agents.copilot_personas_loader import (
    CopilotPersonasLoadError,
    build_system_prompt,
    get_persona,
    load_catalog,
)
from backend.tests.conftest import setup_test_project


# ════════════════════════════════════════════════════════════════════
# Loader tests
# ════════════════════════════════════════════════════════════════════


def test_load_catalog_parses_yaml_successfully():
    """YAML carga + valida schema · personas cliente + admin presentes."""
    catalog = load_catalog(use_cache=False)
    assert catalog.version == "1.0"
    assert "cliente" in catalog.personas
    assert "admin" in catalog.personas
    assert catalog.metadata.subatom == "1.D.B.0"


def test_get_persona_cliente_returns_correct_persona():
    cliente = get_persona("cliente")
    assert "cliente" in cliente.identity.lower() or "tutor" in cliente.identity.lower()
    assert cliente.temperature == pytest.approx(0.2)
    assert cliente.max_tokens == 1500
    assert cliente.citations_required is False
    # R29 sostener · boundaries forbidden include presión coercitiva
    forbidden_joined = " ".join(cliente.scope_boundaries_forbidden).lower()
    assert "coercitiva" in forbidden_joined or "presión" in forbidden_joined


def test_get_persona_admin_returns_correct_persona():
    admin = get_persona("admin")
    assert admin.temperature == pytest.approx(0.15)
    assert admin.max_tokens == 2500
    assert admin.citations_required is True  # admin needs ENAC-ready citations
    # R30 sostener · template asume cero ENS visible
    assert "cero ENS" in admin.system_prompt_template or "R30" in admin.system_prompt_template


def test_get_persona_invalid_role_raises():
    with pytest.raises(CopilotPersonasLoadError):
        get_persona("invalid_role")  # type: ignore[arg-type]


# ════════════════════════════════════════════════════════════════════
# System prompt rendering tests
# ════════════════════════════════════════════════════════════════════


def test_build_system_prompt_cliente_with_context():
    cliente = get_persona("cliente")
    rendered = build_system_prompt(cliente, {
        "client_company": "Fintech Plus SL",
        "project_category": "MEDIA",
        "project_context": "Proyecto: Fintech Plus · Fase: adecuacion · Categoría ENS: MEDIA",
        "current_step_context": "Step 7: PolíticasFirmadas",
    })
    assert "Fintech Plus SL" in rendered
    assert "MEDIA" in rendered
    assert "PolíticasFirmadas" in rendered
    # R29 sostener empírico · template incluye reglas anti-coercitivas
    assert "R29" in rendered or "coercitiva" in rendered.lower()


def test_build_system_prompt_admin_with_context():
    admin = get_persona("admin")
    rendered = build_system_prompt(admin, {
        "portfolio_context": "Portfolio activo: 4 cliente(s)",
        "active_client_context": "Cliente: Fintech Plus · Fase: adecuacion",
    })
    assert "Portfolio activo" in rendered
    assert "Fintech Plus" in rendered
    # R30 sostener · template asume cero ENS Marcos
    assert "cero ENS" in rendered or "R30" in rendered


def test_build_system_prompt_safe_defaults_when_context_missing():
    """Missing placeholders fallback to '(no disponible)' · NO KeyError."""
    cliente = get_persona("cliente")
    rendered = build_system_prompt(cliente, {})
    # Template renders sin crash · placeholders defaults
    assert "(empresa cliente)" in rendered or "no disponible" in rendered


# ════════════════════════════════════════════════════════════════════
# Service tests · context builders + persona accessors
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_service_cliente_role_init_loads_persona():
    svc = CopilotPersonaService("cliente")
    assert svc.role == "cliente"
    assert svc.model == "sonnet-4.6"
    assert svc.temperature == pytest.approx(0.2)
    assert svc.citations_required is False


@pytest.mark.asyncio
async def test_service_admin_role_init_loads_persona():
    svc = CopilotPersonaService("admin")
    assert svc.role == "admin"
    assert svc.model == "sonnet-4.6"
    assert svc.temperature == pytest.approx(0.15)
    assert svc.citations_required is True


@pytest.mark.asyncio
async def test_service_build_client_context_with_project(db):
    """build_client_context fetcha project info · build context dict."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    svc = CopilotPersonaService("cliente")
    ctx = await svc.build_client_context(
        db, pid, step_title="Test step title", fase_actual="adecuacion",
    )
    assert "client_company" in ctx
    assert "project_category" in ctx
    assert "project_context" in ctx
    assert "Test step title" in ctx["current_step_context"]


@pytest.mark.asyncio
async def test_service_build_admin_context_portfolio_summary(db):
    """build_admin_context resumen portfolio + cliente activo opcional."""
    svc = CopilotPersonaService("admin")
    ctx = await svc.build_admin_context(
        db,
        active_project_name="Fintech Plus",
        active_fase="adecuacion",
        active_step_title="Step 7",
    )
    assert "portfolio_context" in ctx
    assert "active_client_context" in ctx
    assert "Fintech Plus" in ctx["active_client_context"]
    assert "Step 7" in ctx["active_client_context"]


@pytest.mark.asyncio
async def test_service_role_mismatch_raises():
    """Service cliente NO puede build admin context · cross-boundary enforce."""
    svc_cliente = CopilotPersonaService("cliente")
    with pytest.raises(ValueError):
        await svc_cliente.build_admin_context(None)  # type: ignore[arg-type]

    svc_admin = CopilotPersonaService("admin")
    with pytest.raises(ValueError):
        await svc_admin.build_client_context(None, None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_service_render_system_prompt_end_to_end(db):
    """End-to-end · service build context + render prompt completo."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    svc = CopilotPersonaService("cliente")
    ctx = await svc.build_client_context(db, pid, step_title="Categorización")
    rendered = svc.render_system_prompt(ctx)
    assert "Categorización" in rendered
    # R29 boundary sostener empírico
    assert "R29" in rendered or "coercitiva" in rendered.lower()
