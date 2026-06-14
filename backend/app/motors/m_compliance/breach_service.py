"""Art. 33 / 34 GDPR breach notification service (atom 9.bis.2).

Workflow:

1. Marcos registers a breach (``register_breach``). The 72h SLA clock
   starts at ``detected_at``. ``breach_code`` is auto-generated as
   ``BREACH_YYYY_NNN``.
2. Within 72h, Marcos triggers ``notify_aepd`` which renders the AEPD
   notification email and sends it. ``notification_status`` advances to
   ``aepd_notified``.
3. If individuals are at high risk (Art. 34), Marcos triggers
   ``notify_affected_clients`` which emails each affected ClientUser.

Emails are sent through the shared ``EmailSender`` (Postmark backend in
production, captured in-memory in tests).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.email.sender import get_email_sender
from backend.app.models.compliance_breach_erasure import (
    BREACH_AEPD_NOTIFIED,
    BREACH_CLIENTS_NOTIFIED,
    BREACH_PENDING,
    FulkroBreachNotification,
)


# AEPD breach notification mailbox. Real address per AEPD guidance; in
# tests we capture via the mock backend (``EmailSender`` backend=mock).
AEPD_NOTIFICATION_EMAIL = "notificaciones@aepd.es"


_CODE_RE = re.compile(r"^BREACH_(\d{4})_(\d{3})$")


def _next_breach_code(latest_code: str | None, year: int | None = None) -> str:
    """Return the next breach code for the given year (YYYY)."""
    y = year or datetime.now(timezone.utc).year
    if latest_code:
        m = _CODE_RE.match(latest_code)
        if m and int(m.group(1)) == y:
            return f"BREACH_{y}_{int(m.group(2)) + 1:03d}"
    return f"BREACH_{y}_001"


class BreachNotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 1. Register ────────────────────────────────────────────────

    async def register_breach(
        self,
        *,
        detected_at: datetime,
        severity: str,
        description: str,
        data_categories_affected: list[str],
        data_subjects_count: int | None = None,
        root_cause: str | None = None,
        containment_actions: str | None = None,
        affected_client_user_ids: list[UUID] | None = None,
        reporter_user_id: UUID | None = None,
    ) -> FulkroBreachNotification:
        # Generate breach_code based on most recent same-year code.
        from sqlalchemy import desc

        latest = (
            await self.db.execute(
                select(FulkroBreachNotification.breach_code)
                .order_by(desc(FulkroBreachNotification.created_at))
                .limit(1)
            )
        ).scalar()
        code = _next_breach_code(latest)

        row = FulkroBreachNotification(
            breach_code=code,
            detected_at=detected_at,
            reported_at=datetime.now(timezone.utc),
            severity=severity,
            description=description,
            data_categories_affected=list(data_categories_affected),
            data_subjects_count=data_subjects_count,
            root_cause=root_cause,
            containment_actions=containment_actions,
            notification_status=BREACH_PENDING,
            affected_client_user_ids=(
                [str(uid) for uid in affected_client_user_ids]
                if affected_client_user_ids
                else None
            ),
            reporter_user_id=(str(reporter_user_id) if reporter_user_id else None),
        )
        self.db.add(row)
        await self.db.flush()
        return row

    # ── 2. AEPD notification ───────────────────────────────────────

    async def notify_aepd(self, breach_id: UUID) -> FulkroBreachNotification:
        row = await self._get(breach_id)
        # Render + send AEPD email (Postmark / mock).
        from backend.app.motors.m_compliance.email_design.mjml_compiler import (
            render_email as render_mjml_email,
        )
        # Identidad fiscal FULKRO (FUENTE ÚNICA · punto #44) en el contexto.
        from backend.app.core.fiscal_identity import get_fiscal_identity
        fi = await get_fiscal_identity(self.db)
        html = render_mjml_email(
            "aepd_breach_notification.mjml",
            dict(breach=row, now=datetime.now(timezone.utc), fiscal=fi),
        )
        subject = (
            f"[FULKRO] Notificación brecha Art. 33 GDPR · {row.breach_code}"
        )
        sent_ok = False
        try:
            result = await get_email_sender().send(
                self.db,
                to=AEPD_NOTIFICATION_EMAIL,
                subject=subject,
                html_body=html,
                template_used="aepd_breach_notification",
            )
            sent_ok = bool(getattr(result, "ok", True)) if result is not None else True
        except Exception as e:  # noqa: BLE001
            logger.warning("AEPD email send failed: {}", e)

        # Solo atestar la notificación Art.33 si el envío fue exitoso (antes se
        # marcaba 'notificado a AEPD' aunque el email fallara → falsa atestación).
        if sent_ok:
            row.notified_aepd_at = datetime.now(timezone.utc)
            row.notification_status = BREACH_AEPD_NOTIFIED
        await self.db.flush()
        return row

    # ── 3. Affected clients notification ───────────────────────────

    async def notify_affected_clients(
        self, breach_id: UUID
    ) -> tuple[FulkroBreachNotification, int]:
        """Email each affected ClientUser (Art. 34 GDPR). Returns (row, sent)."""
        from sqlalchemy import text as _text

        row = await self._get(breach_id)
        if not row.affected_client_user_ids:
            row.notified_clients_at = datetime.now(timezone.utc)
            row.notification_status = BREACH_CLIENTS_NOTIFIED
            await self.db.flush()
            return row, 0

        # Fetch emails of affected client_users (skip tombstoned/anonymised).
        emails_rows = await self.db.execute(
            _text(
                """
                SELECT email FROM client_users
                WHERE id::text = ANY(:ids)
                  AND email NOT LIKE 'anonymised_%@removed.fulkro.local'
                """
            ),
            {"ids": row.affected_client_user_ids},
        )
        emails = [r[0] for r in emails_rows.all()]

        sent_count = 0
        for email in emails:
            from backend.app.motors.m_compliance.email_design.mjml_compiler import (
                render_email as render_mjml_email,
            )
            html = render_mjml_email(
                "client_breach_notification.mjml",
                dict(breach=row, cliente_email=email, now=datetime.now(timezone.utc)),
            )
            try:
                result = await get_email_sender().send(
                    self.db,
                    to=email,
                    subject=(
                        "[FULKRO] Notificación de incidente de seguridad "
                        "(Art. 34 RGPD)"
                    ),
                    html_body=html,
                    template_used="client_breach_notification",
                )
                if result.ok:
                    sent_count += 1
            except Exception as e:  # noqa: BLE001
                logger.warning("Affected client email failed for {}: {}", email, e)

        row.notified_clients_at = datetime.now(timezone.utc)
        row.notification_status = BREACH_CLIENTS_NOTIFIED
        await self.db.flush()
        return row, sent_count

    # ── helpers ────────────────────────────────────────────────────

    async def _get(self, breach_id: UUID) -> FulkroBreachNotification:
        row = (
            await self.db.execute(
                select(FulkroBreachNotification).where(
                    FulkroBreachNotification.id == breach_id
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise KeyError(f"Breach {breach_id} not found")
        return row


def hours_remaining_for_aepd(detected_at: datetime) -> float:
    """Compute hours remaining of the 72h Art. 33 SLA."""
    deadline = detected_at + timedelta(hours=72)
    return (deadline - datetime.now(timezone.utc)).total_seconds() / 3600


# Late imports for hours_remaining_for_aepd helper.
from datetime import timedelta  # noqa: E402
