"""Tests M21 Paso 5 — Stakeholders graph + ENS responsibles + conflictos."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.database import set_tenant_context
from backend.app.models.diagnosis import Stakeholder
from backend.app.motors.m21_diagnosis.stakeholders_service import (
    ENS_ROLES, INCOMPATIBLE_ROLE_PAIRS, PersonaInput,
    build_graph, build_summary, detect_role_conflicts,
    find_decision_chain, get_ens_responsibles,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _set_tenant(db, project_id):
    client_id = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    await set_tenant_context(
        db, client_id=client_id,
        project_id=uuid.UUID(project_id) if isinstance(project_id, str) else project_id,
    )


class TestStakeholdersCatalog:
    def test_ens_roles_has_4_required(self):
        assert set(ENS_ROLES.keys()) == {"ri", "rs", "rseg", "rsis"}

    def test_incompatible_pairs_are_defined(self):
        assert len(INCOMPATIBLE_ROLE_PAIRS) >= 3
        assert ("rseg", "rsis") in INCOMPATIBLE_ROLE_PAIRS


class TestBuildGraph:
    @pytest.mark.asyncio
    async def test_creates_stakeholders(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        async with _admin_setup(db):
            people = await build_graph(
                db, uuid.UUID(project_id),
                personas=[
                    PersonaInput(
                        nombre="Maria Perez", email="mp@ex.es",
                        rol_interno="rseg", cargo="CISO",
                    ),
                    PersonaInput(
                        nombre="Jorge Lopez", email="jl@ex.es",
                        rol_interno="rsis", cargo="CTO",
                    ),
                ],
            )
        assert len(people) == 2

    @pytest.mark.asyncio
    async def test_relations_edges_persisted(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        async with _admin_setup(db):
            await build_graph(
                db, uuid.UUID(project_id),
                personas=[
                    PersonaInput(nombre="Laura", email="laura@ex.es", rol_interno="rsis"),
                    PersonaInput(nombre="Maria", email="maria@ex.es", rol_interno="rseg"),
                ],
                relations=[
                    {"from": "laura", "tipo": "REPORTA_A", "target": "maria"},
                ],
            )
        laura = (await db.execute(
            select(Stakeholder).where(Stakeholder.nombre == "Laura")
        )).scalar_one()
        edges = (laura.relaciones or {}).get("edges", [])
        assert any(e["tipo"] == "REPORTA_A" for e in edges)


class TestEnsResponsibles:
    @pytest.mark.asyncio
    async def test_empty_project_100_missing(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        r = await get_ens_responsibles(db, uuid.UUID(project_id))
        assert r["coverage_pct"] == 0.0
        assert set(r["missing"]) == {"ri", "rs", "rseg", "rsis"}

    @pytest.mark.asyncio
    async def test_partial_coverage(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        async with _admin_setup(db):
            await build_graph(
                db, uuid.UUID(project_id),
                personas=[
                    PersonaInput(nombre="A", email="a@ex.es", rol_interno="rseg"),
                    PersonaInput(nombre="B", email="b@ex.es", rol_interno="rsis"),
                ],
            )
        r = await get_ens_responsibles(db, uuid.UUID(project_id))
        assert r["coverage_pct"] == 50.0
        assert set(r["missing"]) == {"ri", "rs"}

    @pytest.mark.asyncio
    async def test_full_coverage(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        async with _admin_setup(db):
            await build_graph(
                db, uuid.UUID(project_id),
                personas=[
                    PersonaInput(nombre="A", email="a@ex.es", rol_interno="ri"),
                    PersonaInput(nombre="B", email="b@ex.es", rol_interno="rs"),
                    PersonaInput(nombre="C", email="c@ex.es", rol_interno="rseg"),
                    PersonaInput(nombre="D", email="d@ex.es", rol_interno="rsis"),
                ],
            )
        r = await get_ens_responsibles(db, uuid.UUID(project_id))
        assert r["coverage_pct"] == 100.0
        assert r["missing"] == []
        assert r["rseg"]["asignado"] is True
        assert r["rseg"]["nombre"] == "C"


class TestDecisionChain:
    @pytest.mark.asyncio
    async def test_simple_chain(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        async with _admin_setup(db):
            await build_graph(
                db, uuid.UUID(project_id),
                personas=[
                    PersonaInput(nombre="CEO", email="ceo@ex.es"),
                    PersonaInput(nombre="CTO", email="cto@ex.es"),
                    PersonaInput(nombre="Dev", email="dev@ex.es"),
                ],
                relations=[
                    {"from": "dev", "tipo": "REPORTA_A", "target": "cto"},
                    {"from": "cto", "tipo": "REPORTA_A", "target": "ceo"},
                ],
            )
        dev = (await db.execute(
            select(Stakeholder).where(Stakeholder.nombre == "Dev"),
        )).scalar_one()
        chain = await find_decision_chain(db, dev.id)
        assert len(chain) == 3
        assert [c["nombre"] for c in chain] == ["Dev", "CTO", "CEO"]


class TestRoleConflicts:
    @pytest.mark.asyncio
    async def test_no_conflicts_on_clean_graph(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        async with _admin_setup(db):
            await build_graph(
                db, uuid.UUID(project_id),
                personas=[PersonaInput(nombre="A", rol_interno="rseg")],
            )
        c = await detect_role_conflicts(db, uuid.UUID(project_id))
        assert c == []

    @pytest.mark.asyncio
    async def test_detects_rseg_rsis_conflict(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        async with _admin_setup(db):
            await build_graph(
                db, uuid.UUID(project_id),
                personas=[
                    PersonaInput(nombre="Doble", email="d@ex.es", rol_interno="rseg"),
                ],
                relations=[
                    {"from": "doble", "tipo": "TIENE_ROL", "target": "rsis"},
                ],
            )
        c = await detect_role_conflicts(db, uuid.UUID(project_id))
        assert len(c) == 1
        assert set(c[0]["roles_conflicto"]) == {"rseg", "rsis"}


class TestBuildSummary:
    @pytest.mark.asyncio
    async def test_summary_ok_with_4_ens_roles(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        async with _admin_setup(db):
            await build_graph(
                db, uuid.UUID(project_id),
                personas=[
                    PersonaInput(nombre="A", rol_interno="ri"),
                    PersonaInput(nombre="B", rol_interno="rs"),
                    PersonaInput(nombre="C", rol_interno="rseg"),
                    PersonaInput(nombre="D", rol_interno="rsis"),
                ],
            )
        s = await build_summary(db, uuid.UUID(project_id))
        assert s["total_personas"] == 4
        assert s["verdict"] == "ok"
