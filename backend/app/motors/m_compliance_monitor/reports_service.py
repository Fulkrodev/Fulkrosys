"""ComplianceReportsService — dual-mode storage for status reports.

Storage modes selected by ``settings.app_env``:

- ``development`` (or any non-production env):
    Write Markdown report to Desktop folder
    ``/mnt/c/Users/Usuario/Desktop/Fulkro compliance/08-Self_Monitoring_Reports/``
    with filename ``{YYYY-MM-DD}_compliance_status_report.md``.
    If the Desktop folder does not exist (CI, server without WSL mount),
    falls back to ``inline`` mode (DB-only).

- ``production``:
    Upload to MinIO bucket ``fulkro-compliance-reports`` under key
    ``08-Self_Monitoring_Reports/{YYYY-MM-DD}_compliance_status_report.md``.
    A 7-day signed download URL is generated and stored alongside the
    report row + emailed to Marcos.

In both modes a ``ComplianceReport`` row is persisted (source of truth).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.models.compliance_monitor import ComplianceReport


COMPLIANCE_BUCKET = "fulkro-compliance-reports"
DESKTOP_FOLDER_DEFAULT = Path("/mnt/c/Users/Usuario/Desktop/Fulkro compliance")
REPORTS_SUBDIR = "08-Self_Monitoring_Reports"
SIGNED_URL_TTL_DAYS = 7


def _is_production() -> bool:
    return get_settings().app_env.lower() == "production"


def _desktop_root() -> Path:
    """Return the configured Desktop compliance root folder."""
    return DESKTOP_FOLDER_DEFAULT


class ComplianceReportsService:
    """Persists + ships compliance status reports.

    Always writes a ``ComplianceReport`` row. Side artifact (file or MinIO
    object) and ``storage_mode`` depend on ``settings.app_env``.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Public API ──────────────────────────────────────────────────

    async def persist_report(
        self,
        *,
        report_type: str,
        period_start: datetime,
        period_end: datetime,
        summary: dict[str, Any],
        body_markdown: str,
        email_recipient: str | None = None,
    ) -> ComplianceReport:
        """Persist report row + ship artifact (Desktop in dev, MinIO in prod)."""
        if _is_production():
            storage_mode, storage_path, signed_url, signed_expiry = self._ship_minio(
                period_end, body_markdown
            )
        else:
            storage_mode, storage_path = self._ship_desktop(period_end, body_markdown)
            signed_url, signed_expiry = None, None

        row = ComplianceReport(
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            summary=summary,
            body_markdown=body_markdown,
            storage_mode=storage_mode,
            storage_path=storage_path,
            signed_url=signed_url,
            signed_url_expires_at=signed_expiry,
            email_sent_to=email_recipient,
            email_sent_at=None,  # set by caller after email send
            generated_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        await self.db.flush()
        return row

    # ── Desktop (development) ───────────────────────────────────────

    def _ship_desktop(
        self, period_end: datetime, body_markdown: str
    ) -> tuple[str, str | None]:
        """Write the report MD to the Desktop folder, or fallback inline."""
        root = _desktop_root() / REPORTS_SUBDIR
        try:
            root.mkdir(parents=True, exist_ok=True)
            filename = f"{period_end.strftime('%Y-%m-%d')}_compliance_status_report.md"
            path = root / filename
            path.write_text(body_markdown, encoding="utf-8")
            logger.info("Compliance report written to {}", path)
            return "desktop", str(path)
        except OSError as e:
            # CI / Linux server without WSL mount: keep inline-only
            logger.warning(
                "Desktop folder not writable ({}) — using inline mode", e
            )
            return "inline", None

    # ── MinIO (production) ──────────────────────────────────────────

    def _ship_minio(
        self, period_end: datetime, body_markdown: str
    ) -> tuple[str, str | None, str | None, datetime | None]:
        """Upload to MinIO + generate a 7-day signed URL."""
        try:
            from backend.app.core.storage.minio_client import (
                get_minio_client,
                put_object,
            )
        except ImportError:
            logger.warning("minio client unavailable — falling back to inline")
            return "inline", None, None, None

        filename = f"{period_end.strftime('%Y-%m-%d')}_compliance_status_report.md"
        key = f"{REPORTS_SUBDIR}/{filename}"
        try:
            put_object(
                COMPLIANCE_BUCKET,
                key,
                body_markdown.encode("utf-8"),
                content_type="text/markdown; charset=utf-8",
                metadata={"period_end": period_end.isoformat()},
            )
        except Exception as e:  # noqa: BLE001
            logger.error("MinIO put failed: {} — falling back to inline", e)
            return "inline", None, None, None

        try:
            client = get_minio_client()
            signed_url = client.presigned_get_object(
                COMPLIANCE_BUCKET, key, expires=timedelta(days=SIGNED_URL_TTL_DAYS)
            )
            expires_at = datetime.now(timezone.utc) + timedelta(days=SIGNED_URL_TTL_DAYS)
        except Exception as e:  # noqa: BLE001
            logger.warning("Signed URL generation failed: {}", e)
            signed_url, expires_at = None, None

        return "minio", f"{COMPLIANCE_BUCKET}/{key}", signed_url, expires_at

    # ── Documentation export (atom 9.bis.4 helper) ──────────────────

    @staticmethod
    def export_docs_to_storage(category_subdir: str, md_files: dict[str, str]) -> dict[str, str]:
        """Copy a set of MD files to Desktop folder or MinIO depending on env.

        Returns ``{filename: storage_path}`` for callers that want to log
        artifacts. ``category_subdir`` is one of the 9 numbered subdirs
        (``01-RGPD``, ``04-ISMS_ISO27001``, etc).
        """
        if _is_production():
            return ComplianceReportsService._export_docs_minio(category_subdir, md_files)
        return ComplianceReportsService._export_docs_desktop(category_subdir, md_files)

    @staticmethod
    def _export_docs_desktop(category_subdir: str, md_files: dict[str, str]) -> dict[str, str]:
        root = _desktop_root() / category_subdir
        results: dict[str, str] = {}
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning("Desktop export unavailable ({}) — skipping", e)
            return results
        for name, content in md_files.items():
            path = root / name
            try:
                path.write_text(content, encoding="utf-8")
                results[name] = str(path)
            except OSError as e:
                logger.warning("Failed to write {}: {}", path, e)
        return results

    @staticmethod
    def _export_docs_minio(category_subdir: str, md_files: dict[str, str]) -> dict[str, str]:
        try:
            from backend.app.core.storage.minio_client import put_object
        except ImportError:
            return {}
        results: dict[str, str] = {}
        for name, content in md_files.items():
            key = f"{category_subdir}/{name}"
            try:
                put_object(
                    COMPLIANCE_BUCKET,
                    key,
                    content.encode("utf-8"),
                    content_type="text/markdown; charset=utf-8",
                )
                results[name] = f"{COMPLIANCE_BUCKET}/{key}"
            except Exception as e:  # noqa: BLE001
                logger.warning("MinIO export of {} failed: {}", key, e)
        return results
