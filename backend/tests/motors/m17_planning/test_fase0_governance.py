"""Tests FASE 0 gobierno · compute_fase0_governance_state (Ejecutable 8 Pasada 16 F0-5).

Verifica el composer thin pure-functional (P10-F09): branch por categoría,
pasos doc-backed, separación (MEDIA/ALTA) y cadencia comité.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m17_planning.fase0_governance import (
    compute_fase0_governance_state,
)
from backend.tests.conftest import setup_test_project, _admin_setup


async def _set_categoria(db, project_id: str, categoria: str) -> None:
    async with _admin_setup(db):
        await db.execute(
            sa_text("UPDATE projects SET categoria_objetivo = :c WHERE id = :p"),
            {"c": categoria, "p": project_id},
        )
        await db.flush()


async def _gen_doc(db, project_id: str, ecode: str) -> None:
    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO documents (id, project_id, nombre, template_codigo, "
                "estado, created_at) VALUES (gen_random_uuid(), :p, :n, :ec, "
                "'GENERADO', now())"
            ),
            {"p": project_id, "n": f"Doc {ecode}", "ec": ecode},
        )
        await db.flush()


@pytest.mark.asyncio
async def test_fase0_empty_project_all_pending(db):
    _, project_id = await setup_test_project(db)
    await _set_categoria(db, project_id, "BASICA")
    st = await compute_fase0_governance_state(db, uuid.UUID(project_id))
    assert st["branch"] == "BASICO"
    assert st["completed_steps"] == 0
    assert st["fase0_completa"] is False
    assert st["next_step"] == "kickoff"
    assert st["progress_pct"] == 0.0
    # BÁSICA NO incluye paso comité
    assert "comite" not in {s["key"] for s in st["steps"]}


@pytest.mark.asyncio
async def test_fase0_basica_with_docs_progresses(db):
    _, project_id = await setup_test_project(db)
    await _set_categoria(db, project_id, "BASICA")
    for ec in ("E-155", "E-002", "E-150"):
        await _gen_doc(db, project_id, ec)
    st = await compute_fase0_governance_state(db, uuid.UUID(project_id))
    done = {s["key"] for s in st["steps"] if s["done"]}
    # alcance(E-155) + roles(E-002) + plan(E-150) + kickoff (implícito por docs)
    assert {"alcance", "roles", "plan", "kickoff"} <= done
    assert st["fase0_completa"] is True  # BÁSICA: 4 pasos, todos done


@pytest.mark.asyncio
async def test_fase0_media_includes_comite_and_separation(db):
    _, project_id = await setup_test_project(db)
    await _set_categoria(db, project_id, "MEDIA")
    st = await compute_fase0_governance_state(db, uuid.UUID(project_id))
    assert st["branch"] == "MEDIO_ALTO"
    keys = {s["key"] for s in st["steps"]}
    assert "comite" in keys, "MEDIA debe incluir el paso comité"
    roles_step = next(s for s in st["steps"] if s["key"] == "roles")
    assert "separacion" in roles_step
    assert roles_step["separacion"]["obligatoria"] is True
    comite_step = next(s for s in st["steps"] if s["key"] == "comite")
    assert "cadencia" in comite_step
    # sin actas → comité no done (alerta pre-auditoría)
    assert comite_step["done"] is False


@pytest.mark.asyncio
async def test_fase0_governance_endpoint(async_client, db):
    """Endpoint admin read-only GET /planning/projects/{id}/fase0-governance."""
    _, project_id = await setup_test_project(db)
    await _set_categoria(db, project_id, "MEDIA")
    r = await async_client.get(
        f"/api/v1/planning/projects/{project_id}/fase0-governance"
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["branch"] == "MEDIO_ALTO"
    assert data["total_steps"] >= 4
    assert "comite" in {s["key"] for s in data["steps"]}
