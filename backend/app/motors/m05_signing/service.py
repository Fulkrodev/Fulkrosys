"""SigningService · core in-portal signing · SAN-E v3.MB-5.2.

Methods:
- create_intent · cliente inicia firma flow
- request_otp · 6-digit OTP via email · TTL 5min · BD storage
- verify_otp · max 5 attempts · update intent state
- sign · Ed25519 signature + hash chain link
- reject · cliente rechaza · audit log
- verify_chain_integrity · admin audit endpoint
- get_intent_detail · intent + events log

Hash chain: previous_signature_hash = SHA256(prev_signature) per project.
event_hash_sha256 = SHA256(payload + previous_hash + signature).
"""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from backend.app.motors.m05_signing.email_templates import (
    mask_email,
    render_step_up_otp_email,
)
from backend.app.motors.m05_signing.exceptions import (
    IntentExpiredError,
    IntentNotFoundError,
    InvalidIntentStateError,
    OtpExpiredError,
    OtpMaxAttemptsError,
    StepUpOtpRequiredError,
)
from backend.app.motors.m05_signing.keypair import (
    get_public_key_bytes,
    sign_payload,
)
from backend.app.motors.m05_signing.models import (
    SigningEvent,
    SigningIntent,
    SigningOtpCode,
)
from backend.app.motors.m05_signing.signable_types import (
    DEFAULT_INTENT_TTL_HOURS,
    OTP_CODE_LENGTH,
    OTP_MAX_ATTEMPTS,
    OTP_TTL_SECONDS,
    REQUIRES_STEP_UP_OTP,
    SignableType,
)


@dataclass(slots=True)
class RequestOtpResult:
    """Result de SigningService.request_otp.

    NOTA crítica seguridad: ``otp_code_plain`` es SERVICE-INTERNAL · NUNCA
    debe retornarse via API response. La capa API (api.py) construye un
    schema de response distinto que solo incluye ``sent_to_email_masked``
    + ``expires_*``. El plain code va EXCLUSIVAMENTE via email out-of-band.
    """

    otp_code_plain: str
    sent_to_email_masked: str
    expires_in_seconds: int
    expires_at: datetime
    email_ok: bool


