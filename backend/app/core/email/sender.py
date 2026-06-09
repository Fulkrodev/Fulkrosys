"""EmailSender con 3 backends + email_log + retry — Paso 7.

API unificada:

    sender = get_email_sender()
    result = await sender.send(
        db, to="user@example.com", subject="...",
        html_body="<p>...</p>", text_body="...",
        template_used="oferta_retainer",
        magic_link_id=uuid4,
    )
    if result.ok:
        print(result.message_id)
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING, Any

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from backend.app.admin_settings.email_config import SmtpConfig

logger = logging.getLogger(__name__)


VALID_BACKENDS = ("smtp", "postmark_api", "mock")
DEFAULT_BACKEND = "mock"

# Exponential backoff para retry: 2s, 8s, 32s
RETRY_DELAYS_SECONDS = (2, 8, 32)
MAX_RETRIES = len(RETRY_DELAYS_SECONDS)

# SAN-E v3.MB-5.3.D · captura in-memory mock backend para E2E Playwright.
# Module-level list · NEVER en producción (backend != 'mock' = no captura).
# Acceso via /api/v1/_dev/captured-emails (env-gated · doble defensa).
_CAPTURED_EMAILS: list[dict] = []
_MAX_CAPTURED = 200


def get_captured_emails(
    *,
    to: str | None = None,
    subject_pattern: str | None = None,
) -> list[dict]:
    """Returns captured mock emails (newest last) · filterable.

    Solo backend == 'mock' captura. Para uso E2E Playwright vía endpoint
    /_dev/captured-emails (env-gated NO production).
    """
    emails = list(_CAPTURED_EMAILS)
    if to:
        emails = [e for e in emails if e["to"] == to]
    if subject_pattern:
        pat = subject_pattern.lower()
        emails = [e for e in emails if pat in e["subject"].lower()]
    return emails


def reset_captured_emails() -> None:
    """Clear captured mock emails · for test isolation."""
    _CAPTURED_EMAILS.clear()


@dataclass
class EmailResult:
    ok: bool
    message_id: str | None = None
    backend_used: str = ""
    retry_count: int = 0
    error: str | None = None
    email_log_id: uuid.UUID | None = None


class EmailSendError(Exception):
    pass


class EmailSender:
    """Fachada que selecciona backend según ``Settings.email_backend``.

    Sub-fase TODO-EMAIL-SENDER-CONSOLIDATION-001 (post-FASE 5): single
    source of truth = Settings env. Los `os.environ.get(...)` directos
    fueron eliminados — el selector backend, Postmark token y
    from_email/from_name se leen de Settings (parseados via
    ``parse_smtp_from`` para coherencia con SmtpConfig).
    """

    def __init__(
        self,
        backend: str | None = None,
        smtp_config: "SmtpConfig | None" = None,
    ):
        from backend.app.config import get_settings

        settings = get_settings()
        b = (backend or settings.email_backend).strip().lower()
        if b not in VALID_BACKENDS:
            logger.warning(
                "Backend email invalido %r, usando %r", b, DEFAULT_BACKEND,
            )
            b = DEFAULT_BACKEND
        self.backend = b
        self._smtp_config = smtp_config

    async def send(
        self,
        db: AsyncSession,
        *,
        to: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        template_used: str | None = None,
        magic_link_id: uuid.UUID | None = None,
        client_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
        cc: list[str] | None = None,
        retry: bool = True,
    ) -> EmailResult:
        """Envia email + loguea en email_log. Retry opcional.

        ``cc`` (carbon copy) se entrega realmente en los 3 backends (SMTP header
        Cc + envelope · Postmark Cc · mock capture). Antes era un campo aceptado
        pero NO transmitido (review #11)."""
        cc_list = [c for c in (cc or []) if c] or None
        log_id = await self._persist_email_log(
            db,
            recipient=to, subject=subject,
            template_used=template_used, html_body=html_body,
            text_body=text_body,
            magic_link_id=magic_link_id, client_id=client_id,
            metadata={**(metadata or {}), **({"cc": cc_list} if cc_list else {})}
            or None,
        )
        attempts = RETRY_DELAYS_SECONDS if retry else (0,)
        last_error: str | None = None
        message_id: str | None = None

        for attempt_idx, delay in enumerate(attempts):
            if delay > 0 and attempt_idx > 0:
                await asyncio.sleep(delay)
            try:
                message_id = await self._send_one_attempt(
                    db=db,
                    to=to, subject=subject,
                    html_body=html_body,
                    text_body=text_body or _html_to_text(html_body),
                    cc=cc_list,
                )
                await self._mark_sent(db, log_id, message_id, attempt_idx)
                return EmailResult(
                    ok=True, message_id=message_id,
                    backend_used=self.backend,
                    retry_count=attempt_idx, email_log_id=log_id,
                )
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "EmailSender attempt %d failed: %s",
                    attempt_idx + 1, last_error,
                )
                continue

        # All attempts failed
        await self._mark_failed(db, log_id, last_error or "unknown", MAX_RETRIES)
        return EmailResult(
            ok=False, message_id=None, backend_used=self.backend,
            retry_count=MAX_RETRIES, error=last_error,
            email_log_id=log_id,
        )

    # ── Persistence ────────────────────────────────────────────────

    async def _persist_email_log(
        self,
        db: AsyncSession,
        *,
        recipient: str,
        subject: str,
        template_used: str | None,
        html_body: str,
        text_body: str | None,
        magic_link_id: uuid.UUID | None,
        client_id: uuid.UUID | None,
        metadata: dict[str, Any] | None,
    ) -> uuid.UUID:
        now = datetime.now(timezone.utc)
        email_id = uuid.uuid4()
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            import json
            await db.execute(sa_text(
                "INSERT INTO email_log (id, recipient, subject, template_used, "
                "body_html, body_text, backend_used, queued_at, "
                "delivery_status, retry_count, magic_link_id, client_id, "
                "metadata_jsonb, created_at) "
                "VALUES (:id, :to, :subj, :tpl, :html, :text, :be, :q, "
                "'queued', 0, :mlid, :cid, "
                "CAST(:meta AS JSONB), :created)"
            ), {
                "id": str(email_id), "to": recipient, "subj": subject,
                "tpl": template_used,
                "html": html_body, "text": text_body,
                "be": self.backend, "q": now, "created": now,
                "mlid": str(magic_link_id) if magic_link_id else None,
                "cid": str(client_id) if client_id else None,
                "meta": json.dumps(metadata) if metadata else None,
            })
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))
        return email_id

    async def _mark_sent(
        self, db: AsyncSession, log_id: uuid.UUID,
        message_id: str, retry_count: int,
    ) -> None:
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            await db.execute(sa_text(
                "UPDATE email_log SET delivery_status = 'sent', "
                "sent_at = now(), message_id = :mid, retry_count = :rc "
                "WHERE id = :id"
            ), {"id": str(log_id), "mid": message_id, "rc": retry_count})
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))

    async def _mark_failed(
        self, db: AsyncSession, log_id: uuid.UUID,
        error: str, retry_count: int,
    ) -> None:
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            await db.execute(sa_text(
                "UPDATE email_log SET delivery_status = 'failed', "
                "error_message = :err, retry_count = :rc "
                "WHERE id = :id"
            ), {"id": str(log_id), "err": error[:2000], "rc": retry_count})
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))

    # ── Backend dispatch ───────────────────────────────────────────

    async def _send_one_attempt(
        self, *, db: AsyncSession, to: str, subject: str,
        html_body: str, text_body: str, cc: list[str] | None = None,
    ) -> str:
        if self.backend == "mock":
            return await self._send_mock(to, subject, html_body, cc)
        if self.backend == "postmark_api":
            return await self._send_postmark(to, subject, html_body, text_body, cc)
        if self.backend == "smtp":
            return await self._send_smtp(db, to, subject, html_body, text_body, cc)
        raise EmailSendError(f"Backend desconocido: {self.backend!r}")

    async def _send_mock(
        self, to: str, subject: str, html_body: str,
        cc: list[str] | None = None,
    ) -> str:
        message_id = f"mock-{uuid.uuid4()}"
        logger.info(
            "EmailSender[mock] to=%s cc=%s subject=%r (body %d chars)",
            to, cc or [], subject[:80], len(html_body),
        )
        # SAN-E v3.MB-5.3.D · captura in-memory para E2E tests Playwright.
        # NUNCA usar en producción · solo backend == 'mock' (dev/test).
        _CAPTURED_EMAILS.append({
            "to": to,
            "cc": cc or [],
            "subject": subject,
            "html_body": html_body,
            "message_id": message_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        })
        # Cap memoria · drop oldest si > MAX_CAPTURED.
        while len(_CAPTURED_EMAILS) > _MAX_CAPTURED:
            _CAPTURED_EMAILS.pop(0)
        return message_id

    async def _send_postmark(
        self, to: str, subject: str, html_body: str, text_body: str,
        cc: list[str] | None = None,
    ) -> str:
        from backend.app.admin_settings.email_config import parse_smtp_from
        from backend.app.config import get_settings

        settings = get_settings()
        token = settings.postmark_api_token.get_secret_value()
        if not token:
            raise EmailSendError(
                "Settings.postmark_api_token no configurado — "
                "use backend='mock' o configure Postmark"
            )
        from_name, from_email = parse_smtp_from(settings.smtp_from)
        from_header = f"{from_name} <{from_email}>" if from_name else from_email

        import httpx
        payload = {
            "From": from_header,
            "To": to,
            "Subject": subject,
            "HtmlBody": html_body,
            "TextBody": text_body,
            "MessageStream": "outbound",
        }
        if cc:
            payload["Cc"] = ", ".join(cc)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.postmarkapp.com/email",
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-Postmark-Server-Token": token,
                },
            )
        if resp.status_code >= 400:
            raise EmailSendError(
                f"Postmark HTTP {resp.status_code}: {resp.text[:500]}"
            )
        data = resp.json()
        return data.get("MessageID", "postmark-unknown")

    async def _send_smtp(
        self, db: AsyncSession, to: str, subject: str,
        html_body: str, text_body: str, cc: list[str] | None = None,
    ) -> str:
        from backend.app.admin_settings.email_config import get_smtp_config

        cfg = self._smtp_config or await get_smtp_config(db)

        if not cfg.host:
            raise EmailSendError(
                "SMTP host no configurado en Settings env ni AdminSettings.smtp"
            )

        host = cfg.host
        port = cfg.port
        user = cfg.username
        password = cfg.password
        use_tls = cfg.use_tls

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        if cfg.from_name:
            msg["From"] = f"{cfg.from_name} <{cfg.from_email}>"
        else:
            msg["From"] = cfg.from_email
        msg["To"] = to
        if cc:
            # send_message deriva los destinatarios del envelope de las cabeceras
            # To/Cc · con la cabecera Cc los CC reciben el correo de verdad.
            msg["Cc"] = ", ".join(cc)
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # SMTP bloqueante en thread para no frenar el event loop
        def _do_send() -> str:
            if use_tls:
                ctx = ssl.create_default_context()
                with smtplib.SMTP(host, port, timeout=30) as server:
                    server.starttls(context=ctx)
                    if user:
                        server.login(user, password or "")
                    server.send_message(msg)
            else:
                with smtplib.SMTP(host, port, timeout=30) as server:
                    if user:
                        server.login(user, password or "")
                    server.send_message(msg)
            return msg["Message-ID"] or f"smtp-{int(time.time())}"

        return await asyncio.to_thread(_do_send)


def _html_to_text(html: str) -> str:
    """Fallback plain-text cuando el caller no proporciona uno."""
    import re
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


# ══════════════════════════════════════════════════════════════════════
# Singleton factory
# ══════════════════════════════════════════════════════════════════════


_sender: EmailSender | None = None


def get_email_sender(*, force_backend: str | None = None) -> EmailSender:
    """Retorna singleton. ``force_backend`` para tests."""
    global _sender
    if force_backend is not None:
        return EmailSender(backend=force_backend)
    if _sender is None:
        _sender = EmailSender()
    return _sender


def reset_email_sender() -> None:
    """Invalidar el singleton — util en tests."""
    global _sender
    _sender = None
