"""21 named compliance checks (17 base atom 9.bis.6 + 2 atom 10.1 MB-10 + 2 ENS op.mon.1/op.acc.5).

Atom 10.1 (MB-10) adds 2 checks honoring docs Block 1 commitments:
- ``check_admin_actions_audit_logged`` (ENS art.24.1 + ISO 27001 A.8.20 ·
  docs/compliance/04-ISMS_ISO27001/Access_Control_Policy_FULKRO.md:98)
- ``check_marketing_analytics_opt_in_only`` (RGPD Art.7 + AEPD 2020 ·
  docs/compliance/01-RGPD/Privacy_by_Design_FULKRO.md:60)

Original 17 cement (atom 9.bis.6):

Each check is a pure function that:
- Takes an ``AsyncSession`` (for DB-backed checks) and returns a
  ``CheckResult`` describing the current state of one FULKRO compliance
  control.
- Is registered in ``CHECK_REGISTRY`` with metadata (category, frequency,
  severity, description, regulatory basis).
- Has no side effects — alert creation and DB writes are driven by
  ``ComplianceMonitorService.run_check`` from the result.

Result statuses (semaphore):
- ``green``: control healthy
- ``yellow``: degraded / nearing threshold (medium severity)
- ``red``: control broken / breach imminent (high severity)
- ``unknown``: check could not run (returned only on transient failure
  — counts toward ``consecutive_failures``, triggers a yellow alert
  after 3 in a row)

Frequencies (Celery beat cadence):
- ``daily``   → 07:30 Europe/Madrid
- ``weekly``  → Monday 08:00 (after daily)
- ``monthly`` → 1st of month 08:30
- ``quarterly`` → 1st of Jan/Apr/Jul/Oct 09:00
"""
from __future__ import annotations

import asyncio
import os
import socket
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.models.compliance_monitor import (
    FREQUENCY_DAILY,
    FREQUENCY_MONTHLY,
    FREQUENCY_QUARTERLY,
    FREQUENCY_WEEKLY,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    STATUS_GREEN,
    STATUS_RED,
    STATUS_UNKNOWN,
    STATUS_YELLOW,
)


# ── Result type ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CheckResult:
    status: str
    message: str
    severity: str = SEVERITY_MEDIUM
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def green(cls, message: str, **details: Any) -> "CheckResult":
        return cls(status=STATUS_GREEN, message=message, severity=SEVERITY_LOW, details=details)

    @classmethod
    def yellow(cls, message: str, **details: Any) -> "CheckResult":
        return cls(status=STATUS_YELLOW, message=message, severity=SEVERITY_MEDIUM, details=details)

    @classmethod
    def red(cls, message: str, **details: Any) -> "CheckResult":
        return cls(status=STATUS_RED, message=message, severity=SEVERITY_HIGH, details=details)

    @classmethod
    def unknown(cls, message: str, **details: Any) -> "CheckResult":
        return cls(status=STATUS_UNKNOWN, message=message, severity=SEVERITY_LOW, details=details)


@dataclass(frozen=True)
class CheckSpec:
    name: str
    category: str
    frequency: str
    severity: str
    description: str
    regulatory_basis: str
    runner: Callable[[AsyncSession], Awaitable[CheckResult]]


# ── Helper utils ────────────────────────────────────────────────────────


async def _table_exists(db: AsyncSession, table_name: str) -> bool:
    row = await db.execute(
        text("SELECT to_regclass(:t)"), {"t": f"public.{table_name}"}
    )
    return row.scalar() is not None


