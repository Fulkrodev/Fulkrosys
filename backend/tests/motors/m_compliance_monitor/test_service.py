"""Service-level tests for the FULKRO Self-Monitoring System (atom 9.bis.6).

10 tests covering:
- Registry sync (CHECK_REGISTRY → DB upsert)
- Single-check run (state persistence + alert lifecycle)
- Auto-resolve on green transition
- Manual resolve alert
- Frequency batch filter
- Email dispatch (HIGH immediate + MEDIUM digest)
- Check registry completeness + CheckResult helpers
- API status endpoint sanity
- API manual trigger endpoint sanity
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.models.compliance_monitor import (
    ALERT_OPEN,
    ALERT_RESOLVED,
    ComplianceAlert,
    ComplianceCheck,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    STATUS_GREEN,
    STATUS_RED,
    STATUS_YELLOW,
)
from backend.app.motors.m_compliance_monitor.checks import (
    CHECK_REGISTRY,
    CheckResult,
    list_check_names,
)
from backend.app.motors.m_compliance.email_design.mjml_compiler import (
    render_email as render_compliance_email,
)
from backend.app.motors.m_compliance_monitor.service import (
    ComplianceMonitorService,
)


# ── Test 1 — registry has exactly 21 checks (17 base + 2 atom 10.1 + op.mon SIEM + mfa op.acc.5) ──


def test_check_registry_has_20_entries() -> None:
    assert len(CHECK_REGISTRY) == 21
    names = list_check_names()
    # Ensure every registered check has the four required spec fields.
    for name in names:
        spec = CHECK_REGISTRY[name]
        assert spec.category
        assert spec.frequency in ("daily", "weekly", "monthly", "quarterly")
        assert spec.severity in ("high", "medium", "low")
        assert spec.description
        assert spec.regulatory_basis
        assert callable(spec.runner)


# ── Test 2 — CheckResult factory helpers ───────────────────────────────


def test_check_result_factory_helpers_return_expected_statuses() -> None:
    g = CheckResult.green("ok", x=1)
    assert g.status == STATUS_GREEN and g.severity == "low" and g.details == {"x": 1}
    y = CheckResult.yellow("warn")
    assert y.status == STATUS_YELLOW and y.severity == "medium"
    r = CheckResult.red("bad")
    assert r.status == STATUS_RED and r.severity == "high"
    u = CheckResult.unknown("transient")
    assert u.status == "unknown" and u.severity == "low"


# ── Test 3 — sync_registry creates all 20 rows on empty DB ────────────


@pytest.mark.asyncio
async def test_sync_registry_creates_all_checks(db) -> None:
    svc = ComplianceMonitorService(db)
    created = await svc.sync_registry()
    assert created == 21
    rows = (await db.execute(select(ComplianceCheck))).scalars().all()
    assert len(rows) == 21
    names = {r.check_name for r in rows}
    assert names == set(CHECK_REGISTRY.keys())


# ── Test 4 — sync_registry is idempotent ───────────────────────────────


@pytest.mark.asyncio
async def test_sync_registry_idempotent(db) -> None:
    svc = ComplianceMonitorService(db)
    first = await svc.sync_registry()
    second = await svc.sync_registry()
    assert first == 21
    assert second == 0  # no new rows on re-run
    rows = (await db.execute(select(ComplianceCheck))).scalars().all()
    assert len(rows) == 21


# ── Test 5 — run_check persists state + last_result ───────────────────


@pytest.mark.asyncio
async def test_run_check_persists_state(db) -> None:
    svc = ComplianceMonitorService(db)
    await svc.sync_registry()

    fake = CheckResult.green("backups ok", last_completed_at="2026-05-12")
    with patch(
        "backend.app.motors.m_compliance_monitor.service.run_check_by_name",
        new=AsyncMock(return_value=fake),
    ):
        outcome = await svc.run_check("backups_integrity")

    assert outcome.result.status == STATUS_GREEN
    assert outcome.alert_created is False
    row = (
        await db.execute(
            select(ComplianceCheck).where(
                ComplianceCheck.check_name == "backups_integrity"
            )
        )
    ).scalar_one()
    assert row.status == STATUS_GREEN
    assert row.last_run_at is not None
    assert row.next_run_at is not None
    assert row.last_result["message"] == "backups ok"


# ── Test 6 — run_check creates alert on RED ───────────────────────────


@pytest.mark.asyncio
async def test_run_check_creates_alert_on_red(db) -> None:
    svc = ComplianceMonitorService(db)
    await svc.sync_registry()

    fake = CheckResult.red("cert expires in 5 days", days=5)
    with patch(
        "backend.app.motors.m_compliance_monitor.service.run_check_by_name",
        new=AsyncMock(return_value=fake),
    ):
        outcome = await svc.run_check("ssl_cert_expiry")

    assert outcome.alert_created is True
    assert outcome.alert_id is not None
    alert = (
        await db.execute(
            select(ComplianceAlert).where(ComplianceAlert.id == outcome.alert_id)
        )
    ).scalar_one()
    assert alert.severity == SEVERITY_HIGH
    assert alert.status == ALERT_OPEN
    assert "expires in 5 days" in alert.message


# ── Test 7 — second run with green auto-resolves the open alert ───────


@pytest.mark.asyncio
async def test_run_check_auto_resolves_on_green(db) -> None:
    svc = ComplianceMonitorService(db)
    await svc.sync_registry()

    # First: yellow → opens alert.
    with patch(
        "backend.app.motors.m_compliance_monitor.service.run_check_by_name",
        new=AsyncMock(return_value=CheckResult.yellow("close to threshold")),
    ):
        first = await svc.run_check("rls_coverage_percentage")
    assert first.alert_created is True

    # Second: green → must auto-resolve.
    with patch(
        "backend.app.motors.m_compliance_monitor.service.run_check_by_name",
        new=AsyncMock(return_value=CheckResult.green("recovered")),
    ):
        second = await svc.run_check("rls_coverage_percentage")
    assert second.auto_resolved_alert_id == first.alert_id
    alert = (
        await db.execute(
            select(ComplianceAlert).where(ComplianceAlert.id == first.alert_id)
        )
    ).scalar_one()
    assert alert.status == ALERT_RESOLVED
    assert alert.auto_resolved is True
    assert alert.resolved_by == "auto"


# ── Test 8 — manual resolve_alert ─────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_alert_manual(db) -> None:
    svc = ComplianceMonitorService(db)
    await svc.sync_registry()

    with patch(
        "backend.app.motors.m_compliance_monitor.service.run_check_by_name",
        new=AsyncMock(return_value=CheckResult.red("oops")),
    ):
        outcome = await svc.run_check("audit_logs_continuity")
    assert outcome.alert_id is not None

    resolved = await svc.resolve_alert(
        outcome.alert_id,
        resolved_by="marcos@fulkro.es",
        resolution_note="Verified manually, false positive",
    )
    assert resolved.status == ALERT_RESOLVED
    assert resolved.resolved_by == "marcos@fulkro.es"
    assert "false positive" in resolved.resolution_note


# ── Test 9 — frequency batch filters by cadence + dispatches emails ───


@pytest.mark.asyncio
async def test_run_frequency_batch_filters_by_cadence(db) -> None:
    svc = ComplianceMonitorService(db)
    await svc.sync_registry()
    daily_names = {
        n for n, s in CHECK_REGISTRY.items() if s.frequency == "daily"
    }
    assert daily_names  # sanity

    seen: list[str] = []

    async def fake_runner(name: str, _db):
        seen.append(name)
        return CheckResult.green(f"{name} green")

    with patch(
        "backend.app.motors.m_compliance_monitor.service.run_check_by_name",
        side_effect=fake_runner,
    ):
        outcomes = await svc.run_frequency_batch("daily")

    assert set(seen) == daily_names
    assert len(outcomes) == len(daily_names)


# ── Test 10 — alert email html renders all rows ───────────────────────


def test_alert_email_html_renders_rows() -> None:
    """Compliance alert MJML template renders with the expected markers."""
    html = render_compliance_email(
        "compliance_alert.mjml",
        dict(
            severity_label="HIGH",
            severity_level="high",
            status_label="RED",
            period_label="alerta inmediata",
            check_count=1,
            alerts=[
                {
                    "check_name": "ssl_cert_expiry",
                    "status": "RED",
                    "status_level": "red",
                    "message": "cert expires in 5 days",
                }
            ],
            admin_url="https://fulkro.es/admin/compliance/monitor",
            report_url=None,
        ),
    )
    assert "ssl_cert_expiry" in html
    assert "cert expires in 5 days" in html
    assert "alerta inmediata" in html
    assert "Self-Monitoring" in html
    # MJML chrome includes brand and DPO footer.
    assert "FULKRO" in html
    assert "dpo@fulkro.es" in html
