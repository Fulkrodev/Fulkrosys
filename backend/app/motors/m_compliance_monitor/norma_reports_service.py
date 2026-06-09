"""ComplianceNormaReportsService · per-norma compliance reporting (mini-atom 3).

Pipeline:

1. Pick a registered ``NormaModule`` from ``NormaRegistry``.
2. Compute the period window (auto from frequency, or caller-supplied).
3. Aggregate ``CheckOutcome`` for every owned check in the period
   (joins ``compliance_checks`` table, falls back to ``unknown`` when
   the row doesn't exist yet).
4. Delegate scoring + Markdown to the plugin.
5. Persist ``FulkroComplianceNormaReport`` row + export MD via
   ``ComplianceReportsService`` (Desktop dev / MinIO prod / inline
   fallback — same dual-mode plumbing as the weekly status report).
6. Email Marcos when ``score < 85`` or the norma is ``critical``
   priority (uses the existing MJML ``compliance_alert.mjml`` template).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.core.email.sender import get_email_sender
from backend.app.models.compliance_monitor import ComplianceCheck
from backend.app.models.compliance_norma_reports import (
    FulkroComplianceNormaReport,
)
from backend.app.motors.m_compliance.email_design.mjml_compiler import (
    render_email,
)
from backend.app.motors.m_compliance_monitor.normas import (
    CheckOutcome,
    NormaModule,
    NormaRegistry,
)
from backend.app.motors.m_compliance_monitor.reports_service import (
    ComplianceReportsService,
)


_PERIOD_BY_FREQUENCY = {
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
    "quarterly": timedelta(days=92),
}

# Score threshold for proactive email to Marcos.
SCORE_ALERT_THRESHOLD = 85.0


class NormaNotRegisteredError(KeyError):
    """Raised when a norma_key isn't in the plugin registry."""


