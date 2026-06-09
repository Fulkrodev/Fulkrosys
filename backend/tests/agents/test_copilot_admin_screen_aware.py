"""Tests CopilotAdminLLMService screen-aware context · sub-atom 1.D.F.0.D v3.11.

Cobertura:
- Catalog screen_references_catalog persona admin loaded
- normalize_screen_pattern · UUID → [id] pattern
- lookup_screen_reference · match · no-match · None safe
- build_admin_context inyecta current_screen_context + current_screen_actions
- generate_response propaga current_screen + active_motor
- Persona admin referencia botones específicos cuando screen identificada
- Cliente persona NO consume screen_references (admin-only · scope-out)
- Empty path safe behavior (sin screen activa)
- NO agentic destructive · R32 sostener
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.app.agents.copilot_admin_service import CopilotAdminLLMService
from backend.app.agents.copilot_persona_service import CopilotPersonaService
from backend.app.agents.copilot_personas_loader import (
    get_persona,
    load_catalog,
    lookup_screen_reference,
    normalize_screen_pattern,
)


# ════════════════════════════════════════════════════════════════════
# Catalog presence
# ════════════════════════════════════════════════════════════════════


def test_admin_persona_has_screen_references_catalog():
    """Catalog YAML admin includes screen_references entries 1.D.F.0.D."""
    persona = get_persona("admin")
    # Sub-atom 1.D.F.bis.E v3.11 · catalog extended 12 → 38 screens
    # (fix path mismatches detectados audit: evidencias→evidence ·
    # dossier-enac→dossier · cambios→changes · add 25 motors restantes)
    assert len(persona.screen_references_catalog) >= 35
    screens = {entry.screen for entry in persona.screen_references_catalog}
    # Core ENS flow
    assert "/admin/projects/[id]/dda" in screens
    assert "/admin/projects/[id]/magerit" in screens
    assert "/admin/projects/[id]/dimensiones" in screens
    assert "/admin/projects/[id]/evidence" in screens  # fix · NOT evidencias
    assert "/admin/projects/[id]/dossier" in screens  # fix · NOT dossier-enac
    assert "/admin/projects/[id]/conformity" in screens
    # MCPs · contracts · changes
    assert "/admin/projects/[id]/mcps" in screens
    assert "/admin/projects/[id]/contratos" in screens
    assert "/admin/projects/[id]/changes" in screens  # fix · NOT cambios
    # Team · roles · planes
    assert "/admin/projects/[id]/equipo" in screens
    assert "/admin/projects/[id]/roles" in screens
    assert "/admin/projects/[id]/planes-accion" in screens


def test_admin_persona_screen_entries_structure():
    persona = get_persona("admin")
    dda_entry = next(
        e for e in persona.screen_references_catalog
        if e.screen == "/admin/projects/[id]/dda"
    )
    assert dda_entry.screen_name
    assert dda_entry.motor == "m03_dda"
    assert len(dda_entry.actions) >= 2
    assert dda_entry.context_hints


def test_cliente_persona_omits_admin_screen_references():
    """Cliente persona NO incluye admin screen entries · R30 inverso sostener.

    Post 1.D.X.VERIFY 2b (commit 2a8f5db) cliente persona ahora puede tener
    cliente-facing screen entries (digest mensual retainer-checkin · R29
    friendly). R30 inverso invariant: NUNCA admin screens (/admin/* paths)
    leak en cliente persona catalog.

    Future-1.E.copilot-test-refresh · invariant refined post YAML extension.
    """
    persona = get_persona("cliente")
    # Cualquier entry debe ser cliente-facing · NO admin paths
    for entry in persona.screen_references_catalog:
        assert not entry.screen.startswith("/admin/"), (
            f"R30 inverso violado · cliente persona screen catalog leak admin path: "
            f"{entry.screen}"
        )
        assert (
            entry.screen == "/client-portal"
            or entry.screen.startswith("/client-portal/")
            or entry.screen.startswith("/portal/")
        ), (
            f"Cliente persona entry NO cliente-portal-scoped: {entry.screen}"
        )


# ════════════════════════════════════════════════════════════════════
# normalize_screen_pattern · UUID → [id]
# ════════════════════════════════════════════════════════════════════


def test_normalize_screen_pattern_admin_projects_uuid_to_id():
    assert (
        normalize_screen_pattern("/admin/projects/abc-uuid-123/dda")
        == "/admin/projects/[id]/dda"
    )


def test_normalize_screen_pattern_workflow_command_center_uuid_to_id():
    assert (
        normalize_screen_pattern(
            "/admin/workflow-command-center/projects/abc-uuid-123",
        )
        == "/admin/workflow-command-center/projects/[id]"
    )


def test_normalize_screen_pattern_no_match_returns_original():
    """Pathname fuera project-scoped pattern · NO normalize · pass-through."""
    pathname = "/admin/dashboard"
    assert normalize_screen_pattern(pathname) == pathname


def test_normalize_screen_pattern_handles_uuid_format():
    """UUID v4 format normalized correctly."""
    pathname = (
        "/admin/projects/550e8400-e29b-41d4-a716-446655440000/mcps"
    )
    assert (
        normalize_screen_pattern(pathname)
        == "/admin/projects/[id]/mcps"
    )


def test_normalize_screen_pattern_strips_trailing_slash():
    """Catalog patterns son sin trailing slash · normalize debe match."""
    pathname = "/admin/projects/abc-uuid/dda/"
    assert (
        normalize_screen_pattern(pathname) == "/admin/projects/[id]/dda"
    )


# ════════════════════════════════════════════════════════════════════
# lookup_screen_reference
# ════════════════════════════════════════════════════════════════════


def test_lookup_screen_reference_match_dda():
    persona = get_persona("admin")
    ref = lookup_screen_reference(
        persona, "/admin/projects/some-uuid/dda",
    )
    assert ref is not None
    assert ref.motor == "m03_dda"
    assert any("evidencia" in a.lower() for a in ref.actions)


def test_lookup_screen_reference_match_mcps():
    persona = get_persona("admin")
    ref = lookup_screen_reference(
        persona, "/admin/projects/abc/mcps",
    )
    assert ref is not None
    assert ref.motor == "m08_verification"
    assert any("nuclei" in a.lower() for a in ref.actions)


def test_lookup_screen_reference_no_match_returns_none():
    persona = get_persona("admin")
    ref = lookup_screen_reference(persona, "/admin/dashboard")
    assert ref is None


def test_lookup_screen_reference_none_path_returns_none():
    persona = get_persona("admin")
    assert lookup_screen_reference(persona, None) is None


def test_lookup_screen_reference_empty_string_returns_none():
    persona = get_persona("admin")
    assert lookup_screen_reference(persona, "") is None


# ════════════════════════════════════════════════════════════════════
# build_admin_context · screen injection
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_build_admin_context_includes_current_screen_when_provided(db):
    svc = CopilotPersonaService("admin")
    ctx = await svc.build_admin_context(
        db,
        active_project_id=None,
        active_project_name="Fintech Plus",
        active_step_title="DICAT",
        active_fase=None,
        current_screen="/admin/projects/abc/dda",
        active_motor=None,
    )
    assert "current_screen_context" in ctx
    assert "Declaración de Aplicabilidad" in ctx["current_screen_context"]
    assert "current_screen_actions" in ctx
    assert "Marcar medida implementada" in ctx["current_screen_actions"]


@pytest.mark.asyncio
async def test_build_admin_context_without_screen_safe_defaults(db):
    svc = CopilotPersonaService("admin")
    ctx = await svc.build_admin_context(
        db,
        active_project_id=None,
        active_project_name=None,
        current_screen=None,
    )
    assert "sin pantalla activa" in ctx["current_screen_context"]
    assert "guidance conceptual general" in ctx["current_screen_actions"]


@pytest.mark.asyncio
async def test_build_admin_context_active_motor_override_screen_motor(db):
    """active_motor override permite override label motor catalog (debug · custom)."""
    svc = CopilotPersonaService("admin")
    ctx = await svc.build_admin_context(
        db,
        current_screen="/admin/projects/abc/dda",
        active_motor="motor_override_test",
    )
    assert "motor_override_test" in ctx["current_screen_context"]


@pytest.mark.asyncio
async def test_build_admin_context_unknown_screen_safe_defaults(db):
    svc = CopilotPersonaService("admin")
    ctx = await svc.build_admin_context(
        db,
        current_screen="/admin/unknown-route",
    )
    assert "sin pantalla activa" in ctx["current_screen_context"]


# ════════════════════════════════════════════════════════════════════
# generate_response propaga screen context
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_generate_response_propagates_current_screen_to_context(db):
    """LLM mock recibe system prompt con screen-specific actions injected."""
    svc = CopilotAdminLLMService()
    captured_prompts: list[str] = []

    async def fake_call_llm(system_prompt, user_message, db_, project_id, history=None):
        captured_prompts.append(system_prompt)
        return "Respuesta tutor mock"

    with patch(
        "backend.app.agents.copilot_admin_service.llm_enabled",
        return_value=True,
    ), patch.object(svc, "_call_llm", side_effect=fake_call_llm):
        await svc.generate_response(
            db,
            "que_hago",
            project_id=None,
            project_nombre="Cliente X",
            question=None,
            step_template_id=None,
            step_title="DdA",
            fase_actual=None,
            current_screen="/admin/projects/abc/dda",
        )

    assert len(captured_prompts) == 1
    prompt = captured_prompts[0]
    # Screen-specific button references injected en system prompt
    assert "Declaración de Aplicabilidad" in prompt
    assert "Marcar medida implementada" in prompt


@pytest.mark.asyncio
async def test_generate_response_screen_switch_updates_context(db):
    """Cambio de screen entre calls actualiza context injection."""
    svc = CopilotAdminLLMService()
    captured: list[str] = []

    async def fake_call_llm(system_prompt, user_message, db_, project_id, history=None):
        captured.append(system_prompt)
        return "OK"

    with patch(
        "backend.app.agents.copilot_admin_service.llm_enabled",
        return_value=True,
    ), patch.object(svc, "_call_llm", side_effect=fake_call_llm):
        # Call 1 · DdA screen
        await svc.generate_response(
            db,
            "que_hago",
            project_id=None,
            project_nombre=None,
            question=None,
            step_template_id=None,
            step_title=None,
            fase_actual=None,
            current_screen="/admin/projects/abc/dda",
        )
        # Call 2 · MCPs screen
        await svc.generate_response(
            db,
            "que_hago",
            project_id=None,
            project_nombre=None,
            question=None,
            step_template_id=None,
            step_title=None,
            fase_actual=None,
            current_screen="/admin/projects/abc/mcps",
        )

    assert len(captured) == 2
    assert "Declaración de Aplicabilidad" in captured[0]
    assert "Pentest MCPs" in captured[1]
    # Cross-validate · prompts diferentes per screen
    assert captured[0] != captured[1]


@pytest.mark.asyncio
async def test_generate_response_no_screen_safe_default_in_prompt(db):
    """Sin current_screen · system prompt incluye safe default fallback."""
    svc = CopilotAdminLLMService()
    captured: list[str] = []

    async def fake_call_llm(system_prompt, user_message, db_, project_id, history=None):
        captured.append(system_prompt)
        return "OK"

    with patch(
        "backend.app.agents.copilot_admin_service.llm_enabled",
        return_value=True,
    ), patch.object(svc, "_call_llm", side_effect=fake_call_llm):
        await svc.generate_response(
            db,
            "que_hago",
            project_id=None,
            project_nombre=None,
            question=None,
            step_template_id=None,
            step_title=None,
            fase_actual=None,
            current_screen=None,
        )

    assert "sin pantalla activa" in captured[0]


# ════════════════════════════════════════════════════════════════════
# R32 sostener · NO agentic destructive
# ════════════════════════════════════════════════════════════════════


def test_admin_persona_forbids_agentic_destructive_actions():
    """R32 v3.11 sostener · admin persona declara NO destructive agentic."""
    persona = get_persona("admin")
    forbidden_concat = " ".join(persona.scope_boundaries_forbidden).lower()
    assert (
        "no ejecuta acciones destructivas" in forbidden_concat
        or "no agentic actions destructiv" in forbidden_concat
    )


def test_catalog_actions_are_suggestions_not_destructive_commands():
    """Catalog actions describen botones UI · NO comandos destructivos remotos."""
    persona = get_persona("admin")
    for entry in persona.screen_references_catalog:
        for action in entry.actions:
            action_lower = action.lower()
            # NO autonomous "delete all" · "wipe" · "destroy" · etc.
            assert "wipe" not in action_lower
            assert "destroy" not in action_lower
            assert "delete all" not in action_lower
            assert "rm -rf" not in action_lower


# ════════════════════════════════════════════════════════════════════
# Catalog full coverage smoke
# ════════════════════════════════════════════════════════════════════


def test_catalog_load_fresh_from_yaml():
    """Catalog YAML loads fresh · sanity full structure."""
    catalog = load_catalog(use_cache=False)
    assert "admin" in catalog.personas
    admin_persona = catalog.personas["admin"]
    assert len(admin_persona.screen_references_catalog) >= 10
