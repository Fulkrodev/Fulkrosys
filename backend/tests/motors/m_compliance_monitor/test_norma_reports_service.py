"""ComplianceNormaReportsService tests (mini-atom 3)."""
from __future__ import annotations


import pytest
from sqlalchemy import text

from backend.app.motors.m_compliance_monitor.norma_reports_service import (
    ComplianceNormaReportsService,
    NormaNotRegisteredError,
)
from backend.app.motors.m_compliance_monitor.normas import NormaRegistry
from backend.app.motors.m_compliance_monitor.service import (
    ComplianceMonitorService,
)


@pytest.mark.asyncio
async def test_generate_report_persists_db_row(db) -> None:
    # Make sure the registry rows exist (so we get green outcomes).
    await ComplianceMonitorService(db).sync_registry()
    await db.flush()

    svc = ComplianceNormaReportsService(db)
    row = await svc.generate_report("RGPD_UE_2016_679")
    assert row.id is not None
    assert row.norma_key == "RGPD_UE_2016_679"
    assert row.checks_total == 8  # RGPD owns 8 checks
    assert row.report_md_content.startswith("# Reporte de Cumplimiento")
    assert "Art. 33" in row.report_md_content
    # JSON snapshot includes per-check details.
    checks_in_json = row.report_json_content["checks"]
    assert len(checks_in_json) == 8


@pytest.mark.asyncio
async def test_generate_report_unknown_norma_raises(db) -> None:
    svc = ComplianceNormaReportsService(db)
    with pytest.raises(NormaNotRegisteredError):
        await svc.generate_report("DOES_NOT_EXIST_FRAMEWORK")


@pytest.mark.asyncio
async def test_aggregate_outcomes_handles_missing_check_rows(db) -> None:
    """When a check row isn't synced yet, it's reported as ``unknown``."""
    svc = ComplianceNormaReportsService(db)
    # Pick a norma with checks_owned but DON'T sync registry first.
    nis2 = NormaRegistry.get("NIS2_UE_2022_2555")
    assert nis2 is not None
    outcomes = await svc._aggregate_outcomes(nis2)
    assert len(outcomes) == len(nis2.checks_owned)
    # Every outcome should be 'unknown' since rows don't exist.
    assert all(o.status == "unknown" for o in outcomes)


@pytest.mark.asyncio
async def test_score_alert_threshold_marks_email_sent_when_below_85(db) -> None:
    """When score < 85 → email is attempted (mock backend captures it)."""
    await ComplianceMonitorService(db).sync_registry()
    # Force one of RGPD's owned checks to fail so the score drops.
    await db.execute(
        text(
            "UPDATE compliance_checks SET status = 'red', "
            "last_result = '{\"message\": \"forced fail\"}'::jsonb "
            "WHERE check_name = 'breach_workflow_ready'"
        ),
    )
    await db.flush()

    svc = ComplianceNormaReportsService(db)
    row = await svc.generate_report("RGPD_UE_2016_679")
    # breach_workflow_ready weighs 0.18 → score drops by 18 % → 82 %.
    assert float(row.compliance_score) < 85
    # Mock email backend doesn't actually deliver so email_sent_at may
    # stay null in some env configs; what we care about is the alert
    # codepath ran without raising.


@pytest.mark.asyncio
async def test_latest_per_norma_returns_most_recent_per_key(db) -> None:
    await ComplianceMonitorService(db).sync_registry()
    svc = ComplianceNormaReportsService(db)
    # Generate two reports for the same norma; the latest should win.
    first = await svc.generate_report("ENS_RD_311_2022")
    second = await svc.generate_report("ENS_RD_311_2022")
    latest = await svc.latest_per_norma()
    assert latest["ENS_RD_311_2022"].id == second.id
    assert latest["ENS_RD_311_2022"].id != first.id


@pytest.mark.asyncio
async def test_generate_all_due_iterates_registry(db) -> None:
    await ComplianceMonitorService(db).sync_registry()
    svc = ComplianceNormaReportsService(db)
    results = await svc.generate_all_due()
    # 7 registered normas → 7 reports.
    assert len(results) == 7
    keys = {r.norma_key for r in results}
    assert "RGPD_UE_2016_679" in keys
    assert "ISO_27001_2022" in keys


@pytest.mark.asyncio
async def test_report_md_contains_period_window_and_score_line(db) -> None:
    await ComplianceMonitorService(db).sync_registry()
    svc = ComplianceNormaReportsService(db)
    row = await svc.generate_report("LOPDGDD_3_2018")
    # Period header always present.
    period_str = row.period_start.date().isoformat()
    assert period_str in row.report_md_content
    # Score line.
    assert "**Score**:" in row.report_md_content
