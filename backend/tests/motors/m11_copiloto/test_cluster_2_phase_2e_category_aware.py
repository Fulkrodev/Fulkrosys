"""CLUSTER 2 Phase 2E · Copilot Q&A category-aware cliente tests.

Sesión 3B-2B.8 CLUSTER 2 Phase 2E · PageContext.ens_category injection +
system prompt category-specific guidance + audit_log Sub-atom 5.A 3-way OR
(project_id + client_id propagated · accion cliente.copilot.asked + answered).

Coverage:
- PageContext.ens_category field opcional backward-compat None
- _build_system_prompt injects BASICA guidance when ens_category=BASICA
- _build_system_prompt injects MEDIA guidance when ens_category=MEDIA
- _build_system_prompt injects ALTA guidance when ens_category=ALTA
- _build_system_prompt unaffected si ens_category=None (backward-compat)
- _resolve_project_meta returns categoria_objetivo desde projects table

Pattern 16 cumulative formalized: category-aware system prompt injection +
Sub-atom 5.A audit_log LLM interaction tracing.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.agent_14_copiloto.service import _build_system_prompt
from backend.app.agents.agent_14_copiloto.types import PageContext
from backend.app.motors.m11_copiloto.portal_api import _resolve_project_meta
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Phase 2E.1 · PageContext.ens_category field backward-compat
# ════════════════════════════════════════════════════════════════════


def test_page_context_ens_category_optional_default_none():
    """PageContext.ens_category opcional · default None (backward-compat)."""
    pc = PageContext(url="/client-portal/dashboard")
    assert pc.ens_category is None


def test_page_context_ens_category_accepts_basica_media_alta():
    """PageContext.ens_category acepta BASICA/MEDIA/ALTA explicitly."""
    for cat in ("BASICA", "MEDIA", "ALTA"):
        pc = PageContext(ens_category=cat)
        assert pc.ens_category == cat


# ════════════════════════════════════════════════════════════════════
# Phase 2E.1 · _build_system_prompt category injection
# ════════════════════════════════════════════════════════════════════


def test_build_system_prompt_no_category_backward_compat():
    """Sin ens_category · system prompt sin sección categoría."""
    pc = PageContext(url="/client-portal/dashboard")
    prompt = _build_system_prompt(pc, corpus_gap=False)
    assert "## Categoría del proyecto cliente" not in prompt


def test_build_system_prompt_injects_basica_guidance():
    """ens_category=BASICA · prompt include BÁSICA guidance section."""
    pc = PageContext(ens_category="BASICA")
    prompt = _build_system_prompt(pc, corpus_gap=False)
    assert "## Categoría del proyecto cliente · BÁSICA" in prompt
    assert "self-declaration E-041" in prompt
    assert "NO se requiere auditoría externa ENAC" in prompt
    assert "sin prisa" in prompt.lower()


def test_build_system_prompt_injects_media_guidance():
    """ens_category=MEDIA · prompt include MEDIA guidance section."""
    pc = PageContext(ens_category="MEDIA")
    prompt = _build_system_prompt(pc, corpus_gap=False)
    assert "## Categoría del proyecto cliente · MEDIA" in prompt
    assert "auditoría ENAC obligatoria" in prompt
    assert "audit-ready" in prompt


def test_build_system_prompt_injects_alta_guidance():
    """ens_category=ALTA · prompt include ALTA guidance section."""
    pc = PageContext(ens_category="ALTA")
    prompt = _build_system_prompt(pc, corpus_gap=False)
    assert "## Categoría del proyecto cliente · ALTA" in prompt
    assert "vigilancia 24/7 SOC obligatoria" in prompt
    assert "DR (Disaster Recovery)" in prompt


def test_build_system_prompt_normalizes_lowercase_category():
    """ens_category lowercase tolera (upper() normaliza · forward-compat)."""
    pc = PageContext(ens_category="basica")
    prompt = _build_system_prompt(pc, corpus_gap=False)
    assert "BÁSICA" in prompt


def test_build_system_prompt_unknown_category_ignored():
    """ens_category invalido · prompt sin sección categoría (graceful skip)."""
    pc = PageContext(ens_category="INVALID_CAT")
    prompt = _build_system_prompt(pc, corpus_gap=False)
    assert "## Categoría del proyecto cliente" not in prompt


# ════════════════════════════════════════════════════════════════════
# Phase 2E.1 · _resolve_project_meta returns categoria_objetivo
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_resolve_project_meta_returns_categoria_objetivo(
    db: AsyncSession,
) -> None:
    """portal_api._resolve_project_meta resuelve (project_id, ens_category)."""
    client_id_str, project_id_str = await setup_test_project(db)
    client_uuid = uuid.UUID(client_id_str)
    project_uuid = uuid.UUID(project_id_str)

    # Setea categoria_objetivo='MEDIA' al project
    async with _admin_setup(db):
        await db.execute(
            text(
                "UPDATE projects SET categoria_objetivo = :cat "
                "WHERE id = :pid"
            ),
            {"cat": "MEDIA", "pid": project_id_str},
        )

    resolved_project_id, resolved_category = await _resolve_project_meta(
        db, client_uuid,
    )

    assert resolved_project_id == project_id_str
    assert resolved_category == "MEDIA"
    _ = project_uuid


@pytest.mark.asyncio
async def test_resolve_project_meta_handles_null_categoria(
    db: AsyncSession,
) -> None:
    """projects.categoria_objetivo NULL → ens_category=None (graceful)."""
    client_id_str, _ = await setup_test_project(db)
    client_uuid = uuid.UUID(client_id_str)

    # categoria_objetivo default NULL desde setup_test_project (no SET above)
    resolved_project_id, resolved_category = await _resolve_project_meta(
        db, client_uuid,
    )
    assert resolved_project_id is not None
    assert resolved_category is None


@pytest.mark.asyncio
async def test_resolve_project_meta_returns_none_no_project(
    db: AsyncSession,
) -> None:
    """Cliente sin project → (None, None)."""
    orphan_client_id = uuid.uuid4()
    resolved_project_id, resolved_category = await _resolve_project_meta(
        db, orphan_client_id,
    )
    assert resolved_project_id is None
    assert resolved_category is None
