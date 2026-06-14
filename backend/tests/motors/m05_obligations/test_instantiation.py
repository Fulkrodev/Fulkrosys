"""Tests for Motor 5 obligations instantiation service.

Covers deterministic Jinja2 rendering, DB-backed instantiation with
idempotency, category filtering, canonical field persistence, multi-gap
processing, and (optionally) LLM personalisation.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.app.motors.m05_obligations.instantiation_types import (
    ClientContext,
    GapInput,
    ProjectContext,
)
from backend.app.motors.m05_obligations.instantiation_service import (
    instantiate_obligations_for_gap,
    instantiate_obligations_for_multiple_gaps,
)
from backend.app.motors.m05_obligations.library_loader import (
    get_templates_for_measure,
)
from backend.app.motors.m05_obligations.personalization import (
    render_description_deterministic,
)
from backend.app.motors.m05_obligations.types import ObligationTemplate
from backend.tests.conftest import setup_test_project


# ── Helpers ────────────────────────────────────────────────────────────


async def _setup_project_with_context(db):
    """Create a client + project in the DB and return a ProjectContext."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    ctx = ProjectContext(
        project_id=uuid.UUID(project_id),
        nombre_proyecto="Test Project",
        categoria_ens="MEDIA",
        cliente=ClientContext(
            razon_social="ACME Tech S.L.",
            sector="fintech",
        ),
    )
    return ctx


def _make_fake_template(
    descripcion: str = "Obligacion para {{cliente.razon_social}}.",
) -> ObligationTemplate:
    """Build a minimal in-memory template for pure rendering tests."""
    return ObligationTemplate(
        id="OBL-org.1-001",
        measure_code="org.1",
        titulo="Test Template",
        descripcion=descripcion,
        categoria="organizativo",
        modo_ejecucion="consultor_genera",
        entregable_tipo="documento",
        entregable_esperado="Documento de prueba generado",
        esfuerzo_horas=8,
        responsable="Consultor ENS",
        magic_link_template=None,
        dependencias_template_ids=[],
        criterios_aceptacion=["Criterio 1"],
        fuente_normativa=["ENS RD 311/2022"],
        version="1.0",
    )


# ── Sync tests (no DB) ────────────────────────────────────────────────


class TestRenderDescription:

    def test_render_description_substitutes_client_name(self):
        tmpl = _make_fake_template(
            "Politica de seguridad para {{cliente.razon_social}}."
        )
        ctx = ProjectContext(
            project_id=uuid.uuid4(),
            nombre_proyecto="Proyecto Test",
            categoria_ens="MEDIA",
            cliente=ClientContext(razon_social="MiEmpresa S.A."),
        )
        result = render_description_deterministic(tmpl, ctx)
        assert "MiEmpresa S.A." in result
        assert "{{" not in result

    def test_render_description_handles_missing_vars_gracefully(self):
        tmpl = _make_fake_template(
            "Aprobar por {{cliente.organo_aprobador_politicas}} para {{variable_inexistente}}."
        )
        ctx = ProjectContext(
            project_id=uuid.uuid4(),
            nombre_proyecto="Proyecto Test",
            categoria_ens="MEDIA",
            cliente=ClientContext(razon_social="Test S.L."),
        )
        result = render_description_deterministic(tmpl, ctx)
        # Should not raise, missing vars become empty
        assert "{{" not in result
        assert "Aprobar por" in result


# ── Async DB tests ─────────────────────────────────────────────────────


