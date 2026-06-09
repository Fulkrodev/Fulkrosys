"""Tests para las integraciones M3/M5/M7/M9 (Checkpoint 3)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.models.ens import DdaEntry, EnsMeasure
from backend.app.motors.m08_verification.integrations.m3_dda_updater import (
    detect_dda_contradictions,
    get_findings_by_measure,
    get_tech_verification_summary,
)
from backend.app.motors.m08_verification.integrations.m5_obligations import (
    create_remediation_obligations,
)
from backend.app.motors.m08_verification.integrations.m7_evidence import (
    backfill_evidence_for_run,
    create_evidence_for_finding,
)
from backend.app.motors.m08_verification.integrations.m9_audit_prep import (
    collect_findings_for_dossier,
    count_findings_by_measure,
    has_verification_run,
)
from backend.app.motors.m08_verification.models import (
    VerificationFinding, VerificationRun,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _set_tenant(db, project_id):
    """Activa tenant context en la sesion para bypass RLS en helpers."""
    from backend.app.database import set_tenant_context
    client_id = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"),
        {"pid": str(project_id)},
    )).scalar()
    await set_tenant_context(
        db, client_id=client_id,
        project_id=uuid.UUID(project_id) if isinstance(project_id, str) else project_id,
    )


async def _create_run_with_finding(
    db, project_id, measure_code="op.exp.5",
    severity="high", classification="confirmed",
    cve_id="CVE-2024-TEST",
    title="Test finding",
):
    async with _admin_setup(db):
        run = VerificationRun(
            project_id=uuid.UUID(project_id) if isinstance(project_id, str) else project_id,
            category="BASICO",
            mode="internal",
            status="completed",
            scope_jsonb={"targets": ["test.example.es"], "web_apps": [], "exclusions": []},
            tools_used=["nuclei"],
            completed_at=datetime.now(timezone.utc),
            total_findings=1,
            confirmed_findings=1,
        )
        db.add(run)
        await db.flush()
        vf = VerificationFinding(
            project_id=run.project_id,
            run_id=run.id,
            finding_hash=f"t_{uuid.uuid4().hex[:12]}",
            title=title,
            description="descripcion",
            severity=severity,
            affected_host="test.example.es",
            cve_id=cve_id,
            tool_sources=["nuclei"],
            raw_outputs=[{"tool": "nuclei", "excerpt": "x"}],
            confidence_score=0.95,
            zfp_gate1_dedup=True,
            zfp_gate2_fp_filter=True,
            zfp_gate3_cross_tool=1,
            zfp_gate4_retest="not_applicable",
            zfp_gate5_classification=classification,
            ens_measures=[{"measure": measure_code, "title": "t", "method": "rule"}],
            ens_primary_measure=measure_code,
            remediation_summary="apt upgrade",
            status="open",
        )
        db.add(vf)
        await db.flush()
    return run, vf


async def _ensure_ens_measure(db, code):
    r = await db.execute(select(EnsMeasure).where(EnsMeasure.codigo == code))
    m = r.scalar_one_or_none()
    if m:
        return m.id
    async with _admin_setup(db):
        m = EnsMeasure(codigo=code, nombre=f"Medida {code}", marco="anexo_ii")
        db.add(m)
        await db.flush()
    return m.id


# ═══════════════════════════════════════════════════════════════════
# M3 DdA updater
# ═══════════════════════════════════════════════════════════════════

class TestDdaUpdater:
    @pytest.mark.asyncio
    async def test_tech_verification_summary_flags_non_compliant(self, db):
        _, project_id = await setup_test_project(db)
        await _create_run_with_finding(
            db, project_id, measure_code="op.exp.5", severity="critical",
        )
        summary = await get_tech_verification_summary(
            db, uuid.UUID(project_id),
        )
        assert "op.exp.5" in summary
        assert summary["op.exp.5"]["status"] == "non_compliant"
        assert summary["op.exp.5"]["open_findings"] == 1
        assert summary["op.exp.5"]["worst_severity"] == "critical"

    @pytest.mark.asyncio
    async def test_tech_verification_summary_low_finding_partial(self, db):
        _, project_id = await setup_test_project(db)
        await _create_run_with_finding(
            db, project_id, measure_code="op.mon.1", severity="low",
        )
        summary = await get_tech_verification_summary(
            db, uuid.UUID(project_id),
        )
        assert summary["op.mon.1"]["status"] == "partial"

    @pytest.mark.asyncio
    async def test_detect_contradictions_with_implantado_dda(self, db):
        _, project_id = await setup_test_project(db)
        m_id = await _ensure_ens_measure(db, "op.acc.6")
        async with _admin_setup(db):
            db.add(DdaEntry(
                project_id=uuid.UUID(project_id),
                measure_id=m_id,
                aplicabilidad="aplica",
                estado_implementacion="implantado",
            ))
            await db.flush()
        await _create_run_with_finding(
            db, project_id, measure_code="op.acc.6", severity="high",
        )
        await _set_tenant(db, project_id)
        contras = await detect_dda_contradictions(db, uuid.UUID(project_id))
        assert len(contras) == 1
        assert contras[0]["medida"] == "op.acc.6"

    @pytest.mark.asyncio
    async def test_findings_by_measure_indexes_correctly(self, db):
        _, project_id = await setup_test_project(db)
        await _create_run_with_finding(
            db, project_id, measure_code="mp.si.1",
        )
        idx = await get_findings_by_measure(db, uuid.UUID(project_id))
        assert "mp.si.1" in idx
        assert len(idx["mp.si.1"]) == 1


# ═══════════════════════════════════════════════════════════════════
# M5 Obligations
# ═══════════════════════════════════════════════════════════════════

class TestM5Obligations:
    @pytest.mark.asyncio
    async def test_creates_obligation_per_finding(self, db):
        _, project_id = await setup_test_project(db)
        run, vf = await _create_run_with_finding(
            db, project_id, measure_code="op.exp.5", severity="high",
        )
        await _set_tenant(db, project_id)
        obligations = await create_remediation_obligations(db, run.id)
        assert len(obligations) == 1
        assert obligations[0].tipo_ejecucion == "remediacion_hallazgo"
        assert obligations[0].measure_code == "op.exp.5"
        # SLA deadline set
        assert obligations[0].fecha_objetivo is not None

    @pytest.mark.asyncio
    async def test_idempotent_does_not_duplicate(self, db):
        _, project_id = await setup_test_project(db)
        run, _ = await _create_run_with_finding(
            db, project_id, measure_code="op.exp.5",
        )
        await _set_tenant(db, project_id)
        first = await create_remediation_obligations(db, run.id)
        second = await create_remediation_obligations(db, run.id)
        assert len(first) == 1
        assert len(second) == 0  # no duplica

    @pytest.mark.asyncio
    async def test_needs_review_findings_excluded(self, db):
        _, project_id = await setup_test_project(db)
        run, _ = await _create_run_with_finding(
            db, project_id, classification="needs_review",
        )
        obligations = await create_remediation_obligations(db, run.id)
        assert len(obligations) == 0


# ═══════════════════════════════════════════════════════════════════
# M7 Evidence
# ═══════════════════════════════════════════════════════════════════

class TestM7Evidence:
    @pytest.mark.asyncio
    async def test_creates_evidence_for_confirmed(self, db):
        _, project_id = await setup_test_project(db)
        _, vf = await _create_run_with_finding(
            db, project_id, measure_code="op.exp.5",
        )
        await _set_tenant(db, project_id)
        ev = await create_evidence_for_finding(db, vf)
        assert ev is not None
        assert ev.tipo == "verification_finding"
        assert ev.measure_code == "op.exp.5"
        assert ev.vigente is True
        # 180 dias
        delta = (ev.fecha_caducidad - ev.fecha_evidencia).days
        assert delta == 180

    @pytest.mark.asyncio
    async def test_skips_needs_review(self, db):
        _, project_id = await setup_test_project(db)
        _, vf = await _create_run_with_finding(
            db, project_id, classification="needs_review",
        )
        ev = await create_evidence_for_finding(db, vf)
        assert ev is None

    @pytest.mark.asyncio
    async def test_backfill_is_idempotent(self, db):
        _, project_id = await setup_test_project(db)
        run, _ = await _create_run_with_finding(
            db, project_id, measure_code="op.acc.6",
        )
        await _set_tenant(db, project_id)
        first = await backfill_evidence_for_run(db, run.id)
        second = await backfill_evidence_for_run(db, run.id)
        assert len(first) == 1
        assert len(second) == 0


# ═══════════════════════════════════════════════════════════════════
# M9 audit prep helpers
# ═══════════════════════════════════════════════════════════════════

class TestM9AuditPrep:
    @pytest.mark.asyncio
    async def test_collect_findings_returns_dicts(self, db):
        _, project_id = await setup_test_project(db)
        await _create_run_with_finding(
            db, project_id, measure_code="mp.info.3",
        )
        findings = await collect_findings_for_dossier(
            db, uuid.UUID(project_id),
        )
        assert len(findings) == 1
        assert findings[0]["title"] == "Test finding"
        assert findings[0]["ens_primary_measure"] == "mp.info.3"

    @pytest.mark.asyncio
    async def test_collect_findings_excludes_needs_review(self, db):
        _, project_id = await setup_test_project(db)
        await _create_run_with_finding(
            db, project_id, classification="needs_review",
        )
        findings = await collect_findings_for_dossier(
            db, uuid.UUID(project_id),
        )
        assert len(findings) == 0

    @pytest.mark.asyncio
    async def test_count_findings_by_measure_open_only(self, db):
        _, project_id = await setup_test_project(db)
        await _create_run_with_finding(
            db, project_id, measure_code="op.ext.1",
        )
        counts = await count_findings_by_measure(db, uuid.UUID(project_id))
        assert counts.get("op.ext.1") == 1

    @pytest.mark.asyncio
    async def test_has_verification_run_true_after_creation(self, db):
        _, project_id = await setup_test_project(db)
        assert await has_verification_run(db, uuid.UUID(project_id)) is False
        await _create_run_with_finding(db, project_id)
        assert await has_verification_run(db, uuid.UUID(project_id)) is True
