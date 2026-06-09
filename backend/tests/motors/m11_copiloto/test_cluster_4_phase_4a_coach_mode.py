"""CLUSTER 4 Phase 4A · LLM coach mode upgrade tests.

Sesión 3B-2B.8 CLUSTER 4 Phase 4A · PageContext.coach_mode injection +
_build_system_prompt coach guidance + 2 endpoints (POST coach + GET next-step).

Coverage:
- PageContext coach fields backward-compat default
- _build_system_prompt injects coach guidance cuando coach_mode=True
- _build_system_prompt NO coach guidance cuando coach_mode=False (default)
- coach guidance template contiene R29 firmísimo phrases
- Stack with category guidance Phase 2E + coach guidance Phase 4A coexisten

Pattern 21 cumulative formalized: Coach context injection pattern (PageContext
coach_mode + system prompt enrichment + deterministic O(1) next-step compose
sin LLM call).
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.agents.agent_14_copiloto.service import _build_system_prompt
from backend.app.agents.agent_14_copiloto.types import PageContext


# ════════════════════════════════════════════════════════════════════
# Phase 4A.1 · PageContext coach fields backward-compat
# ════════════════════════════════════════════════════════════════════


def test_page_context_coach_mode_default_false():
    """PageContext coach_mode default False (backward-compat)."""
    pc = PageContext()
    assert pc.coach_mode is False
    assert pc.coach_current_phase is None
    assert pc.coach_pending_action is None


def test_page_context_coach_fields_set_explicit():
    """coach_mode + coach_current_phase + coach_pending_action set explicit."""
    pc = PageContext(
        coach_mode=True,
        coach_current_phase="ADECUACION",
        coach_pending_action="Firmar DdA",
    )
    assert pc.coach_mode is True
    assert pc.coach_current_phase == "ADECUACION"
    assert pc.coach_pending_action == "Firmar DdA"


# ════════════════════════════════════════════════════════════════════
# Phase 4A.1 · _build_system_prompt coach injection
# ════════════════════════════════════════════════════════════════════


def test_build_system_prompt_no_coach_when_default():
    """Sin coach_mode · system prompt sin sección coach (backward-compat)."""
    pc = PageContext(url="/client-portal/dashboard")
    prompt = _build_system_prompt(pc, corpus_gap=False)
    assert "## Modo coach activo" not in prompt


def test_build_system_prompt_injects_coach_when_active():
    """coach_mode=True · prompt incluye sección coach guidance R29."""
    pc = PageContext(
        coach_mode=True,
        coach_current_phase="IMPLANTACION",
        coach_pending_action="Subir política de accesos",
    )
    prompt = _build_system_prompt(pc, corpus_gap=False)
    assert "## Modo coach activo" in prompt
    assert "IMPLANTACION" in prompt
    assert "Subir política de accesos" in prompt
    assert "Sin prisa" in prompt
    assert "primer-principios" in prompt
    assert "Marcos owns content" in prompt or "Marcos owns" in prompt


def test_build_system_prompt_coach_handles_missing_pending_action():
    """coach_mode=True sin pending_action · prompt usa fallback friendly."""
    pc = PageContext(
        coach_mode=True,
        coach_current_phase="ALCANCE",
        coach_pending_action=None,
    )
    prompt = _build_system_prompt(pc, corpus_gap=False)
    assert "## Modo coach activo" in prompt
    assert "ALCANCE" in prompt
    assert "sin prisa por tu parte" in prompt.lower()


def test_build_system_prompt_coach_default_phase_when_none():
    """coach_mode=True sin current_phase · usa 'actual' fallback."""
    pc = PageContext(
        coach_mode=True,
        coach_current_phase=None,
        coach_pending_action="Aprobar plan",
    )
    prompt = _build_system_prompt(pc, corpus_gap=False)
    assert "## Modo coach activo" in prompt
    assert "fase ENS: **actual**" in prompt
    assert "Aprobar plan" in prompt


# ════════════════════════════════════════════════════════════════════
# Phase 4A · Stack category + coach guidance coexistence
# ════════════════════════════════════════════════════════════════════


def test_build_system_prompt_stacks_category_and_coach_guidance():
    """Cuando categoría + coach_mode ambos activos · ambos guidances injected."""
    pc = PageContext(
        ens_category="MEDIA",
        coach_mode=True,
        coach_current_phase="ADECUACION",
        coach_pending_action="Firmar DdA",
    )
    prompt = _build_system_prompt(pc, corpus_gap=False)

    # Phase 2E category guidance present
    assert "## Categoría del proyecto cliente · MEDIA" in prompt
    assert "auditoría ENAC" in prompt

    # Phase 4A coach guidance present
    assert "## Modo coach activo" in prompt
    assert "ADECUACION" in prompt
    assert "Firmar DdA" in prompt


def test_build_system_prompt_coach_only_no_category():
    """coach_mode active sin ens_category · solo coach guidance (no category)."""
    pc = PageContext(
        coach_mode=True,
        coach_current_phase="DIAGNOSTICO",
        coach_pending_action="Revisar onboarding",
    )
    prompt = _build_system_prompt(pc, corpus_gap=False)
    assert "## Modo coach activo" in prompt
    assert "## Categoría del proyecto cliente" not in prompt


# ════════════════════════════════════════════════════════════════════
# Phase 4A · cliente-mínimo filosofía enforcement
# ════════════════════════════════════════════════════════════════════


def test_coach_guidance_enforces_no_creator_mode():
    """Coach guidance contiene enforcement cliente NO genera contenido ENS."""
    pc = PageContext(
        coach_mode=True,
        coach_current_phase="IMPLANTACION",
        coach_pending_action="Revisar política",
    )
    prompt = _build_system_prompt(pc, corpus_gap=False)
    # Filosofía cliente-mínimo enforcement explicit en prompt
    assert (
        "NO genera contenido" in prompt
        or "NO genera" in prompt.lower()
    )
    assert "recibe" in prompt.lower() or "aprueba" in prompt.lower()


def test_coach_guidance_r29_no_pression():
    """Coach guidance NO contiene phrases coercitivas (R29 firmísimo)."""
    pc = PageContext(
        coach_mode=True,
        coach_current_phase="IMPLANTACION",
        coach_pending_action="Subir log",
    )
    prompt = _build_system_prompt(pc, corpus_gap=False)
    # Phrases R29 anti-coercitivas
    coercive_anti_patterns = [
        "urgente!!", "ya mismo", "obligatorio inmediato",
        "tienes que ahora", "rápido",
    ]
    for pattern in coercive_anti_patterns:
        assert pattern not in prompt.lower(), (
            f"R29 violation: coercitive pattern '{pattern}' in coach prompt"
        )
