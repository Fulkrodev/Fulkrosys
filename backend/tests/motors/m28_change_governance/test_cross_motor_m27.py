"""Tests integración cross-motor m28 ↔ m27 (sub-fase 5.5.F.0.H ADR-023).

m28/api.py POST /recategorizations y POST /extraordinary-audits
escriben en las tablas m27 (recategorizations + extraordinary_audits)
en lugar de duplicar tablas. ADR-023 formaliza dominio compartido.

Tests verifican:
1. Recategorization creada via m28 endpoint persiste en m27.recategorizations.
2. Extraordinary audit creada via m28 endpoint persiste en m27.extraordinary_audits.
3. Topology persiste en change_topologies (NO cross-motor — tabla dedicada m28).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.conformity_lifecycle import (
    ExtraordinaryAuditRow,
    RecategorizationRow,
)
from backend.app.models.change_governance import ChangeTopologyRow
from backend.app.models.operations import Change
from backend.tests.conftest import setup_test_project


@pytest.mark.asyncio
async def test_intake_change_persists_in_changes_table(
    async_client, db: AsyncSession,
):
    """POST /changes crea row en changes (operations.changes) con metadata."""
    _, pid = await setup_test_project(db)
    res = await async_client.post(
        f"/api/v1/changes/projects/{pid}/changes",
        json={
            "description": "Cambio prueba persistencia DB-backed m28 sub-fase 5.5.F.0.H",
            "requested_by": "Marcos Test",
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["state"] == "intake"

    # Verify row en DB
    cid = uuid.UUID(data["change_id"])
    stmt = select(Change).where(Change.id == cid)
    row = (await db.execute(stmt)).scalar_one_or_none()
    assert row is not None, "Change row debería persistir en DB"
    assert row.descripcion is not None
    assert row.metadata_jsonb is not None
    assert row.metadata_jsonb.get("state") == "intake"


@pytest.mark.asyncio
async def test_recategorization_persists_in_m27_table(
    async_client, db: AsyncSession,
):
    """ADR-023: m28 POST /recategorizations escribe en m27.recategorizations."""
    _, pid = await setup_test_project(db)

    # Crear change primero
    c = await async_client.post(
        f"/api/v1/changes/projects/{pid}/changes",
        json={
            "description": "Cambio que dispara recategorización ENS hacia MEDIA",
            "requested_by": "Marcos Test",
        },
    )
    assert c.status_code == 201
    change_id = c.json()["change_id"]

    # Crear recategorization via m28
    r = await async_client.post(
        f"/api/v1/changes/projects/{pid}/recategorizations",
        json={
            "change_id": change_id,
            "new_category": "MEDIA",
            "rationale": "Sistema escala fuera del umbral BÁSICA tras nuevo activo",
        },
    )
    assert r.status_code == 201, r.text
    rec_id = uuid.UUID(r.json()["recategorization_id"])

    # Verify cross-motor: registro debe existir en tabla m27
    stmt = select(RecategorizationRow).where(RecategorizationRow.id == rec_id)
    rec_row = (await db.execute(stmt)).scalar_one_or_none()
    assert rec_row is not None, (
        "Recategorization debería persistir en m27.recategorizations "
        "(ADR-023 cross-motor reuse)"
    )
    assert rec_row.new_category == "MEDIA"
    assert rec_row.project_id == uuid.UUID(pid)


@pytest.mark.asyncio
async def test_extraordinary_audit_persists_in_m27_table(
    async_client, db: AsyncSession,
):
    """ADR-023: m28 POST /extraordinary-audits escribe en m27.extraordinary_audits."""
    _, pid = await setup_test_project(db)

    c = await async_client.post(
        f"/api/v1/changes/projects/{pid}/changes",
        json={
            "description": "Incidente material que requiere auditoría extraordinaria fuera renewal",
            "requested_by": "Marcos Test",
        },
    )
    assert c.status_code == 201
    change_id = c.json()["change_id"]

    a = await async_client.post(
        f"/api/v1/changes/projects/{pid}/extraordinary-audits",
        json={
            "change_id": change_id,
            "rationale": "Materialidad alta, fuera de ventana renewal bianual normal",
        },
    )
    assert a.status_code == 201, a.text
    audit_id = uuid.UUID(a.json()["audit_id"])

    stmt = select(ExtraordinaryAuditRow).where(
        ExtraordinaryAuditRow.id == audit_id
    )
    audit_row = (await db.execute(stmt)).scalar_one_or_none()
    assert audit_row is not None, (
        "Extraordinary audit debería persistir en m27.extraordinary_audits "
        "(ADR-023 cross-motor reuse)"
    )
    assert audit_row.project_id == uuid.UUID(pid)


@pytest.mark.asyncio
async def test_topology_persists_in_change_topologies_table(
    async_client, db: AsyncSession,
):
    """Topology persiste en tabla DEDICADA change_topologies (NO cross-motor)."""
    _, pid = await setup_test_project(db)

    res = await async_client.post(
        f"/api/v1/changes/projects/{pid}/roles/topology/review",
        json={
            "sector": "publico",
            "employees": 50,
            "has_internal_it": True,
            "has_internal_ciso": False,
            "multi_site": False,
            "category": "MEDIA",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert "recommended_pattern" in body

    stmt = select(ChangeTopologyRow).where(
        ChangeTopologyRow.project_id == uuid.UUID(pid)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    assert row is not None, "Topology debería persistir en change_topologies"
    assert row.pattern_id == body["recommended_pattern"]
