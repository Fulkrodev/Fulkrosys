"""WhatsAppService · MB-8 atom 8.1.

Opt-in flow (Q3.D hybrid):
  1. Marcos admin invites cliente via UI · service stores OTP + sends WA template
  2. Cliente introduces phone E.164 in /portal · receives OTP via WA
  3. Cliente introduces OTP in /portal · verify_otp sets verified_at + opt_in_at

Bidirectional (Q4.C):
  - send_outbound · Marcos sends · stored as direction='outbound'
  - handle_inbound · webhook receives · stored as direction='inbound'

RGPD art.15 export (Q6.D):
  - export_rgpd_art15 · returns all thread + messages JSON for a client_user
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import string
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import phonenumbers
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.client_portal import ClientUser
from backend.app.motors.m31_whatsapp.dialog_360_client import (
    Dialog360Client,
    SendMessageResult,
    get_default_client,
)
from backend.app.motors.m31_whatsapp.models import (
    WhatsAppMessage,
    WhatsAppThread,
)


logger = logging.getLogger(__name__)


OTP_LENGTH = 6
OTP_TTL_MINUTES = 10
MAX_OTP_ATTEMPTS = 5  # lockout anti-brute-force por OTP emitido


class WhatsAppError(Exception):
    """Generic WhatsApp service error."""


@dataclass
class OptInInitiationResult:
    client_user_id: str
    phone_e164: str
    otp_sent: bool
    error: Optional[str] = None


@dataclass
class ThreadOut:
    id: str
    project_id: str
    client_user_id: Optional[str]
    status: str
    last_outbound_at: Optional[str]
    last_inbound_at: Optional[str]
    last_message_preview: Optional[str]
    messages_count: int


@dataclass
class MessageOut:
    id: str
    thread_id: str
    direction: str
    sender_type: str
    content: str
    whatsapp_message_id: Optional[str]
    sent_at: str
    delivered_at: Optional[str]
    read_at: Optional[str]


@dataclass
class RGPDExportPayload:
    client_user_id: str
    threads: list[ThreadOut] = field(default_factory=list)
    messages: list[MessageOut] = field(default_factory=list)


def _generate_otp(length: int = OTP_LENGTH) -> str:
    """6-digit numeric OTP · phone keyboard friendly.

    Usa secrets (CSPRNG) en vez de random.choices (PRNG no criptográfico):
    el OTP es un control de autenticación y debe ser impredecible.
    """
    return "".join(secrets.choice(string.digits) for _ in range(length))


def _hash_otp(otp: str) -> str:
    """SHA-256 hex del OTP · nunca se persiste el OTP en claro."""
    return hashlib.sha256((otp or "").strip().encode("utf-8")).hexdigest()


def validate_phone_e164(raw: str) -> str:
    """Validate + normalize to E.164 format · raises WhatsAppError on invalid."""
    try:
        parsed = phonenumbers.parse(raw, "ES")  # default region ES
    except phonenumbers.NumberParseException as exc:
        raise WhatsAppError(f"Phone parse failed: {exc}")
    if not phonenumbers.is_valid_number(parsed):
        raise WhatsAppError("Phone number invalid for region")
    return phonenumbers.format_number(
        parsed, phonenumbers.PhoneNumberFormat.E164,
    )


class WhatsAppService:
    """6-7 method facade for M31 motor."""

    def __init__(self, client: Optional[Dialog360Client] = None):
        self._client = client or get_default_client()

    async def initiate_opt_in(
        self,
        db: AsyncSession,
        *,
        client_user_id: uuid.UUID,
        phone_raw: str,
    ) -> OptInInitiationResult:
        """Validate phone + generate OTP + send via WA template."""
        try:
            phone_e164 = validate_phone_e164(phone_raw)
        except WhatsAppError as exc:
            return OptInInitiationResult(
                client_user_id=str(client_user_id),
                phone_e164=phone_raw,
                otp_sent=False,
                error=str(exc),
            )

        user = (await db.execute(
            select(ClientUser).where(ClientUser.id == client_user_id)
        )).scalar_one_or_none()
        if user is None:
            raise WhatsAppError(f"ClientUser {client_user_id} not found")

        # M13 · sin proveedor real (modo mock/demo) el OTP NUNCA llega al móvil:
        # send_text devuelve ok=True sin enviar nada → la UI avanzaba a pedir un
        # OTP que jamás llegaba (callejón sin salida). Cortamos honestamente:
        # otp_sent=False + error explícito · NO persistimos un OTP inútil.
        if getattr(self._client, "mock_mode", False):
            return OptInInitiationResult(
                client_user_id=str(client_user_id),
                phone_e164=phone_e164,
                otp_sent=False,
                error=(
                    "WhatsApp todavía no está disponible (modo demo · sin "
                    "proveedor real configurado). Te avisaremos cuando se active."
                ),
            )

        otp = _generate_otp()
        now = datetime.now(timezone.utc)
        user.whatsapp_number = phone_e164
        user.whatsapp_verification_otp = _hash_otp(otp)  # se guarda el HASH
        user.whatsapp_otp_sent_at = now
        user.whatsapp_otp_attempts = 0  # reset lockout al emitir OTP nuevo
        await db.flush()

        # Primer contacto: WhatsApp exige una PLANTILLA aprobada para mensajes
        # business-initiated (el texto libre se rechaza fuera de la ventana de
        # 24h). Si hay plantilla configurada (dialog_360_otp_template · p.ej.
        # plantilla de autenticación con {{1}}=código) la usamos; si no, caemos
        # a texto (válido en mock/dev y dentro de la ventana de 24h).
        from backend.app.config import get_settings
        otp_template = getattr(get_settings(), "dialog_360_otp_template", "") or ""
        if otp_template:
            result = await self._client.send_template(
                to=phone_e164, template_name=otp_template, lang="es", params=[otp],
            )
        else:
            body = f"FULKRO · Tu código de verificación es {otp}. Válido 10 min."
            result = await self._client.send_text(to=phone_e164, body=body)
        if not result.ok:
            return OptInInitiationResult(
                client_user_id=str(client_user_id),
                phone_e164=phone_e164,
                otp_sent=False,
                error=result.error,
            )
        return OptInInitiationResult(
            client_user_id=str(client_user_id),
            phone_e164=phone_e164,
            otp_sent=True,
        )

    async def verify_otp(
        self,
        db: AsyncSession,
        *,
        client_user_id: uuid.UUID,
        otp_input: str,
    ) -> bool:
        """Validate OTP within TTL · set verified_at + opt_in_at."""
        user = (await db.execute(
            select(ClientUser).where(ClientUser.id == client_user_id)
        )).scalar_one_or_none()
        if user is None:
            raise WhatsAppError("ClientUser not found")
        if not user.whatsapp_verification_otp:
            return False
        if not user.whatsapp_otp_sent_at:
            return False
        # Lockout anti-brute-force: tras MAX_OTP_ATTEMPTS fallos el OTP queda
        # invalidado hasta pedir uno nuevo (initiate_opt_in resetea el contador).
        if (user.whatsapp_otp_attempts or 0) >= MAX_OTP_ATTEMPTS:
            return False
        # TTL check
        now = datetime.now(timezone.utc)
        sent = user.whatsapp_otp_sent_at
        if sent.tzinfo is None:
            sent = sent.replace(tzinfo=timezone.utc)
        elapsed_min = (now - sent).total_seconds() / 60
        if elapsed_min > OTP_TTL_MINUTES:
            return False
        # Comparacion en tiempo constante sobre el HASH (nunca el OTP en claro).
        if not secrets.compare_digest(
            _hash_otp(otp_input), user.whatsapp_verification_otp,
        ):
            user.whatsapp_otp_attempts = (user.whatsapp_otp_attempts or 0) + 1
            await db.flush()
            return False
        # OK · mark verified + opt-in active
        user.whatsapp_verified_at = now
        user.whatsapp_opt_in_at = now
        user.whatsapp_verification_otp = None
        user.whatsapp_otp_attempts = 0
        await db.flush()
        return True

    async def get_or_create_thread(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        client_user_id: uuid.UUID,
    ) -> WhatsAppThread:
        """Get active thread or create new one (1:1 cliente↔Marcos)."""
        existing = (await db.execute(
            select(WhatsAppThread).where(
                WhatsAppThread.project_id == project_id,
                WhatsAppThread.client_user_id == client_user_id,
                WhatsAppThread.status == "active",
                WhatsAppThread.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if existing is not None:
            return existing
        thread = WhatsAppThread(
            project_id=project_id,
            client_user_id=client_user_id,
            status="active",
        )
        db.add(thread)
        await db.flush()
        return thread

    async def send_outbound(
        self,
        db: AsyncSession,
        *,
        thread: WhatsAppThread,
        body: str,
        sender_type: str = "marcos",
    ) -> WhatsAppMessage:
        """Persist outbound message + dispatch via Dialog360Client."""
        user = (await db.execute(
            select(ClientUser).where(ClientUser.id == thread.client_user_id)
        )).scalar_one_or_none()
        if user is None or not user.whatsapp_number:
            raise WhatsAppError("Recipient phone not configured")

        result: SendMessageResult = await self._client.send_text(
            to=user.whatsapp_number, body=body,
        )
        now = datetime.now(timezone.utc)
        msg = WhatsAppMessage(
            thread_id=thread.id,
            project_id=thread.project_id,
            direction="outbound",
            sender_type=sender_type,
            content=body,
            whatsapp_message_id=result.whatsapp_message_id,
            sent_at=now,
            failed_at=None if result.ok else now,
            failure_reason=None if result.ok else result.error,
            metadata_jsonb={"raw": result.raw_response} if result.raw_response else {},
        )
        db.add(msg)
        thread.last_outbound_at = now
        thread.last_message_preview = body[:500]
        thread.messages_count = (thread.messages_count or 0) + 1
        await db.flush()
        return msg

    async def handle_inbound(
        self,
        db: AsyncSession,
        *,
        from_phone: str,
        body: str,
        whatsapp_message_id: Optional[str] = None,
    ) -> Optional[WhatsAppMessage]:
        """Webhook inbound · find recipient ClientUser by phone + persist."""
        user = (await db.execute(
            select(ClientUser).where(
                ClientUser.whatsapp_number == from_phone,
                ClientUser.whatsapp_verified_at.isnot(None),
            )
        )).scalar_one_or_none()
        if user is None:
            logger.info(
                "WA inbound from %s · no verified user · ignoring",
                from_phone[:6] + "***",
            )
            return None

        # Find latest active project for this user (single project per client
        # in MVP · same assumption as adaptive_dashboard).
        proj_row = (await db.execute(text(
            "SELECT id FROM projects WHERE client_id = :cid "
            "AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1"
        ), {"cid": str(user.client_id)})).first()
        if proj_row is None:
            return None

        thread = await self.get_or_create_thread(
            db, project_id=proj_row[0], client_user_id=user.id,
        )
        now = datetime.now(timezone.utc)
        msg = WhatsAppMessage(
            thread_id=thread.id,
            project_id=thread.project_id,
            direction="inbound",
            sender_type="cliente",
            content=body,
            whatsapp_message_id=whatsapp_message_id,
            sent_at=now,
        )
        db.add(msg)
        thread.last_inbound_at = now
        thread.last_message_preview = body[:500]
        thread.messages_count = (thread.messages_count or 0) + 1
        await db.flush()
        return msg

    async def export_rgpd_art15(
        self,
        db: AsyncSession,
        client_user_id: uuid.UUID,
    ) -> RGPDExportPayload:
        """Return all threads + messages for a client user · RGPD art.15."""
        threads = (await db.execute(
            select(WhatsAppThread).where(
                WhatsAppThread.client_user_id == client_user_id,
                WhatsAppThread.deleted_at.is_(None),
            )
        )).scalars().all()

        thread_ids = [t.id for t in threads]
        if not thread_ids:
            return RGPDExportPayload(client_user_id=str(client_user_id))

        messages = (await db.execute(
            select(WhatsAppMessage).where(
                WhatsAppMessage.thread_id.in_(thread_ids),
                WhatsAppMessage.deleted_at.is_(None),
            ).order_by(WhatsAppMessage.sent_at.asc())
        )).scalars().all()

        return RGPDExportPayload(
            client_user_id=str(client_user_id),
            threads=[
                ThreadOut(
                    id=str(t.id),
                    project_id=str(t.project_id),
                    client_user_id=(
                        str(t.client_user_id) if t.client_user_id else None
                    ),
                    status=t.status,
                    last_outbound_at=(
                        t.last_outbound_at.isoformat()
                        if t.last_outbound_at else None
                    ),
                    last_inbound_at=(
                        t.last_inbound_at.isoformat()
                        if t.last_inbound_at else None
                    ),
                    last_message_preview=t.last_message_preview,
                    messages_count=t.messages_count or 0,
                )
                for t in threads
            ],
            messages=[
                MessageOut(
                    id=str(m.id),
                    thread_id=str(m.thread_id),
                    direction=m.direction,
                    sender_type=m.sender_type,
                    content=m.content,
                    whatsapp_message_id=m.whatsapp_message_id,
                    sent_at=m.sent_at.isoformat() if m.sent_at else "",
                    delivered_at=(
                        m.delivered_at.isoformat() if m.delivered_at else None
                    ),
                    read_at=m.read_at.isoformat() if m.read_at else None,
                )
                for m in messages
            ],
        )
