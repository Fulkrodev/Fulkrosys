"""Tests for adaptive_dashboard_service · MB-7 atom 7.1.

Covers cross-motor aggregation + Q5.2/Q5.3 cement (NO role dimension).
"""
import uuid

import pytest
from sqlalchemy import text

from backend.app.services.adaptive_dashboard_service import (
    get_adaptive_dashboard,
)
from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


async def _seed_client_and_project(
    db,
    *,
    categoria: str = "MEDIA",
    fase: str | None = "dda",
    archetype: str = "saas_only",
    sector: str = "tecnologia",
) -> tuple[uuid.UUID, uuid.UUID]:
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, sector, created_at) "
            "VALUES (:id, :n, :cif, :sect, now())"
        ), {
            "id": str(client_id),
            "n": "Test SaaS Co",
            "cif": cif,
            "sect": sector,
        })
        await db.execute(text(
            "INSERT INTO projects "
            "(id, client_id, nombre, categoria_objetivo, fase, "
            " archetype, created_at) "
            "VALUES (:id, :cid, :n, :cat, :fase, :arch, now())"
        ), {
            "id": str(project_id),
            "cid": str(client_id),
            "n": "Test Project",
            "cat": categoria,
            "fase": fase,
            "arch": archetype,
        })
    await db.execute(
        text("SELECT set_config('app.current_client_id', :v, true)"),
        {"v": str(client_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": str(project_id)},
    )
    await db.flush()
    return client_id, project_id


async def test_adaptive_dashboard_returns_tier_phase_archetype_sector_no_role(db):
    """Context exposes 4 dims (tier+phase+archetype+sector) · NO role field."""
    client_id, project_id = await _seed_client_and_project(
        db, categoria="ALTA", fase="conformidad", archetype="hybrid",
        sector="sanidad",
    )

    view = await get_adaptive_dashboard(db, client_id)

    assert view.context.categoria_objetivo == "ALTA"
    assert view.context.current_phase == "conformidad"
    assert view.context.archetype == "hybrid"
    assert view.context.sector == "sanidad"
    # Q5.2 cement: no role / permission attribute in context
    assert not hasattr(view.context, "role")
    assert not hasattr(view.context, "permission_level")
    assert view.context.project_id == str(project_id)


async def test_adaptive_dashboard_today_actions_priorizadas(db):
    """Phase=verificacion always produces the pentest step-up action."""
    client_id, _ = await _seed_client_and_project(
        db, categoria="MEDIA", fase="verificacion", archetype="saas_only",
    )

    view = await get_adaptive_dashboard(db, client_id)

    assert len(view.today_actions) <= 5
    assert view.today_actions, "verificacion phase always produces pentest action"
    pentest = view.today_actions[0]
    assert pentest.id == "verification_pentest"
    assert pentest.priority == "high"
    assert pentest.requires_step_up is True
    assert all(a.priority in ("high", "medium", "low") for a in view.today_actions)


async def test_adaptive_dashboard_workflow_summary_phase_step(db):
    """workflow_summary includes phase_step + phase_total + counters."""
    client_id, _ = await _seed_client_and_project(
        db, categoria="BASICA", fase="diagnostico",
    )

    view = await get_adaptive_dashboard(db, client_id)

    summary = view.workflow_summary
    assert summary["phase"] == "diagnostico"
    assert summary["phase_total"] == 10
    assert summary["phase_step"] == 3  # diagnostico = index 2 + 1 (10-fases SAN-C: pre_venta·onboarding·diagnostico)
    assert "dda_pending" in summary
    assert "evidence_pending" in summary
    assert "risks_open" in summary
    assert "magerit_assets_pending" in summary