class SigningService:
    """Core service in-portal signing."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ----------------------------------------------------------------
    # Intent lifecycle
    # ----------------------------------------------------------------

    async def create_intent(
        self,
        *,
        project_id: uuid.UUID,
        signable_type: SignableType,
        document_hash_sha256: str,
        created_by_user_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
        signable_ref_id: uuid.UUID | None = None,
        signable_ref_type: str | None = None,
        document_version_id: uuid.UUID | None = None,
        intent_payload: dict | None = None,
        ttl_hours: int = DEFAULT_INTENT_TTL_HOURS,
    ) -> SigningIntent:
        """Create signing intent · cliente inicia firma flow."""
        requires_otp = signable_type in REQUIRES_STEP_UP_OTP
        intent = SigningIntent(
            project_id=project_id,
            signable_type=signable_type,
            signable_ref_id=signable_ref_id,
            signable_ref_type=signable_ref_type,
            document_id=document_id,
            document_hash_sha256=document_hash_sha256,
            document_version_id=document_version_id,
            intent_payload=intent_payload or {},
            status="otp_required" if requires_otp else "pending",
            requires_step_up_otp=requires_otp,
            expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
            created_by_user_id=created_by_user_id,
        )
        self.db.add(intent)
        await self.db.flush()

        await self._log_event(
            project_id=project_id,
            signing_intent_id=intent.id,
            event_type="intent_created",
            actor_user_id=created_by_user_id,
            actor_type="client_user",
            event_payload={
                "signable_type": signable_type,
                "document_hash_sha256": document_hash_sha256,
                "requires_step_up_otp": requires_otp,
            },
        )
        return intent

    # ----------------------------------------------------------------
    # OTP step-up (email + DB storage · 6-digit · TTL 5min · 5 attempts)
    # ----------------------------------------------------------------

    async def request_otp(
        self,
        *,
        intent_id: uuid.UUID,
        user_id: uuid.UUID,
        request_ip: str | None = None,
    ) -> RequestOtpResult:
        """Generate 6-digit OTP · store sha256 hash + TTL 5min · send email.

        Email sent via core EmailSender · plain code SOLO via email
        out-of-band · audit log captura masked email (NO code). El plain
        code regresa en ``RequestOtpResult.otp_code_plain`` para uso
        SERVICE-INTERNAL · API layer DEBE redactar antes de response.
        """
        intent = await self._get_intent_or_404(intent_id)
        if not intent.requires_step_up_otp:
            raise InvalidIntentStateError(
                "Intent does not require step-up OTP"
            )
        if intent.status not in ("otp_required",):
            raise InvalidIntentStateError(
                f"Intent in state {intent.status} · cannot request OTP"
            )
        if intent.expires_at < datetime.now(UTC):
            raise IntentExpiredError("Intent expired")

        # Look up ClientUser email + name (necesarios pre-render email)
        user_row = await self.db.execute(
            sa_text(
                "SELECT email, full_name, client_id FROM client_users "
                "WHERE id = :uid AND deleted_at IS NULL"
            ),
            {"uid": str(user_id)},
        )
        user_hit = user_row.first()
        if user_hit is None:
            raise InvalidIntentStateError(
                f"client_user {user_id} no existe o eliminado"
            )
        user_email, user_full_name, user_client_id = user_hit

        # Generate 6-digit code
        otp_code = "".join(
            str(secrets.randbelow(10)) for _ in range(OTP_CODE_LENGTH)
        )
        code_hash = hashlib.sha256(otp_code.encode()).hexdigest()
        expires = datetime.now(UTC) + timedelta(seconds=OTP_TTL_SECONDS)

        # Upsert OTP code (delete previous · insert new)
        existing_stmt = select(SigningOtpCode).where(
            SigningOtpCode.signing_intent_id == intent_id,
            SigningOtpCode.user_id == user_id,
        )
        existing = (await self.db.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            existing.code_sha256 = code_hash
            # NO resetear `attempts`: si se reseteara, un atacante esquivaría el
            # bloqueo por max_attempts simplemente re-solicitando OTP (fuerza
            # bruta ilimitada sobre 6 dígitos). El contador persiste entre
            # regeneraciones de código (anti brute-force-by-re-request).
            existing.expires_at = expires
            existing.consumed_at = None
            existing.created_at = datetime.now(UTC)
        else:
            otp = SigningOtpCode(
                signing_intent_id=intent_id,
                user_id=user_id,
                code_sha256=code_hash,
                attempts=0,
                max_attempts=OTP_MAX_ATTEMPTS,
                expires_at=expires,
            )
            self.db.add(otp)
        await self.db.flush()

        # Render email + send via core EmailSender
        from backend.app.core.email.sender import get_email_sender

        subject, html_body, text_body = render_step_up_otp_email(
            otp_code=otp_code,
            signable_type=intent.signable_type,
            user_name=(
                user_full_name
                or (user_email.split("@")[0] if user_email else "Hola")
            ),
            expires_in_minutes=OTP_TTL_SECONDS // 60,
            request_ip=request_ip,
        )
        sender = get_email_sender()
        email_result = await sender.send(
            self.db,
            to=user_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            template_used="m05_signing/step_up_otp",
            client_id=user_client_id,
            metadata={
                "signing_intent_id": str(intent.id),
                "project_id": str(intent.project_id),
                "signable_type": intent.signable_type,
                "event_type": "step_up_otp",
            },
        )

        # Audit log · NUNCA contiene plain code · solo masked email
        masked = mask_email(user_email)
        await self._log_event(
            project_id=intent.project_id,
            signing_intent_id=intent_id,
            event_type="otp_sent",
            actor_user_id=user_id,
            actor_type="client_user",
            event_payload={
                "sent_to_email_masked": masked,
                "expires_in_seconds": OTP_TTL_SECONDS,
                "expires_at": expires.isoformat(),
                "request_ip": request_ip,
                "email_send_ok": email_result.ok,
            },
        )

        return RequestOtpResult(
            otp_code_plain=otp_code,
            sent_to_email_masked=masked,
            expires_in_seconds=OTP_TTL_SECONDS,
            expires_at=expires,
            email_ok=email_result.ok,
        )

    async def verify_otp(
        self,
        *,
        intent_id: uuid.UUID,
        user_id: uuid.UUID,
        otp_code: str,
    ) -> bool:
        """Verify OTP · raises if expired/max attempts · returns True/False."""
        intent = await self._get_intent_or_404(intent_id)

        otp_stmt = select(SigningOtpCode).where(
            SigningOtpCode.signing_intent_id == intent_id,
            SigningOtpCode.user_id == user_id,
            SigningOtpCode.consumed_at.is_(None),
        )
        otp = (await self.db.execute(otp_stmt)).scalar_one_or_none()
        if otp is None:
            raise OtpExpiredError("OTP no encontrado o consumido")
        if otp.expires_at < datetime.now(UTC):
            raise OtpExpiredError("OTP expirado")
        if otp.attempts >= otp.max_attempts:
            raise OtpMaxAttemptsError(
                "Max OTP attempts reached · intent locked"
            )

        otp.attempts += 1
        provided_hash = hashlib.sha256(otp_code.encode()).hexdigest()
        if provided_hash != otp.code_sha256:
            await self.db.flush()
            return False

        otp.consumed_at = datetime.now(UTC)
        intent.status = "otp_verified"
        intent.updated_at = datetime.now(UTC)
        await self.db.flush()

        await self._log_event(
            project_id=intent.project_id,
            signing_intent_id=intent_id,
            event_type="otp_verified",
            actor_user_id=user_id,
            actor_type="client_user",
            event_payload={"attempts": otp.attempts},
        )
        return True

    # ----------------------------------------------------------------
    # Sign (Ed25519 · hash chain link)
    # ----------------------------------------------------------------

    async def sign(
        self,
        *,
        intent_id: uuid.UUID,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        signature_message_extras: dict | None = None,
    ) -> SigningEvent:
        """Generate Ed25519 signature · hash chain link · update intent.signed."""
        intent = await self._get_intent_or_404(intent_id)
        # Step-up OTP precedence: si intent requires_step_up_otp, status debe
        # ser otp_verified · cualquier otro estado pre-firma (otp_required ·
        # pending) → StepUpOtpRequiredError (más específico que InvalidIntentStateError).
        if intent.requires_step_up_otp and intent.status != "otp_verified":
            raise StepUpOtpRequiredError(
                "Step-up OTP verification required before signing"
            )
        if intent.status not in ("pending", "otp_verified"):
            raise InvalidIntentStateError(
                f"Intent in state {intent.status} · cannot sign"
            )
        if intent.expires_at < datetime.now(UTC):
            intent.status = "expired"
            intent.updated_at = datetime.now(UTC)
            await self.db.flush()
            raise IntentExpiredError("Intent expired")

        # Per-document advisory lock (Pattern #22) · serializa firmas
        # concurrentes del mismo documento para que _get_last_signature_hash lea
        # un previous_hash estable (evita doble-firma en carrera con el mismo
        # eslabón de cadena). Mismo patrón que sign_canvas.
        doc_lock_key = f"signing_document_{intent.document_id or intent.id}"
        await self.db.execute(
            sa_text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": doc_lock_key},
        )

        # Build signature message (deterministic JSON sorted keys)
        signed_at_iso = datetime.now(UTC).isoformat()
        message_dict: dict = {
            "intent_id": str(intent.id),
            "project_id": str(intent.project_id),
            "signable_type": intent.signable_type,
            "document_hash_sha256": intent.document_hash_sha256,
            "signed_at": signed_at_iso,
            "signed_by_user_id": str(user_id),
            "intent_payload": intent.intent_payload,
        }
        if signature_message_extras:
            message_dict["extras"] = signature_message_extras

        message_bytes = json.dumps(
            message_dict, sort_keys=True, default=str
        ).encode("utf-8")
        signature_bytes = sign_payload(message_bytes)
        public_key_bytes = get_public_key_bytes()

        # Hash chain · previous_signature_hash from last signed event in project
        previous_hash = await self._get_last_signature_hash(intent.project_id)

        event_hash_input = (
            message_bytes + (previous_hash or "").encode() + signature_bytes
        )
        event_hash = hashlib.sha256(event_hash_input).hexdigest()

        intent.status = "signed"
        intent.updated_at = datetime.now(UTC)
        await self.db.flush()

        event = await self._log_event(
            project_id=intent.project_id,
            signing_intent_id=intent.id,
            event_type="signature_generated",
            actor_user_id=user_id,
            actor_type="client_user",
            event_payload=message_dict,
            signature_ed25519=signature_bytes,
            signature_public_key=public_key_bytes,
            signature_message=message_bytes.decode("utf-8"),
            previous_signature_hash=previous_hash,
            event_hash_sha256=event_hash,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return event

    # ----------------------------------------------------------------
    # Sign canvas TIER 1 (Ejecutable 7.7 · NO OTP re-prompt)
    # ----------------------------------------------------------------

    async def sign_canvas(
        self,
        *,
        intent_id: uuid.UUID,
        user_id: uuid.UUID,
        signature_canvas_dataurl: str,
        signed_name: str,
        signed_surname: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        signature_message_extras: dict | None = None,
    ) -> SigningEvent:
        """TIER 1 canvas sign · Ed25519 + hash chain + canvas image + nombre + apellido.

        NO OTP re-prompt (cliente already MFA-authenticated portal session).
        Compatible con TODOS signable_type (override REQUIRES_STEP_UP_OTP frozenset
        cuando canvas data + name + surname provided · TIER 1 path).

        Bypassa step-up OTP gate sostained · doctrine: la captura visual canvas
        + nombre + apellido + IP + Ed25519 system signature + hash chain audit
        constituye TIER 1 firma electrónica simple eIDAS Art. 25.1 (ADR-009/010).
        """
        intent = await self._get_intent_or_404(intent_id)
        if intent.status in ("signed", "rejected", "expired"):
            raise InvalidIntentStateError(
                f"Intent already terminal: {intent.status}"
            )
        if intent.expires_at < datetime.now(UTC):
            intent.status = "expired"
            intent.updated_at = datetime.now(UTC)
            await self.db.flush()
            raise IntentExpiredError("Intent expired")

        # Per-document advisory lock (Pattern #22 reuse) · serializes
        # concurrent admin/cliente simultaneous sign attempts safe.
        doc_lock_key = f"signing_document_{intent.document_id or intent.id}"
        await self.db.execute(
            sa_text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": doc_lock_key},
        )

        # Build deterministic signature message (sorted keys JSON)
        signed_at_iso = datetime.now(UTC).isoformat()
        # SHA256 of canvas dataurl (NOT the dataurl itself · keeps message size bounded)
        canvas_hash = hashlib.sha256(
            signature_canvas_dataurl.encode("utf-8")
        ).hexdigest()
        message_dict: dict = {
            "intent_id": str(intent.id),
            "project_id": str(intent.project_id),
            "signable_type": intent.signable_type,
            "document_hash_sha256": intent.document_hash_sha256,
            "signed_at": signed_at_iso,
            "signed_by_user_id": str(user_id),
            "signed_name": signed_name,
            "signed_surname": signed_surname,
            "signature_canvas_sha256": canvas_hash,
            "intent_payload": intent.intent_payload,
            "tier": "TIER_1_CANVAS",
        }
        if signature_message_extras:
            message_dict["extras"] = signature_message_extras

        message_bytes = json.dumps(
            message_dict, sort_keys=True, default=str
        ).encode("utf-8")
        signature_bytes = sign_payload(message_bytes)
        public_key_bytes = get_public_key_bytes()

        # Hash chain link
        previous_hash = await self._get_last_signature_hash(intent.project_id)
        event_hash_input = (
            message_bytes + (previous_hash or "").encode() + signature_bytes
        )
        event_hash = hashlib.sha256(event_hash_input).hexdigest()

        intent.status = "signed"
        intent.updated_at = datetime.now(UTC)
        await self.db.flush()

        event = await self._log_event(
            project_id=intent.project_id,
            signing_intent_id=intent.id,
            event_type="signature_generated",
            actor_user_id=user_id,
            actor_type="client_user",
            event_payload=message_dict,
            signature_ed25519=signature_bytes,
            signature_public_key=public_key_bytes,
            signature_message=message_bytes.decode("utf-8"),
            previous_signature_hash=previous_hash,
            event_hash_sha256=event_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            signature_canvas_dataurl=signature_canvas_dataurl,
            signed_name=signed_name,
            signed_surname=signed_surname,
        )
        return event

    # ----------------------------------------------------------------
    # Reject
    # ----------------------------------------------------------------

    async def reject(
        self,
        *,
        intent_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
    ) -> SigningEvent:
        """Cliente rechaza firma · update intent.status='rejected' + audit log."""
        intent = await self._get_intent_or_404(intent_id)
        if intent.status in ("signed", "rejected", "expired"):
            raise InvalidIntentStateError(
                f"Intent already terminal: {intent.status}"
            )
        intent.status = "rejected"
        intent.updated_at = datetime.now(UTC)
        await self.db.flush()

        return await self._log_event(
            project_id=intent.project_id,
            signing_intent_id=intent_id,
            event_type="rejected",
            actor_user_id=user_id,
            actor_type="client_user",
            event_payload={"reason": reason[:500]},
        )

    # ----------------------------------------------------------------
    # Verify chain integrity (admin audit endpoint)
    # ----------------------------------------------------------------

    async def verify_chain_integrity(
        self, project_id: uuid.UUID,
    ) -> dict:
        """Verify entire project signing chain · returns dict report.

        Recomputes expected previous_signature_hash from each prev event's
        signature_ed25519 SHA256 · detects tampering.
        """
        stmt = (
            select(SigningEvent)
            .where(
                SigningEvent.project_id == project_id,
                SigningEvent.event_type == "signature_generated",
            )
            .order_by(SigningEvent.created_at)
        )
        events = (await self.db.execute(stmt)).scalars().all()

        broken_links: list[dict] = []
        for i, event in enumerate(events):
            if i == 0:
                if event.previous_signature_hash is not None:
                    broken_links.append({
                        "position": i,
                        "event_id": str(event.id),
                        "issue": "first event has previous_signature_hash != NULL",
                    })
                continue
            prev_event = events[i - 1]
            if prev_event.signature_ed25519 is None:
                broken_links.append({
                    "position": i,
                    "event_id": str(event.id),
                    "issue": "previous event has no signature bytes",
                })
                continue
            expected_prev_hash = hashlib.sha256(
                prev_event.signature_ed25519
            ).hexdigest()
            if event.previous_signature_hash != expected_prev_hash:
                broken_links.append({
                    "position": i,
                    "event_id": str(event.id),
                    "issue": (
                        f"hash mismatch · expected "
                        f"{expected_prev_hash[:16]}... · got "
                        f"{(event.previous_signature_hash or 'NULL')[:16]}..."
                    ),
                })

        return {
            "project_id": str(project_id),
            "total_signatures": len(events),
            "broken_links": broken_links,
            "chain_valid": len(broken_links) == 0,
        }

    # ----------------------------------------------------------------
    # Cliente firmas hub history (atom 0.2 MB-6)
    # ----------------------------------------------------------------

    async def get_signing_history(
        self, project_id: uuid.UUID,
    ) -> list[dict]:
        """Lista signed/pending intents project + chain position.

        Returns una lista de dicts ordenada por created_at ascendente:
          {intent, signed_at, signature_event_id, event_hash_sha256, chain_position}

        chain_position es 1-indexed (1, 2, 3, ...) sobre signature_generated
        events en orden cronológico. Pending/rejected intents tienen chain_position=None.
        """
        intents_stmt = (
            select(SigningIntent)
            .where(SigningIntent.project_id == project_id)
            .order_by(SigningIntent.created_at)
        )
        intents = (await self.db.execute(intents_stmt)).scalars().all()

        events_stmt = (
            select(SigningEvent)
            .where(
                SigningEvent.project_id == project_id,
                SigningEvent.event_type == "signature_generated",
            )
            .order_by(SigningEvent.created_at)
        )
        events = (await self.db.execute(events_stmt)).scalars().all()

        events_by_intent: dict[uuid.UUID, tuple[SigningEvent, int]] = {
            ev.signing_intent_id: (ev, idx + 1)
            for idx, ev in enumerate(events)
        }

        history: list[dict] = []
        for intent in intents:
            pair = events_by_intent.get(intent.id)
            if pair is None:
                history.append({
                    "intent": intent,
                    "signed_at": None,
                    "signature_event_id": None,
                    "event_hash_sha256": None,
                    "chain_position": None,
                })
            else:
                event, position = pair
                history.append({
                    "intent": intent,
                    "signed_at": event.created_at,
                    "signature_event_id": event.id,
                    "event_hash_sha256": event.event_hash_sha256,
                    "chain_position": position,
                })
        return history

    # ----------------------------------------------------------------
    # Detail (intent + events)
    # ----------------------------------------------------------------

    async def get_intent_detail(
        self, intent_id: uuid.UUID,
    ) -> dict:
        """Returns intent + ordered events log + chain position."""
        intent = await self._get_intent_or_404(intent_id)
        events_stmt = (
            select(SigningEvent)
            .where(SigningEvent.signing_intent_id == intent_id)
            .order_by(SigningEvent.created_at)
        )
        events = (await self.db.execute(events_stmt)).scalars().all()

        return {
            "intent": {
                "id": str(intent.id),
                "project_id": str(intent.project_id),
                "signable_type": intent.signable_type,
                "signable_ref_id": (
                    str(intent.signable_ref_id) if intent.signable_ref_id else None
                ),
                "document_id": (
                    str(intent.document_id) if intent.document_id else None
                ),
                "document_hash_sha256": intent.document_hash_sha256,
                "status": intent.status,
                "requires_step_up_otp": intent.requires_step_up_otp,
                "expires_at": intent.expires_at.isoformat(),
                "created_by_user_id": str(intent.created_by_user_id),
                "created_at": intent.created_at.isoformat(),
                "updated_at": (
                    intent.updated_at.isoformat() if intent.updated_at else None
                ),
            },
            "events": [
                {
                    "id": str(ev.id),
                    "event_type": ev.event_type,
                    "actor_user_id": (
                        str(ev.actor_user_id) if ev.actor_user_id else None
                    ),
                    "actor_type": ev.actor_type,
                    "event_payload": ev.event_payload,
                    "previous_signature_hash": ev.previous_signature_hash,
                    "event_hash_sha256": ev.event_hash_sha256,
                    "created_at": ev.created_at.isoformat(),
                }
                for ev in events
            ],
        }

    # ----------------------------------------------------------------
    # Helpers privados
    # ----------------------------------------------------------------

    async def _get_intent_or_404(
        self, intent_id: uuid.UUID,
    ) -> SigningIntent:
        intent = await self.db.get(SigningIntent, intent_id)
        if intent is None:
            raise IntentNotFoundError(f"Intent {intent_id} no existe")
        return intent

    async def _get_last_signature_hash(
        self, project_id: uuid.UUID,
    ) -> str | None:
        """Get SHA256(prev_signature) for hash chain linking."""
        stmt = (
            select(SigningEvent.signature_ed25519)
            .where(
                SigningEvent.project_id == project_id,
                SigningEvent.event_type == "signature_generated",
            )
            .order_by(desc(SigningEvent.created_at))
            .limit(1)
        )
        result = (await self.db.execute(stmt)).scalar_one_or_none()
        if result is None:
            return None
        return hashlib.sha256(result).hexdigest()

    async def _log_event(
        self,
        *,
        project_id: uuid.UUID,
        signing_intent_id: uuid.UUID,
        event_type: str,
        actor_user_id: uuid.UUID | None,
        actor_type: str,
        event_payload: dict,
        signature_ed25519: bytes | None = None,
        signature_public_key: bytes | None = None,
        signature_message: str | None = None,
        previous_signature_hash: str | None = None,
        event_hash_sha256: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        signature_canvas_dataurl: str | None = None,
        signed_name: str | None = None,
        signed_surname: str | None = None,
    ) -> SigningEvent:
        """Log signing event · INMUTABLE."""
        # event_hash_sha256 calculado outside para signature_generated;
        # otros events usan SHA256(payload) simple.
        if event_hash_sha256 is None:
            payload_bytes = json.dumps(
                event_payload, sort_keys=True, default=str
            ).encode("utf-8")
            event_hash_sha256 = hashlib.sha256(payload_bytes).hexdigest()

        # NOTA: Postgres ``now()`` retorna transaction START time (NO call time),
        # por lo que multiple events insertados en una sola transaction
        # comparten created_at idéntico · rompe ORDER BY created_at DESC en
        # _get_last_signature_hash. Solución: set created_at Python-side con
        # datetime.now(UTC) que SI cambia entre llamadas dentro de la misma
        # transaction (incluyendo microseconds).
        event = SigningEvent(
            project_id=project_id,
            signing_intent_id=signing_intent_id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            event_payload=event_payload,
            signature_ed25519=signature_ed25519,
            signature_public_key=signature_public_key,
            signature_message=signature_message,
            previous_signature_hash=previous_signature_hash,
            event_hash_sha256=event_hash_sha256,
            ip_address=ip_address,
            user_agent=user_agent,
            signature_canvas_dataurl=signature_canvas_dataurl,
            signed_name=signed_name,
            signed_surname=signed_surname,
            created_at=datetime.now(UTC),
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def verify_intent_signature(
        self, intent_id: uuid.UUID,
    ) -> dict:
        """Verify Ed25519 signature integrity + hash chain link · admin audit.

        Returns dict {valid, intent_id, event_id, signed_at, signature_hex_8chars,
        message_match, prev_hash_match, public_key_match}.
        """
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )

        intent = await self._get_intent_or_404(intent_id)
        ev_stmt = (
            select(SigningEvent)
            .where(
                SigningEvent.signing_intent_id == intent_id,
                SigningEvent.event_type == "signature_generated",
            )
            .order_by(desc(SigningEvent.created_at))
            .limit(1)
        )
        event = (await self.db.execute(ev_stmt)).scalar_one_or_none()
        if event is None:
            return {
                "valid": False,
                "intent_id": str(intent_id),
                "reason": "no signature_generated event",
            }

        result: dict = {
            "intent_id": str(intent_id),
            "event_id": str(event.id),
            "signed_at": event.created_at.isoformat(),
            "signature_hex_8chars": (
                event.signature_ed25519.hex()[:8]
                if event.signature_ed25519 else None
            ),
            "event_hash_sha256": event.event_hash_sha256,
        }
        if event.signature_ed25519 is None or event.signature_public_key is None:
            result["valid"] = False
            result["reason"] = "signature bytes missing"
            return result

        try:
            pubkey = Ed25519PublicKey.from_public_bytes(
                event.signature_public_key
            )
            pubkey.verify(
                event.signature_ed25519,
                (event.signature_message or "").encode("utf-8"),
            )
            result["valid"] = True
            result["signature_verify"] = "ok"
        except InvalidSignature:
            result["valid"] = False
            result["signature_verify"] = "invalid"
        except Exception as exc:  # pragma: no cover
            result["valid"] = False
            result["signature_verify"] = f"error: {exc}"
        return result