class ComplianceNormaReportsService:
    """Generates + persists per-norma compliance reports."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.reports_service = ComplianceReportsService(db)

    # ── Public entrypoints ────────────────────────────────────────

    async def generate_report(
        self,
        norma_key: str,
        *,
        period_end: datetime | None = None,
    ) -> FulkroComplianceNormaReport:
        """Build, persist and ship the report for one norma."""
        module = NormaRegistry.get(norma_key)
        if module is None:
            raise NormaNotRegisteredError(norma_key)

        period_end = period_end or datetime.now(timezone.utc)
        period_start = period_end - _PERIOD_BY_FREQUENCY[module.frequency]

        outcomes = await self._aggregate_outcomes(module)
        score = module.calculate_score(outcomes)
        status = module.score_to_status(score)
        report_md = module.generate_report_md(outcomes, period_start, period_end)
        report_json = module.generate_report_json(outcomes, period_start, period_end)

        counters = self._tally_outcomes(module, outcomes)
        row = FulkroComplianceNormaReport(
            norma_key=module.norma_key,
            norma_name=module.norma_name,
            period_start=period_start,
            period_end=period_end,
            compliance_score=score,
            status=status,
            checks_total=counters["total"],
            checks_passed=counters["green"],
            checks_warning=counters["yellow"] + counters["unknown"],
            checks_failed=counters["red"],
            report_md_content=report_md,
            report_json_content=report_json,
            generated_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        await self.db.flush()

        # Ship to Desktop (dev) or MinIO (prod) via the existing service.
        filename = (
            f"{module.norma_key}_{period_end.strftime('%Y-%m-%d')}_report.md"
        )
        paths = ComplianceReportsService.export_docs_to_storage(
            "08-Self_Monitoring_Reports/per_norma",
            {filename: report_md},
        )
        if filename in paths:
            path = paths[filename]
            # Distinguish dev / prod from the path prefix.
            if path.startswith("/mnt/c/") or path.startswith("/home/"):
                row.storage_path_dev = path
            else:
                row.storage_path_prod = path
            await self.db.flush()

        await self._maybe_alert(module, row, outcomes)
        return row

    async def generate_all_due(self) -> list[FulkroComplianceNormaReport]:
        """Run ``generate_report`` for every registered norma."""
        results: list[FulkroComplianceNormaReport] = []
        for module in NormaRegistry.get_all():
            try:
                results.append(await self.generate_report(module.norma_key))
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "Norma report failed for {}: {}", module.norma_key, e
                )
        return results

    async def latest_per_norma(self) -> dict[str, FulkroComplianceNormaReport]:
        """Return the most recent report (by ``generated_at``) per norma."""
        from sqlalchemy import desc

        # Sub-query: max(generated_at) per norma_key.
        rows = (
            await self.db.execute(
                select(FulkroComplianceNormaReport).order_by(
                    desc(FulkroComplianceNormaReport.generated_at)
                )
            )
        ).scalars().all()
        latest: dict[str, FulkroComplianceNormaReport] = {}
        for row in rows:
            latest.setdefault(row.norma_key, row)
        return latest

    # ── Internal helpers ──────────────────────────────────────────

    async def _aggregate_outcomes(self, module: NormaModule) -> list[CheckOutcome]:
        if not module.checks_owned:
            return []
        rows = (
            await self.db.execute(
                select(ComplianceCheck).where(
                    ComplianceCheck.check_name.in_(module.checks_owned)
                )
            )
        ).scalars().all()
        by_name = {r.check_name: r for r in rows}
        outcomes: list[CheckOutcome] = []
        for name in module.checks_owned:
            row = by_name.get(name)
            if row is None:
                outcomes.append(
                    CheckOutcome(
                        check_name=name,
                        status="unknown",
                        message="check no registrado todavía",
                        last_run_at=None,
                        regulatory_basis=None,
                    )
                )
                continue
            outcomes.append(
                CheckOutcome(
                    check_name=row.check_name,
                    status=row.status,  # type: ignore[arg-type]
                    message=(row.last_result or {}).get(
                        "message", row.description or ""
                    ),
                    last_run_at=row.last_run_at,
                    regulatory_basis=row.regulatory_basis,
                )
            )
        return outcomes

    @staticmethod
    def _tally_outcomes(
        module: NormaModule, outcomes: list[CheckOutcome]
    ) -> dict[str, int]:
        counters = {"green": 0, "yellow": 0, "red": 0, "unknown": 0, "total": 0}
        owned = set(module.checks_owned)
        for o in outcomes:
            if o.check_name not in owned:
                continue
            counters["total"] += 1
            counters[o.status] = counters.get(o.status, 0) + 1
        return counters

    async def _maybe_alert(
        self,
        module: NormaModule,
        row: FulkroComplianceNormaReport,
        outcomes: list[CheckOutcome],
    ) -> None:
        """Email Marcos when score is below threshold or norma is critical."""
        if (
            float(row.compliance_score) >= SCORE_ALERT_THRESHOLD
            and module.priority != "critical"
        ):
            return

        settings = get_settings()
        recipient = (
            getattr(settings, "compliance_alert_email", None)
            or settings.consultor_email
        )
        if not recipient:
            return

        severity_level = (
            "high"
            if float(row.compliance_score) < 70
            else ("medium" if float(row.compliance_score) < 85 else "low")
        )
        admin_url = (
            f"{settings.app_base_url.rstrip('/')}/admin/compliance/norma-reports"
        )
        alerts = [
            {
                "check_name": o.check_name,
                "status": o.status.upper(),
                "status_level": o.status,
                "message": o.message,
            }
            for o in outcomes
            if o.status in ("red", "yellow", "unknown")
        ][:10]

        try:
            html = render_email(
                "compliance_alert.mjml",
                dict(
                    severity_label=f"{module.norma_key} {row.compliance_score:.1f}%",
                    severity_level=severity_level,
                    status_label=row.status.upper(),
                    period_label=(
                        f"{row.period_start.date()} → {row.period_end.date()}"
                    ),
                    check_count=len(alerts),
                    alerts=alerts,
                    admin_url=admin_url,
                    report_url=None,
                ),
            )
            result = await get_email_sender().send(
                self.db,
                to=recipient,
                subject=(
                    f"[FULKRO] {module.norma_name} · "
                    f"score {row.compliance_score:.1f}%"
                ),
                html_body=html,
                template_used="norma_compliance_alert",
            )
            if result.ok:
                row.email_sent_at = datetime.now(timezone.utc)
                await self.db.flush()
        except Exception as e:  # noqa: BLE001
            logger.warning("Norma alert email failed for {}: {}", module.norma_key, e)