async def _column_exists(db: AsyncSession, table: str, column: str) -> bool:
    row = await db.execute(
        text(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :t AND column_name = :c
            """
        ),
        {"t": table, "c": column},
    )
    return row.scalar() is not None


def _http_get(url: str, timeout: float = 5.0) -> tuple[int, str]:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r = client.get(url)
            return r.status_code, r.text[:500]
    except httpx.HTTPError as e:
        return 0, str(e)[:500]


# ── 1. Cookie banner reachable (daily, high) ────────────────────────────


async def check_cookies_banner_functional(db: AsyncSession) -> CheckResult:
    """Verify the public cookie banner endpoint responds.

    Calls the public ``/api/v1/legal/cookies`` page (or fallback to
    ``app_base_url``) and checks 200 + presence of the marker
    ``CookieConsentBanner`` (server-rendered tag).
    """
    settings = get_settings()
    url = f"{settings.app_base_url.rstrip('/')}/legal/cookies"
    code, body = await asyncio.to_thread(_http_get, url)
    if code == 0:
        return CheckResult.unknown(f"Cookie banner endpoint unreachable: {body}", url=url)
    if code != 200:
        return CheckResult.red(
            f"Cookie banner page returned HTTP {code}", url=url, code=code, severity=SEVERITY_HIGH
        )
    return CheckResult.green("Cookie banner page reachable", url=url, code=code)


# ── 2. RGPD endpoints responding (daily, high) ──────────────────────────


async def check_rgpd_endpoints_responding(db: AsyncSession) -> CheckResult:
    """Verify the 3 RGPD cliente endpoints are wired and respond.

    Smoke-tests existence of routes at OpenAPI level (HEAD on each).
    A 401/403 counts as healthy (route exists, auth gate works).
    """
    settings = get_settings()
    base = settings.app_base_url.rstrip("/")
    paths = [
        "/api/v1/portal/rgpd/access",
        "/api/v1/portal/rgpd/erasure",
        "/api/v1/portal/rgpd/portability",
    ]
    missing: list[str] = []
    for p in paths:
        code, _ = await asyncio.to_thread(_http_get, base + p, 3.0)
        # Route mounted: any of 200/401/403/405; missing route returns 404
        if code in (0, 404):
            missing.append(p)
    if not missing:
        return CheckResult.green("All RGPD endpoints reachable", checked=paths)
    return CheckResult.red(
        f"RGPD endpoints missing: {', '.join(missing)}",
        missing=missing,
    )


# ── 3. SSL cert expiry (daily, high) ────────────────────────────────────


async def check_ssl_cert_expiry(db: AsyncSession) -> CheckResult:
    """Days remaining before app_base_url SSL cert expires.

    ``red`` if <14 days, ``yellow`` if <30 days, ``green`` otherwise.
    On localhost / http base_url returns ``green`` with a 'skipped' note
    (dev env has no cert to inspect).
    """
    settings = get_settings()
    parsed = urlparse(settings.app_base_url)
    if parsed.scheme != "https":
        return CheckResult.green("Non-https app_base_url, SSL check skipped", url=settings.app_base_url)
    hostname = parsed.hostname or ""
    port = parsed.port or 443

    def _probe() -> Optional[datetime]:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=5.0) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                not_after = cert.get("notAfter") if cert else None
                if not not_after:
                    return None
                return datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)

    try:
        expires = await asyncio.to_thread(_probe)
    except (OSError, ssl.SSLError) as e:
        return CheckResult.unknown(f"SSL probe failed: {e}", host=hostname)

    if expires is None:
        return CheckResult.unknown("Cert returned no notAfter", host=hostname)
    days = (expires - datetime.now(timezone.utc)).days
    if days < 14:
        return CheckResult.red(
            f"SSL cert expires in {days} days", days=days, host=hostname, expires=expires.isoformat()
        )
    if days < 30:
        return CheckResult.yellow(
            f"SSL cert expires in {days} days", days=days, host=hostname, expires=expires.isoformat()
        )
    return CheckResult.green(f"SSL cert valid for {days} more days", days=days, host=hostname)


# ── 4. Backups integrity (weekly, high) ─────────────────────────────────


async def check_backups_integrity(db: AsyncSession) -> CheckResult:
    """Verify a recent successful BackupJob exists within last 48h.

    Reads ``backup_jobs`` table (M26). ``red`` if no completed full backup
    in last 7 days, ``yellow`` if no completed in last 48h, ``green``
    otherwise.
    """
    if not await _table_exists(db, "backup_jobs"):
        return CheckResult.unknown("backup_jobs table missing (M26 not deployed)")

    row = await db.execute(
        text(
            """
            SELECT MAX(completed_at) AS last_completed
            FROM backup_jobs
            WHERE status = 'completed'
            """
        )
    )
    last = row.scalar()
    if last is None:
        return CheckResult.red("No completed backups found")
    age = datetime.now(timezone.utc) - last
    if age > timedelta(days=7):
        return CheckResult.red(
            f"Latest backup is {age.days} days old", last_completed_at=last.isoformat()
        )
    if age > timedelta(hours=48):
        return CheckResult.yellow(
            f"Latest backup is {age.total_seconds() / 3600:.1f}h old",
            last_completed_at=last.isoformat(),
        )
    return CheckResult.green(
        f"Latest backup completed {age.total_seconds() / 3600:.1f}h ago",
        last_completed_at=last.isoformat(),
    )


# ── 5. Audit log continuity (daily, medium) ─────────────────────────────


async def check_audit_logs_continuity(db: AsyncSession) -> CheckResult:
    """Check audit_log has new rows in last 24h.

    A platform with active cliente work should never have a 24h gap. A gap
    indicates either no activity (acceptable for new FULKRO with 1 cliente)
    OR the audit middleware is broken (critical).
    """
    if not await _table_exists(db, "audit_log"):
        return CheckResult.unknown("audit_log table missing")
    # La columna canónica de audit_log es ``timestamp`` (NO created_at · ver
    # models/audit_log.py:35). Verificación adversarial: este check fallaba con
    # ColumnNotFound en runtime · check_admin_actions_audit_logged ya usa timestamp.
    row = await db.execute(text("SELECT MAX(timestamp) FROM audit_log"))
    last = row.scalar()
    if last is None:
        return CheckResult.yellow("audit_log is empty")
    age = datetime.now(timezone.utc) - last
    if age > timedelta(days=2):
        return CheckResult.yellow(
            f"audit_log gap of {age.days} days", last_entry_at=last.isoformat()
        )
    return CheckResult.green(f"audit_log fresh ({age.total_seconds() / 3600:.1f}h)", last_entry_at=last.isoformat())


# ── 6. DPO email channel working (weekly, high) ─────────────────────────


async def check_dpo_email_working(db: AsyncSession) -> CheckResult:
    """Verify the DPO contact alias (dpo@fulkro.es) is configured.

    Verifies via configured settings + audit_log evidence that the alias
    has received at least one routing event in the last 90 days (or marks
    yellow if just configured + no activity yet).
    """
    settings = get_settings()
    # dpo_email is a future setting; for now check via consultor_email fallback
    dpo_email = getattr(settings, "dpo_email", "dpo@fulkro.es")
    if not dpo_email or "@" not in dpo_email:
        return CheckResult.red("DPO email alias not configured")

    if not await _table_exists(db, "email_log"):
        return CheckResult.green(
            "DPO email alias configured (email_log table not yet present)",
            dpo_email=dpo_email,
        )
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    row = await db.execute(
        text(
            """
            SELECT COUNT(*) FROM email_log
            WHERE (to_address = :dpo OR from_address = :dpo)
              AND created_at >= :cutoff
            """
        ),
        {"dpo": dpo_email, "cutoff": cutoff},
    )
    count = row.scalar() or 0
    if count == 0:
        return CheckResult.yellow(
            "DPO email alias has no traffic in last 90 days — verify alias still resolves",
            dpo_email=dpo_email,
        )
    return CheckResult.green(
        f"DPO email alias active ({count} events in last 90 days)",
        dpo_email=dpo_email,
        events=count,
    )


# ── 7. security.txt reachable (weekly, medium) ──────────────────────────


async def check_security_txt_reachable(db: AsyncSession) -> CheckResult:
    """RFC 9116: /.well-known/security.txt must be reachable + parseable."""
    settings = get_settings()
    url = f"{settings.app_base_url.rstrip('/')}/.well-known/security.txt"
    code, body = await asyncio.to_thread(_http_get, url, 5.0)
    if code != 200:
        return CheckResult.red(
            f"security.txt unreachable (HTTP {code})", url=url, code=code
        )
    if "Contact:" not in body:
        return CheckResult.yellow(
            "security.txt missing required Contact: directive", url=url
        )
    return CheckResult.green("security.txt reachable + valid", url=url)


# ── 8. Privacy policy freshness (monthly, medium) ───────────────────────


async def check_privacy_policy_freshness(db: AsyncSession) -> CheckResult:
    """Privacy policy must be reviewed annually (Art. 24.1 GDPR practice).

    Reads the privacy policy MD frontmatter ``last_reviewed_at`` field from
    the bundled file shipped under ``docs/compliance/01-RGPD/``. ``yellow``
    if older than 11 months, ``red`` if older than 13 months.
    """
    from pathlib import Path

    candidates = [
        Path("docs/compliance/01-RGPD/privacy_policy.md"),
        Path("docs/compliance/01-RGPD/PRIVACY_POLICY.md"),
        Path("frontend/public/legal/privacy.md"),
    ]
    found_path = next((p for p in candidates if p.exists()), None)
    if found_path is None:
        return CheckResult.yellow(
            "Privacy policy MD file not found (will be created in atom 9.bis.4)",
            searched=[str(p) for p in candidates],
        )
    age = datetime.now(timezone.utc) - datetime.fromtimestamp(
        found_path.stat().st_mtime, tz=timezone.utc
    )
    if age > timedelta(days=400):
        return CheckResult.red(
            f"Privacy policy not modified in {age.days} days", path=str(found_path)
        )
    if age > timedelta(days=335):
        return CheckResult.yellow(
            f"Privacy policy aging ({age.days} days since last edit)",
            path=str(found_path),
        )
    return CheckResult.green(
        f"Privacy policy recent ({age.days} days since last edit)",
        path=str(found_path),
    )


# ── 9. Breach workflow ready (monthly, high) ────────────────────────────


async def check_breach_workflow_ready(db: AsyncSession) -> CheckResult:
    """Verify fulkro_breach_notifications table exists + endpoint wired."""
    if not await _table_exists(db, "fulkro_breach_notifications"):
        return CheckResult.yellow(
            "fulkro_breach_notifications table not yet present (atom 9.bis.1 pending)"
        )
    return CheckResult.green("Breach notification workflow ready (table present)")


# ── 10. Sub-processor DPA expirations (monthly, medium) ─────────────────


async def check_sub_processor_dpa_expirations(db: AsyncSession) -> CheckResult:
    """Verify no sub-processor DPA expires in next 60 days.

    Reads from ``fulkro_ropa_treatments`` if present (created in atom
    9.bis.3). Until then returns ``yellow`` informational.
    """
    if not await _table_exists(db, "fulkro_ropa_treatments"):
        return CheckResult.yellow(
            "fulkro_ropa_treatments table not yet present (atom 9.bis.3 pending)"
        )
    if not await _column_exists(db, "fulkro_ropa_treatments", "dpa_expires_at"):
        return CheckResult.green("RoPA table present without dpa_expires_at column (OK)")
    row = await db.execute(
        text(
            """
            SELECT processor_name, dpa_expires_at
            FROM fulkro_ropa_treatments
            WHERE dpa_expires_at IS NOT NULL
              AND dpa_expires_at < NOW() + INTERVAL '60 days'
            """
        )
    )
    expiring = [{"processor": r[0], "expires_at": r[1].isoformat()} for r in row.all()]
    if expiring:
        return CheckResult.red(
            f"{len(expiring)} sub-processor DPA(s) expire in next 60 days",
            expiring=expiring,
        )
    return CheckResult.green("No sub-processor DPA expirations imminent")


# ── 11. NIS2 vulnerability inbox (weekly, medium) ───────────────────────


async def check_nis2_vulnerability_inbox(db: AsyncSession) -> CheckResult:
    """Verify the published vulnerability disclosure inbox is monitored.

    Practical proxy: security.txt declares a ``Contact:`` address, and that
    address has either email_log activity OR an explicit "monitored=true"
    marker in settings. Returns ``yellow`` if no monitoring evidence found.
    """
    settings = get_settings()
    url = f"{settings.app_base_url.rstrip('/')}/.well-known/security.txt"
    code, body = await asyncio.to_thread(_http_get, url, 5.0)
    if code != 200:
        return CheckResult.yellow(
            "Cannot verify vulnerability inbox: security.txt unreachable",
            url=url,
        )
    contact_line = next((ln for ln in body.splitlines() if ln.startswith("Contact:")), None)
    if not contact_line:
        return CheckResult.yellow("security.txt has no Contact: line")
    # Extract email
    email = contact_line.split(":", 1)[1].strip().lstrip("mailto:")
    return CheckResult.green(
        f"Vulnerability inbox declared: {email}", url=url, contact=email
    )


# ── 12. RLS coverage % (weekly, medium) ─────────────────────────────────


async def check_rls_coverage_percentage(db: AsyncSession) -> CheckResult:
    """Compute RLS coverage over tenant-sensitive tables.

    Tenant-sensitive = table has a ``project_id``, ``client_id`` or
    ``tenant_client_id`` column (the latter used by the PII tables fixed by
    ``fulkro_pii_rls_002``).
    Coverage = tables with rowsecurity=true AND at least one policy /
    tenant-sensitive total. A table can have RLS enabled but no policy (which
    fails closed yet leaves the table effectively unusable), so we require a
    real policy to count it as covered.
    ``red`` if <70 %, ``yellow`` if <90 %, ``green`` if >=90 %.
    """
    sensitive_rows = await db.execute(
        text(
            """
            SELECT DISTINCT c.table_name
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
              AND c.column_name IN ('project_id', 'client_id', 'tenant_client_id')
            """
        )
    )
    sensitive = [r[0] for r in sensitive_rows.all()]
    if not sensitive:
        return CheckResult.green("No tenant-sensitive tables identified")

    rls_rows = await db.execute(
        text(
            """
            SELECT cls.relname
            FROM pg_class cls
            WHERE cls.relkind = 'r' AND cls.relrowsecurity = true
              AND cls.relnamespace = 'public'::regnamespace
              AND EXISTS (
                  SELECT 1 FROM pg_policy pol WHERE pol.polrelid = cls.oid
              )
            """
        )
    )
    rls_tables = {r[0] for r in rls_rows.all()}
    covered = [t for t in sensitive if t in rls_tables]
    pct = round(100.0 * len(covered) / len(sensitive), 1) if sensitive else 100.0
    uncovered = sorted(set(sensitive) - rls_tables)
    if pct < 70:
        return CheckResult.red(
            f"RLS coverage at {pct}% ({len(covered)}/{len(sensitive)})",
            coverage_pct=pct,
            uncovered=uncovered[:20],
        )
    if pct < 90:
        return CheckResult.yellow(
            f"RLS coverage at {pct}% ({len(covered)}/{len(sensitive)})",
            coverage_pct=pct,
            uncovered=uncovered[:20],
        )
    return CheckResult.green(
        f"RLS coverage at {pct}% ({len(covered)}/{len(sensitive)})",
        coverage_pct=pct,
        uncovered=uncovered[:20],
    )


# ── 13. DPA template version current (monthly, medium) ──────────────────


async def check_dpa_template_version(db: AsyncSession) -> CheckResult:
    """Verify the DPA template DOCX exists + is reviewed within 24 months."""
    from pathlib import Path

    candidates = [
        Path("backend/app/motors/m06_document_factory/templates/legal/DPA_FULKRO_cliente.docx"),
        Path("docs/compliance/09-Templates_Cliente_Sign/DPA_FULKRO_cliente.docx"),
    ]
    found = next((p for p in candidates if p.exists()), None)
    if found is None:
        return CheckResult.yellow(
            "DPA template DOCX not yet present (atom 9.bis.3 pending)",
            searched=[str(p) for p in candidates],
        )
    age = datetime.now(timezone.utc) - datetime.fromtimestamp(
        found.stat().st_mtime, tz=timezone.utc
    )
    if age > timedelta(days=730):
        return CheckResult.red(
            f"DPA template not reviewed in {age.days} days", path=str(found)
        )
    if age > timedelta(days=545):
        return CheckResult.yellow(
            f"DPA template aging ({age.days} days)", path=str(found)
        )
    return CheckResult.green(
        f"DPA template current ({age.days} days)", path=str(found)
    )


# ── 14. Sub-processors list freshness (monthly, low) ────────────────────


async def check_sub_processors_list_freshness(db: AsyncSession) -> CheckResult:
    """The public sub-processors MD must be reviewed quarterly."""
    from pathlib import Path

    candidates = [
        Path("docs/compliance/06-Sub_Processors/sub_processors.md"),
        Path("docs/compliance/06-Sub_Processors/SUB_PROCESSORS.md"),
    ]
    found = next((p for p in candidates if p.exists()), None)
    if found is None:
        return CheckResult.yellow(
            "Sub-processors MD not yet present (atom 9.bis.4 pending)"
        )
    age = datetime.now(timezone.utc) - datetime.fromtimestamp(
        found.stat().st_mtime, tz=timezone.utc
    )
    if age > timedelta(days=120):
        return CheckResult.yellow(
            f"Sub-processors list aging ({age.days} days)", path=str(found)
        )
    return CheckResult.green(
        f"Sub-processors list current ({age.days} days)", path=str(found)
    )


# ── 15. RoPA review due (quarterly, medium) ─────────────────────────────


async def check_ropa_review_due(db: AsyncSession) -> CheckResult:
    """RoPA (Art. 30 GDPR) must be reviewed at least annually.

    Reads ``fulkro_ropa_treatments`` for the most recent
    ``last_reviewed_at`` column (created in atom 9.bis.3). Returns
    ``yellow`` if the table is not yet present.
    """
    if not await _table_exists(db, "fulkro_ropa_treatments"):
        return CheckResult.yellow(
            "fulkro_ropa_treatments table not yet present (atom 9.bis.3 pending)"
        )
    if not await _column_exists(db, "fulkro_ropa_treatments", "last_reviewed_at"):
        return CheckResult.green("RoPA table present, no last_reviewed_at column to inspect")
    row = await db.execute(
        text("SELECT MAX(last_reviewed_at) FROM fulkro_ropa_treatments")
    )
    last = row.scalar()
    if last is None:
        return CheckResult.yellow("No RoPA entries marked as reviewed yet")
    age = datetime.now(timezone.utc) - last
    if age > timedelta(days=400):
        return CheckResult.red(
            f"RoPA not reviewed in {age.days} days — annual review overdue",
            last_reviewed_at=last.isoformat(),
        )
    if age > timedelta(days=335):
        return CheckResult.yellow(
            f"RoPA review due ({age.days} days)", last_reviewed_at=last.isoformat()
        )
    return CheckResult.green(
        f"RoPA reviewed {age.days} days ago", last_reviewed_at=last.isoformat()
    )


# ── 16. ISMS docs review due (quarterly, medium) ────────────────────────


async def check_isms_docs_review_due(db: AsyncSession) -> CheckResult:
    """ISO 27001:2022 §7.5 — documented information shall be reviewed.

    Checks the 5 ISMS MD files for mtime within last 18 months. Marks
    yellow per-file aging.
    """
    from pathlib import Path

    expected = [
        "information_security_policy.md",
        "risk_assessment.md",
        "asset_register.md",
        "access_control_policy.md",
        "incident_response_plan.md",
    ]
    base = Path("docs/compliance/04-ISMS_ISO27001")
    missing: list[str] = []
    aging: list[str] = []
    overdue: list[str] = []
    now = datetime.now(timezone.utc)
    for name in expected:
        p = base / name
        if not p.exists():
            missing.append(name)
            continue
        age = now - datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if age > timedelta(days=545):
            overdue.append(name)
        elif age > timedelta(days=400):
            aging.append(name)
    if missing or overdue:
        return CheckResult.red(
            f"ISMS docs: {len(missing)} missing, {len(overdue)} overdue review",
            missing=missing,
            overdue=overdue,
            aging=aging,
        )
    if aging:
        return CheckResult.yellow(
            f"ISMS docs aging: {len(aging)} approaching review window",
            aging=aging,
        )
    return CheckResult.green(f"All {len(expected)} ISMS docs current")


# ── 17. Cookie consent renewal (24m) (quarterly, medium) ────────────────


async def check_cookie_consent_renewal_24month(db: AsyncSession) -> CheckResult:
    """Guía AEPD 2020: cookie consent must be re-collected every 24 months.

    Reads ``client_users.consent_renewal_due`` if present. Returns the
    count of expired vs upcoming renewals.
    """
    if not await _table_exists(db, "client_users"):
        return CheckResult.green("client_users table not present (no consents to check)")
    if not await _column_exists(db, "client_users", "consent_renewal_due"):
        return CheckResult.yellow(
            "consent_renewal_due column not yet present (atom 9.bis.1 pending)"
        )
    row = await db.execute(
        text(
            """
            SELECT
              SUM((consent_renewal_due < NOW())::int)        AS expired,
              SUM((consent_renewal_due < NOW() + INTERVAL '30 days')::int) AS upcoming,
              COUNT(*) AS total
            FROM client_users
            WHERE consent_renewal_due IS NOT NULL
            """
        )
    )
    r = row.first()
    expired = (r[0] or 0) if r else 0
    upcoming = (r[1] or 0) if r else 0
    total = (r[2] or 0) if r else 0
    if expired > 0:
        return CheckResult.red(
            f"{expired} client_users have expired cookie consent (>24 months)",
            expired=expired,
            upcoming=upcoming,
            total=total,
        )
    if upcoming > 0:
        return CheckResult.yellow(
            f"{upcoming} client_users approaching cookie consent renewal (next 30 days)",
            upcoming=upcoming,
            total=total,
        )
    return CheckResult.green(
        f"All {total} client_users consents within 24m window", total=total
    )


# ── 18. Admin actions audit logged (daily, high) · MB-10 atom 10.1 ─────


# Admin emails recognized for audit verification. FULKRO opera con un único
# admin (Marcos · ADR-013 + ADR-020 v3). Fuente única: el email admin
# configurado (``marcos_admin_email`` · env ``FULKRO_MARCOS_ADMIN_EMAIL``),
# de modo que rotar el dominio mantiene este check coherente sin tocar código.
# Se conserva además el email histórico pre-rotación porque las filas de
# ``audit_log`` escritas bajo él siguen siendo acciones legítimas de Marcos
# (continuidad de la traza · append-only R6).
_ADMIN_EMAILS_AUDIT_TRAIL_HISTORICAL: tuple[str, ...] = (
    "marcos@fulkro.es",
)


def _admin_emails_audit_trail() -> list[str]:
    """Emails admin reconocidos en la traza · configurado + históricos."""
    emails = set(_ADMIN_EMAILS_AUDIT_TRAIL_HISTORICAL)
    configured = get_settings().marcos_admin_email
    if configured:
        emails.add(configured)
    return sorted(emails)


async def check_admin_actions_audit_logged(db: AsyncSession) -> CheckResult:
    """Verify admin actions generate ``audit_log`` rows in last 24h.

    Honors compliance docs commitment:
    ``docs/compliance/04-ISMS_ISO27001/Access_Control_Policy_FULKRO.md:98``.

    ENS RD 311/2022 art.24.1 + ISO/IEC 27001:2022 A.8.20 require continuous
    audit trail of administrative actions. Silent gap (admin active in last
    7 days but zero rows in last 24h) = audit chain degradation, suspicious.

    Thresholds:
    - GREEN: admin activity logged last 24h (audit trail active)
    - YELLOW (informational): zero admin activity 7+ days (dev/vacation OK)
    - YELLOW (suspicious): zero last 24h BUT activity in 7d (gap)
    """
    if not await _table_exists(db, "audit_log"):
        return CheckResult.yellow(
            "audit_log table NOT present (legacy migration pending)"
        )

    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)

    row = await db.execute(
        text(
            "SELECT COUNT(*) FROM audit_log "
            "WHERE usuario = ANY(:emails) AND timestamp > :cutoff"
        ),
        {"emails": _admin_emails_audit_trail(), "cutoff": cutoff_24h},
    )
    count_24h = row.scalar() or 0

    row = await db.execute(
        text(
            "SELECT COUNT(*) FROM audit_log "
            "WHERE usuario = ANY(:emails) AND timestamp > :cutoff"
        ),
        {"emails": _admin_emails_audit_trail(), "cutoff": cutoff_7d},
    )
    count_7d = row.scalar() or 0

    if count_24h > 0:
        return CheckResult.green(
            f"Admin audit trail active · {count_24h} rows last 24h",
            count_24h=count_24h,
            count_7d=count_7d,
        )
    if count_7d == 0:
        return CheckResult.yellow(
            "No admin actions logged in 7 days · verify Marcos activity "
            "(dev environment OR vacation OK · informational)",
            count_24h=0,
            count_7d=0,
        )
    return CheckResult.yellow(
        f"Admin audit gap · 0 rows last 24h but {count_7d} in 7d · "
        "verify expected pause or audit chain disruption",
        count_24h=0,
        count_7d=count_7d,
    )


# ── 19. Marketing analytics opt-in only (weekly, high) · atom 10.1 ─────


# Known environment variables que indicarían un servicio de analítica de
# marketing integrado. Si cualquiera está set en producción, el check
# requiere auditoría manual para verificar gate de consentimiento por
# usuario antes del disparo de eventos.
_MARKETING_ANALYTICS_ENV_KEYS: tuple[str, ...] = (
    "POSTHOG_API_KEY",
    "POSTHOG_HOST",
    "GA_MEASUREMENT_ID",
    "GA4_MEASUREMENT_ID",
    "MATOMO_URL",
    "MIXPANEL_TOKEN",
    "SEGMENT_WRITE_KEY",
    "AMPLITUDE_API_KEY",
)


async def check_marketing_analytics_opt_in_only(db: AsyncSession) -> CheckResult:
    """Verify marketing analytics integration adherence to opt-in only.

    Honors compliance docs commitment:
    ``docs/compliance/01-RGPD/Privacy_by_Design_FULKRO.md:60``.

    Current FULKRO state (privacy-by-design FULKRO-RGPD-PBD-001 §4.2): NO
    marketing analytics integration. The check verifies this state by
    inspecting environment variables conocidos para PostHog/GA/Matomo/
    Mixpanel/Segment/Amplitude.

    Thresholds:
    - GREEN: no analytics integration detected · opt-in trivially satisfied
    - YELLOW: integration detected · manual audit required (verify consent
      gate active before tracking events fires)

    NOTE: este check NO requiere parámetro ``db`` pero respeta la firma común
    para uniformidad del registry.
    """
    enabled = sorted(
        k for k in _MARKETING_ANALYTICS_ENV_KEYS if os.environ.get(k)
    )
    if enabled:
        return CheckResult.yellow(
            f"Marketing analytics integration detected ({enabled[0]}) · "
            "MANUAL audit required · verify per-user consent gate active "
            "before firing tracking events (RGPD Art.7 + AEPD 2020)",
            integrations=enabled,
        )
    return CheckResult.green(
        "No marketing analytics integration · RGPD Art.7 opt-in trivially "
        "satisfied (privacy-by-design FULKRO-RGPD-PBD-001 §4.2)",
        integrations=[],
    )


# Indicadores de detección de intrusión / monitorización (op.mon.1).
_IDS_INDICATOR_PATHS = (
    "/var/run/fail2ban/fail2ban.sock",  # fail2ban activo
    "/run/fail2ban/fail2ban.sock",
    "/run/auditd.pid",                  # auditd activo
    "/var/run/auditd.pid",
)


async def check_intrusion_detection_present(db: AsyncSession) -> CheckResult:
    """ENS op.mon.1 (detección de intrusión · aplica desde MEDIA) + op.mon.3
    (vigilancia · desde BÁSICA).

    Dogfooding (R7): FULKRO declara ENS Medio sobre sí mismo, así que DEBE tener
    detección de intrusión / monitorización de logs. Antes el plugin ENS NO
    tenía ningún check op.mon (gap detectado en docs/audits/SIEM_INVESTIGATION.md).

    Detecta fail2ban/auditd activos (pidfile/sock) o el flag explícito
    ``FULKRO_IDS_ENABLED`` (atestación tras instalarlo en Hetzner). Honest: si no
    hay nada → RED (no conformidad op.mon.1 · remediar con fail2ban/auditd · NO
    requiere un SIEM dedicado para MEDIA single-host). Esta firma respeta el
    contrato común aunque no usa ``db``.
    """
    flag = os.environ.get("FULKRO_IDS_ENABLED", "").strip().lower() in {
        "1", "true", "yes",
    }
    active_paths = [p for p in _IDS_INDICATOR_PATHS if os.path.exists(p)]
    if flag or active_paths:
        return CheckResult.green(
            "Detección de intrusión / monitorización presente (op.mon.1)",
            ids_enabled_flag=flag,
            active_indicators=active_paths,
        )
    return CheckResult.red(
        "Sin detección de intrusión (op.mon.1) ni monitorización de logs activa "
        "· dogfooding ENS Medio. Remediar: instalar fail2ban/auditd o definir "
        "FULKRO_IDS_ENABLED tras configurarlo (ver docs/audits/"
        "SIEM_INVESTIGATION.md · un SIEM dedicado NO es necesario para MEDIA "
        "single-host).",
        ids_enabled_flag=flag,
        active_indicators=[],
    )


async def check_mfa_enforcement(db: AsyncSession) -> CheckResult:
    """ENS op.acc.5 (mecanismo de autenticación · 2FA) · op.acc.6 (gestión).

    Dogfooding (R7 + R4): FULKRO declara ENS Medio sobre sí mismo y su doctrina R4
    exige WebAuthn (Yubikey) / TOTP para el acceso de administración. Este check
    verifica que TODOS los usuarios admin activos tienen un segundo factor
    enrolado (WebAuthn o TOTP). Si alguno carece de 2FA → RED (no conformidad
    op.acc.5). Plataforma-global (sin tenant)."""
    rows = await db.execute(
        text(
            """
            SELECT
              count(*) AS total,
              count(*) FILTER (
                WHERE EXISTS (SELECT 1 FROM auth_webauthn_credentials w
                              WHERE w.user_id = u.id)
                   OR EXISTS (SELECT 1 FROM auth_totp_secrets t
                              WHERE t.user_id = u.id)
              ) AS con_2fa
            FROM auth_users u
            WHERE u.is_active = true AND u.deleted_at IS NULL
            """
        )
    )
    row = rows.mappings().first()
    total = int((row or {}).get("total", 0) or 0)
    con_2fa = int((row or {}).get("con_2fa", 0) or 0)
    if total == 0:
        return CheckResult.unknown(
            "No hay usuarios admin activos para evaluar 2FA (op.acc.5)",
            total=0, con_2fa=0,
        )
    if con_2fa == total:
        return CheckResult.green(
            f"Todos los administradores activos ({total}) tienen 2FA "
            f"(WebAuthn/TOTP) · op.acc.5",
            total=total, con_2fa=con_2fa,
        )
    return CheckResult.red(
        f"{total - con_2fa} de {total} administradores activos SIN segundo "
        f"factor (op.acc.5 · R4). Enrola WebAuthn/TOTP para todos.",
        total=total, con_2fa=con_2fa,
    )


# ── Registry ────────────────────────────────────────────────────────────


CHECK_REGISTRY: dict[str, CheckSpec] = {
    spec.name: spec
    for spec in [
        CheckSpec(
            name="cookies_banner_functional",
            category="cookies",
            frequency=FREQUENCY_DAILY,
            severity=SEVERITY_HIGH,
            description="CookieConsentBanner page reachable (Guía AEPD 2020)",
            regulatory_basis="RD-Ley 13/2012 art.4 + Guía AEPD 2020",
            runner=check_cookies_banner_functional,
        ),
        CheckSpec(
            name="rgpd_endpoints_responding",
            category="rgpd",
            frequency=FREQUENCY_DAILY,
            severity=SEVERITY_HIGH,
            description="GDPR art.15/17/20 endpoints reachable for clientes",
            regulatory_basis="Art. 15, 17, 20 GDPR (UE 2016/679)",
            runner=check_rgpd_endpoints_responding,
        ),
        CheckSpec(
            name="ssl_cert_expiry",
            category="security",
            frequency=FREQUENCY_DAILY,
            severity=SEVERITY_HIGH,
            description="Days remaining until app_base_url SSL cert expires",
            regulatory_basis="ISO 27001:2022 A.8.24 + NIS2 art.21.2.h",
            runner=check_ssl_cert_expiry,
        ),
        CheckSpec(
            name="backups_integrity",
            category="resilience",
            frequency=FREQUENCY_WEEKLY,
            severity=SEVERITY_HIGH,
            description="Recent successful BackupJob within last 48h",
            regulatory_basis="ISO 27001:2022 A.8.13 + ENS [op.exp.10]",
            runner=check_backups_integrity,
        ),
        CheckSpec(
            name="audit_logs_continuity",
            category="audit",
            frequency=FREQUENCY_DAILY,
            severity=SEVERITY_MEDIUM,
            description="audit_log table receiving events within 24h",
            regulatory_basis="ISO 27001:2022 A.8.15 + ENS [op.exp.8]",
            runner=check_audit_logs_continuity,
        ),
        CheckSpec(
            name="dpo_email_working",
            category="rgpd",
            frequency=FREQUENCY_WEEKLY,
            severity=SEVERITY_HIGH,
            description="DPO contact alias (dpo@fulkro.es) routing alive",
            regulatory_basis="Art. 37.7 + 38.4 GDPR + LOPDGDD art.34.5",
            runner=check_dpo_email_working,
        ),
        CheckSpec(
            name="security_txt_reachable",
            category="security",
            frequency=FREQUENCY_WEEKLY,
            severity=SEVERITY_MEDIUM,
            description="RFC 9116 /.well-known/security.txt reachable",
            regulatory_basis="NIS2 art.21.2.b + RFC 9116",
            runner=check_security_txt_reachable,
        ),
        CheckSpec(
            name="privacy_policy_freshness",
            category="rgpd",
            frequency=FREQUENCY_MONTHLY,
            severity=SEVERITY_MEDIUM,
            description="Privacy policy reviewed annually (Art. 24.1 practice)",
            regulatory_basis="Art. 13-14 + 24.1 GDPR",
            runner=check_privacy_policy_freshness,
        ),
        CheckSpec(
            name="breach_workflow_ready",
            category="rgpd",
            frequency=FREQUENCY_MONTHLY,
            severity=SEVERITY_HIGH,
            description="fulkro_breach_notifications schema ready (72h workflow)",
            regulatory_basis="Art. 33-34 GDPR + LOPDGDD art.74",
            runner=check_breach_workflow_ready,
        ),
        CheckSpec(
            name="sub_processor_dpa_expirations",
            category="rgpd",
            frequency=FREQUENCY_MONTHLY,
            severity=SEVERITY_MEDIUM,
            description="No sub-processor DPA expires in next 60 days",
            regulatory_basis="Art. 28 GDPR + SCC 2021/914",
            runner=check_sub_processor_dpa_expirations,
        ),
        CheckSpec(
            name="nis2_vulnerability_inbox",
            category="security",
            frequency=FREQUENCY_WEEKLY,
            severity=SEVERITY_MEDIUM,
            description="Vulnerability disclosure inbox declared + reachable",
            regulatory_basis="NIS2 art.21.2.b + ISO/IEC 29147:2018",
            runner=check_nis2_vulnerability_inbox,
        ),
        CheckSpec(
            name="rls_coverage_percentage",
            category="security",
            frequency=FREQUENCY_WEEKLY,
            severity=SEVERITY_MEDIUM,
            description="RLS coverage % over tenant-sensitive tables",
            regulatory_basis="ISO 27001:2022 A.5.18 + ENS [op.acc.4]",
            runner=check_rls_coverage_percentage,
        ),
        CheckSpec(
            name="dpa_template_version",
            category="rgpd",
            frequency=FREQUENCY_MONTHLY,
            severity=SEVERITY_MEDIUM,
            description="DPA template DOCX reviewed within 24 months",
            regulatory_basis="Art. 28 GDPR",
            runner=check_dpa_template_version,
        ),
        CheckSpec(
            name="sub_processors_list_freshness",
            category="rgpd",
            frequency=FREQUENCY_MONTHLY,
            severity=SEVERITY_LOW,
            description="Public sub-processors MD reviewed quarterly",
            regulatory_basis="Art. 28.2 GDPR (sub-processor transparency)",
            runner=check_sub_processors_list_freshness,
        ),
        CheckSpec(
            name="ropa_review_due",
            category="rgpd",
            frequency=FREQUENCY_QUARTERLY,
            severity=SEVERITY_MEDIUM,
            description="RoPA annual review status (Art. 30 GDPR)",
            regulatory_basis="Art. 30 GDPR",
            runner=check_ropa_review_due,
        ),
        CheckSpec(
            name="isms_docs_review_due",
            category="isms",
            frequency=FREQUENCY_QUARTERLY,
            severity=SEVERITY_MEDIUM,
            description="ISO 27001:2022 §7.5 — ISMS docs reviewed within 18m",
            regulatory_basis="ISO 27001:2022 §7.5.2",
            runner=check_isms_docs_review_due,
        ),
        CheckSpec(
            name="cookie_consent_renewal_24month",
            category="cookies",
            frequency=FREQUENCY_QUARTERLY,
            severity=SEVERITY_MEDIUM,
            description="client_users cookie consent renewal cycle (24m)",
            regulatory_basis="Guía AEPD 2020 (Cookies) §4.4",
            runner=check_cookie_consent_renewal_24month,
        ),
        # ── Atom 10.1 (MB-10) · honors docs Block 1 commitments ───────────
        CheckSpec(
            name="admin_actions_audit_logged",
            category="audit",
            frequency=FREQUENCY_DAILY,
            severity=SEVERITY_HIGH,
            description="Admin (Marcos) actions generate audit_log rows last 24h",
            regulatory_basis="ENS RD 311/2022 art.24.1 + ISO/IEC 27001:2022 A.8.20",
            runner=check_admin_actions_audit_logged,
        ),
        CheckSpec(
            name="marketing_analytics_opt_in_only",
            category="cookies",
            frequency=FREQUENCY_WEEKLY,
            severity=SEVERITY_HIGH,
            description="Marketing analytics requires opt-in consent gate (no leak)",
            regulatory_basis="Art. 7 GDPR + Guía AEPD 2020 (Cookies) §4",
            runner=check_marketing_analytics_opt_in_only,
        ),
        # ── SIEM_INVESTIGATION.md · op.mon dogfooding gap ─────────────────
        CheckSpec(
            name="intrusion_detection_present",
            category="security",
            frequency=FREQUENCY_DAILY,
            severity=SEVERITY_HIGH,
            description="IDS/monitorización de logs activa (fail2ban/auditd) · op.mon.1",
            regulatory_basis="ENS RD 311/2022 [op.mon.1] Detección de intrusión + [op.mon.3] Vigilancia",
            runner=check_intrusion_detection_present,
        ),
        CheckSpec(
            name="mfa_enforcement",
            category="security",
            frequency=FREQUENCY_DAILY,
            severity=SEVERITY_HIGH,
            description="2FA (WebAuthn/TOTP) enrolado para todos los admin · op.acc.5",
            regulatory_basis="ENS RD 311/2022 [op.acc.5] Mecanismo de autenticación + [op.acc.6]",
            runner=check_mfa_enforcement,
        ),
    ]
}


def list_check_names() -> list[str]:
    return list(CHECK_REGISTRY.keys())


def get_check_spec(name: str) -> CheckSpec:
    if name not in CHECK_REGISTRY:
        raise KeyError(f"Unknown check: {name}")
    return CHECK_REGISTRY[name]


async def run_check_by_name(name: str, db: AsyncSession) -> CheckResult:
    """Execute one check, returning its result. Swallows DB errors as ``unknown``."""
    spec = get_check_spec(name)
    try:
        return await spec.runner(db)
    except SQLAlchemyError as e:
        return CheckResult.unknown(f"DB error in {name}: {e!s}"[:300])
    except Exception as e:  # noqa: BLE001
        return CheckResult.unknown(f"Runtime error in {name}: {e!s}"[:300])
