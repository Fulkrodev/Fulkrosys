"""ComplianceMonitorService — orchestrates check runs + alert lifecycle.

Responsibilities:

- Upsert ``ComplianceCheck`` registry rows from ``CHECK_REGISTRY``
- Run a single check or a frequency batch (daily/weekly/monthly/quarterly)
- Persist results, manage alert open/auto-resolve transitions
- Emit emails (HIGH = immediate, MEDIUM = daily digest, LOW = weekly digest)

Used by:
- Celery beat tasks (``tasks.py``)
- Admin API ``/admin/compliance/monitor`` (manual trigger)
- Tests (direct instantiation with a session fixture)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.core.email.sender import get_email_sender
from backend.app.motors.m_compliance.email_design.mjml_compiler import (
    render_email as render_mjml_email,
)
from backend.app.models.compliance_monitor import (
    ALERT_OPEN,
    ALERT_RESOLVED,
    ComplianceAlert,
    ComplianceCheck,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    STATUS_GREEN,
    STATUS_RED,
    STATUS_UNKNOWN,
    STATUS_YELLOW,
)
from backend.app.motors.m_compliance_monitor.checks import (
    CHECK_REGISTRY,
    CheckResult,
    CheckSpec,
    run_check_by_name,
)
from backend.app.motors.m_compliance_monitor.reports_service import (
    ComplianceReportsService,
)


# Cadence-to-next-run helpers
_FREQ_DELTAS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
    "quarterly": timedelta(days=92),
}

_STATUS_COLOR = {
    STATUS_GREEN: "#22c55e",
    STATUS_YELLOW: "#eab308",
    STATUS_RED: "#ef4444",
    STATUS_UNKNOWN: "#94a3b8",
}


@dataclass
class RunOutcome:
    check_name: str
    result: CheckResult
    alert_created: bool
    alert_id: UUID | None
    auto_resolved_alert_id: UUID | None


class ComplianceMonitorService:
    """Orchestrates the self-monitoring lifecycle."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Registry sync ───────────────────────────────────────────────

    async def sync_registry(self) -> int:
        """Upsert one row per ``CheckSpec`` in ``CHECK_REGISTRY``.

        Returns the number of newly-created rows. Existing rows have their
        metadata (category, frequency, severity, description, regulatory_basis)
        updated to match the registry. Status / last_run / counters are not
        touched.
        """
        created = 0
        existing = {
            row.check_name: row
            for row in (await self.db.execute(select(ComplianceCheck))).scalars()
        }
        for name, spec in CHECK_REGISTRY.items():
            row = existing.get(name)
            if row is None:
                row = ComplianceCheck(
                    check_name=name,
                    category=spec.category,
                    frequency=spec.frequency,
                    severity_threshold=spec.severity,
                    description=spec.description,
                    regulatory_basis=spec.regulatory_basis,
                )
                self.db.add(row)
                created += 1
            else:
                row.category = spec.category
                row.frequency = spec.frequency
                row.severity_threshold = spec.severity
                row.description = spec.description
                row.regulatory_basis = spec.regulatory_basis
        await self.db.flush()
        return created

    # ── Run a single check ─────────────────────────────────────────

    async def run_check(self, name: str) -> RunOutcome:
        """Execute one check, persist result, create/resolve alerts."""
        spec: CheckSpec = CHECK_REGISTRY[name]
        result = await run_check_by_name(name, self.db)
        now = datetime.now(timezone.utc)

        check_row = await self._ensure_check_row(spec)
        check_row.last_run_at = now
        check_row.next_run_at = now + _FREQ_DELTAS.get(spec.frequency, timedelta(days=1))
        check_row.status = result.status
        check_row.last_result = {
            "status": result.status,
            "message": result.message,
            "severity": result.severity,
            "details": result.details,
            "ran_at": now.isoformat(),
        }
        if result.status == STATUS_UNKNOWN:
            check_row.consecutive_failures = (check_row.consecutive_failures or 0) + 1
        else:
            check_row.consecutive_failures = 0

        alert_created = False
        alert_id: UUID | None = None
        auto_resolved_id: UUID | None = None

        # Open-alert handling: if green now and there's an open alert → resolve
        if result.status == STATUS_GREEN:
            auto_resolved_id = await self._auto_resolve_open_alert(check_row, now)

        # Create alert for yellow/red OR for unknown after 3 consecutive failures
        should_alert = result.status in (STATUS_YELLOW, STATUS_RED) or (
            result.status == STATUS_UNKNOWN
            and (check_row.consecutive_failures or 0) >= 3
        )
        if should_alert:
            existing = await self._open_alert_for(check_row.id)
            if existing is None:
                alert = ComplianceAlert(
                    check_id=str(check_row.id),
                    check_name=name,
                    severity=result.severity,
                    status=ALERT_OPEN,
                    message=result.message,
                    details=result.details,
                    triggered_at=now,
                )
                self.db.add(alert)
                await self.db.flush()
                alert_created = True
                alert_id = alert.id
            else:
                # Update existing alert with most recent message + details
                existing.severity = result.severity
                existing.message = result.message
                existing.details = result.details
                alert_id = existing.id

        await self.db.flush()
        return RunOutcome(
            check_name=name,
            result=result,
            alert_created=alert_created,
            alert_id=alert_id,
            auto_resolved_alert_id=auto_resolved_id,
        )

    # ── Run a frequency batch ──────────────────────────────────────

    async def run_frequency_batch(self, frequency: str) -> list[RunOutcome]:
        """Run all checks for a given frequency and email the digest."""
        names = [n for n, s in CHECK_REGISTRY.items() if s.frequency == frequency]
        outcomes: list[RunOutcome] = []
        for name in names:
            try:
                outcomes.append(await self.run_check(name))
            except Exception as e:  # noqa: BLE001
                logger.error("Check {} crashed: {}", name, e)
        await self._dispatch_alerts(outcomes, frequency)
        return outcomes

    # ── Alert dispatch / email ─────────────────────────────────────

    async def _dispatch_alerts(
        self, outcomes: list[RunOutcome], frequency: str
    ) -> int:
        """Email recipients based on severity tier.

        - HIGH: per-alert immediate email
        - MEDIUM/LOW: aggregated digest per batch run

        Returns the number of emails sent.
        """
        settings = get_settings()
        recipient = (
            getattr(settings, "compliance_alert_email", None)
            or settings.consultor_email
        )
        if not recipient:
            return 0

        high_alerts = [
            o
            for o in outcomes
            if o.alert_created and o.result.severity == SEVERITY_HIGH
        ]
        digest_alerts = [
            o
            for o in outcomes
            if o.alert_created and o.result.severity in (SEVERITY_MEDIUM, SEVERITY_LOW)
        ]

        sent = 0
        for outcome in high_alerts:
            await self._send_email(
                recipient=recipient,
                subject_label="HIGH",
                outcomes=[outcome],
                frequency=frequency,
                immediate=True,
            )
            sent += 1
        if digest_alerts:
            await self._send_email(
                recipient=recipient,
                subject_label="DIGEST",
                outcomes=digest_alerts,
                frequency=frequency,
                immediate=False,
            )
            sent += 1
        return sent

    async def _send_email(
        self,
        *,
        recipient: str,
        subject_label: str,
        outcomes: list[RunOutcome],
        frequency: str,
        immediate: bool,
    ) -> None:
        period_label = "alerta inmediata" if immediate else f"digest {frequency}"
        status_label = "RED" if subject_label == "HIGH" else "YELLOW/MEDIUM"
        severity_level = "high" if subject_label == "HIGH" else "medium"
        alerts_for_template = [
            {
                "check_name": o.check_name,
                "status": o.result.status.upper(),
                "status_level": o.result.status,
                "message": o.result.message,
            }
            for o in outcomes
        ]
        admin_url = f"{get_settings().app_base_url.rstrip('/')}/admin/compliance/monitor"
        html = render_mjml_email(
            "compliance_alert.mjml",
            dict(
                severity_label=subject_label,
                severity_level=severity_level,
                status_label=status_label,
                period_label=period_label,
                check_count=len(alerts_for_template),
                alerts=alerts_for_template,
                admin_url=admin_url,
                report_url=None,
            ),
        )
        try:
            result = await get_email_sender().send(
                self.db,
                to=recipient,
                subject=f"[FULKRO] Compliance {subject_label} · {period_label}",
                html_body=html,
                template_used="compliance_alert",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Compliance alert email failed: {}", e)
            return

        if not result.ok:
            logger.warning("Compliance alert email not OK: {}", result)
            return

        # Mark email_sent_at on the alerts
        ids = [o.alert_id for o in outcomes if o.alert_id]
        if ids:
            await self.db.execute(
                update(ComplianceAlert)
                .where(ComplianceAlert.id.in_(ids))
                .values(email_sent_at=datetime.now(timezone.utc))
            )

    # ── Manual alert resolve ───────────────────────────────────────

    async def resolve_alert(
        self, alert_id: UUID, *, resolved_by: str, resolution_note: str
    ) -> ComplianceAlert:
        row = (
            await self.db.execute(
                select(ComplianceAlert).where(ComplianceAlert.id == alert_id)
            )
        ).scalar_one_or_none()
        if row is None:
            raise KeyError(f"Alert {alert_id} not found")
        if row.status == ALERT_RESOLVED:
            return row
        row.status = ALERT_RESOLVED
        row.resolved_at = datetime.now(timezone.utc)
        row.resolved_by = resolved_by
        row.resolution_note = resolution_note
        await self.db.flush()
        return row

    # ── Weekly status digest ───────────────────────────────────────

    async def generate_weekly_report(self) -> dict[str, Any]:
        """Produce + persist the weekly status report (Monday 08:00)."""
        now = datetime.now(timezone.utc)
        period_end = now
        period_start = now - timedelta(days=7)

        rows = (await self.db.execute(select(ComplianceCheck))).scalars().all()
        by_status: dict[str, list[ComplianceCheck]] = {
            STATUS_GREEN: [],
            STATUS_YELLOW: [],
            STATUS_RED: [],
            STATUS_UNKNOWN: [],
        }
        for r in rows:
            by_status.setdefault(r.status, []).append(r)
        summary = {
            "total": len(rows),
            "green": len(by_status[STATUS_GREEN]),
            "yellow": len(by_status[STATUS_YELLOW]),
            "red": len(by_status[STATUS_RED]),
            "unknown": len(by_status[STATUS_UNKNOWN]),
        }

        body = _render_weekly_md(rows, period_start, period_end, summary)
        recipient = (
            getattr(get_settings(), "compliance_alert_email", None)
            or get_settings().consultor_email
        )
        report = await ComplianceReportsService(self.db).persist_report(
            report_type="weekly_status",
            period_start=period_start,
            period_end=period_end,
            summary=summary,
            body_markdown=body,
            email_recipient=recipient,
        )
        return {
            "report_id": str(report.id),
            "storage_mode": report.storage_mode,
            "storage_path": report.storage_path,
            "signed_url": report.signed_url,
            "summary": summary,
        }

    # ── Internal helpers ───────────────────────────────────────────

    async def _ensure_check_row(self, spec: CheckSpec) -> ComplianceCheck:
        row = (
            await self.db.execute(
                select(ComplianceCheck).where(ComplianceCheck.check_name == spec.name)
            )
        ).scalar_one_or_none()
        if row is None:
            row = ComplianceCheck(
                check_name=spec.name,
                category=spec.category,
                frequency=spec.frequency,
                severity_threshold=spec.severity,
                description=spec.description,
                regulatory_basis=spec.regulatory_basis,
            )
            self.db.add(row)
            await self.db.flush()
        return row

    async def _open_alert_for(self, check_id: UUID) -> ComplianceAlert | None:
        return (
            await self.db.execute(
                select(ComplianceAlert)
                .where(ComplianceAlert.check_id == str(check_id))
                .where(ComplianceAlert.status == ALERT_OPEN)
            )
        ).scalar_one_or_none()

    async def _auto_resolve_open_alert(
        self, check_row: ComplianceCheck, now: datetime
    ) -> UUID | None:
        existing = await self._open_alert_for(check_row.id)
        if existing is None:
            return None
        existing.status = ALERT_RESOLVED
        existing.resolved_at = now
        existing.resolved_by = "auto"
        existing.auto_resolved = True
        existing.resolution_note = "Check returned green on subsequent run"
        await self.db.flush()
        return existing.id


def _render_weekly_md(
    rows: list[ComplianceCheck],
    period_start: datetime,
    period_end: datetime,
    summary: dict[str, int],
) -> str:
    lines = [
        f"# FULKRO Compliance Status Report",
        "",
        f"Período: **{period_start.date().isoformat()}** → **{period_end.date().isoformat()}**",
        "",
        "## Resumen",
        "",
        f"- Total checks: **{summary['total']}**",
        f"- 🟢 Green: **{summary['green']}**",
        f"- 🟡 Yellow: **{summary['yellow']}**",
        f"- 🔴 Red: **{summary['red']}**",
        f"- ⚪ Unknown: **{summary['unknown']}**",
        "",
        "## Detalle por check",
        "",
        "| Check | Categoría | Cadencia | Estado | Último run | Mensaje |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=lambda x: (x.status, x.check_name)):
        msg = (r.last_result or {}).get("message", "")[:80]
        last = r.last_run_at.isoformat(timespec="minutes") if r.last_run_at else "—"
        lines.append(
            f"| `{r.check_name}` | {r.category} | {r.frequency} | "
            f"**{r.status.upper()}** | {last} | {msg} |"
        )
    lines.extend(
        [
            "",
            "## Base regulatoria",
            "",
            "Cada check referencia su base regulatoria explícita en `regulatory_basis`. "
            "Ver `/admin/compliance/monitor` o tabla `compliance_checks` para detalle.",
            "",
            "---",
            "",
            "FULKRO Self-Monitoring System · MB-9.bis atom 9.bis.6 · "
            f"Generado: {period_end.isoformat()}",
        ]
    )
    return "\n".join(lines)