class TestInstantiateObligations:

    async def test_instantiate_org_1_creates_obligations(self, db):
        ctx = await _setup_project_with_context(db)
        gap = GapInput(gap_id=uuid.uuid4(), measure_code="org.1")

        outcome = await instantiate_obligations_for_gap(db, gap, ctx)

        # org.1 has 3 templates in the library
        assert len(outcome.obligations_created_ids) >= 3
        assert len(outcome.validation_errors) == 0
        assert len(outcome.obligations_existing_ids) == 0

    async def test_instantiate_idempotent(self, db):
        ctx = await _setup_project_with_context(db)
        gap = GapInput(gap_id=uuid.uuid4(), measure_code="org.1")

        outcome1 = await instantiate_obligations_for_gap(db, gap, ctx)
        assert len(outcome1.obligations_created_ids) >= 3

        # Second call with same project+templates -> all existing
        outcome2 = await instantiate_obligations_for_gap(db, gap, ctx)
        assert len(outcome2.obligations_created_ids) == 0
        assert len(outcome2.obligations_existing_ids) >= 3

    async def test_instantiate_returns_empty_for_uncovered_measure(self, db):
        ctx = await _setup_project_with_context(db)

        # Find a measure code that exists in ens_measures but has no
        # templates in the library.
        from backend.app.motors.m05_obligations.library_loader import load_library

        lib = load_library()
        library_codes = {t.measure_code for t in lib.templates}
        res = await db.execute(text("SELECT codigo FROM ens_measures LIMIT 100"))
        uncovered_code = None
        for row in res.fetchall():
            if row[0] not in library_codes:
                uncovered_code = row[0]
                break

        if uncovered_code is None:
            pytest.skip("All ens_measures codes have library templates")

        gap = GapInput(gap_id=uuid.uuid4(), measure_code=uncovered_code)
        outcome = await instantiate_obligations_for_gap(db, gap, ctx)
        assert len(outcome.obligations_created_ids) == 0
        assert len(outcome.templates_skipped_no_match) > 0

    async def test_instantiate_op_acc_6_creates_multiple(self, db):
        ctx = await _setup_project_with_context(db)
        gap = GapInput(gap_id=uuid.uuid4(), measure_code="op.acc.6")

        outcome = await instantiate_obligations_for_gap(db, gap, ctx)

        # op.acc.6 has the 4 baseline templates plus the cierre 2% expansion
        assert len(outcome.obligations_created_ids) >= 4
        assert len(outcome.validation_errors) == 0

    async def test_instantiate_filters_by_category(self, db):
        """Templates are served for the measure regardless of ENS category
        in the current library (all 3 org.1 templates are ``organizativo``).
        Verify that the category field is stored correctly on the obligation.
        """
        ctx = await _setup_project_with_context(db)
        gap = GapInput(gap_id=uuid.uuid4(), measure_code="org.1")

        outcome = await instantiate_obligations_for_gap(db, gap, ctx)
        assert len(outcome.obligations_created_ids) >= 1

        # Verify the stored measure_code
        row = await db.execute(
            text(
                "SELECT measure_code FROM obligations WHERE id = :oid"
            ),
            {"oid": str(outcome.obligations_created_ids[0])},
        )
        assert row.scalar() == "org.1"

    async def test_instantiate_persists_canonical_fields(self, db):
        ctx = await _setup_project_with_context(db)
        gap = GapInput(gap_id=uuid.uuid4(), measure_code="org.1")

        outcome = await instantiate_obligations_for_gap(db, gap, ctx)
        oid = outcome.obligations_created_ids[0]

        row = await db.execute(
            text(
                "SELECT criterios_aceptacion, fuente_normativa, "
                "template_id, template_version, esfuerzo_estimado, "
                "estado, modo_ejecucion "
                "FROM obligations WHERE id = :oid"
            ),
            {"oid": str(oid)},
        )
        rec = row.mappings().one()

        # Canonical fields copied verbatim from template
        tmpl = get_templates_for_measure("org.1")[0]
        assert rec["criterios_aceptacion"] == tmpl.criterios_aceptacion
        assert rec["fuente_normativa"] == tmpl.fuente_normativa
        assert rec["template_id"] == tmpl.id
        assert rec["template_version"] == "1.0"
        assert rec["esfuerzo_estimado"] == tmpl.esfuerzo_horas
        # 'pendiente' (ES) = canónico de la máquina de estados (antes 'pending' EN
        # dejaba la obligación en limbo: no arrancable ni contabilizada).
        assert rec["estado"] == "pendiente"
        assert rec["modo_ejecucion"] == tmpl.modo_ejecucion

    async def test_instantiate_for_multiple_gaps(self, db):
        ctx = await _setup_project_with_context(db)
        gaps = [
            GapInput(gap_id=uuid.uuid4(), measure_code="org.1"),
            GapInput(gap_id=uuid.uuid4(), measure_code="op.acc.6"),
        ]

        outcomes = await instantiate_obligations_for_multiple_gaps(db, gaps, ctx)

        assert len(outcomes) == 2
        # org.1 -> 3, op.acc.6 -> 4
        total_created = sum(
            len(o.obligations_created_ids) for o in outcomes
        )
        assert total_created >= 7

    async def test_instantiate_records_metadata(self, db):
        ctx = await _setup_project_with_context(db)
        gap = GapInput(gap_id=uuid.uuid4(), measure_code="org.1")

        outcome = await instantiate_obligations_for_gap(db, gap, ctx)
        oid = outcome.obligations_created_ids[0]

        row = await db.execute(
            text(
                "SELECT metadata_extra FROM obligations WHERE id = :oid"
            ),
            {"oid": str(oid)},
        )
        meta = row.scalar()
        assert meta is not None
        assert meta["personalizada_con_llm"] is False

    async def test_instantiate_invalid_measure_returns_validation_error(self, db):
        ctx = await _setup_project_with_context(db)
        gap = GapInput(
            gap_id=uuid.uuid4(),
            measure_code="nonexistent.99",
        )

        outcome = await instantiate_obligations_for_gap(db, gap, ctx)

        assert len(outcome.obligations_created_ids) == 0
        assert len(outcome.validation_errors) == 1
        assert "nonexistent.99" in outcome.validation_errors[0]


# ── LLM test ───────────────────────────────────────────────────────────


class TestLLMPersonalization:

    @pytest.mark.llm
    async def test_instantiate_with_llm_personalization(self, db):
        ctx = await _setup_project_with_context(db)
        gap = GapInput(gap_id=uuid.uuid4(), measure_code="org.1")

        outcome = await instantiate_obligations_for_gap(
            db, gap, ctx, use_llm_personalization=True
        )

        assert len(outcome.obligations_created_ids) >= 1
        assert len(outcome.validation_errors) == 0

        # Check metadata records LLM usage
        oid = outcome.obligations_created_ids[0]
        row = await db.execute(
            text(
                "SELECT metadata_extra FROM obligations WHERE id = :oid"
            ),
            {"oid": str(oid)},
        )
        meta = row.scalar()
        assert meta["personalizada_con_llm"] is True
