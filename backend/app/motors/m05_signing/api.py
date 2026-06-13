"""M05 in-portal signing · REST API · SAN-E v3.MB-5.2.

6 endpoints cliente-facing + 1 admin chain integrity.

Cliente endpoints requieren auth ClientUser (cookie session + CSRF triple
binding pattern existing M21). Admin endpoint requiere require_owner.

NOTA email OTP: este atom NO envia email automáticamente · returns plain
OTP code en el response del request-otp endpoint para que el caller (UI
frontend) maneje display/email vía M18 EmailSender. Decisión simplificada
para evitar coupling tight con M18 templates · futura iteración wire-up
M18 send con template signing/step_up_otp.html (atom 5.2.bis si Marcos).
"""
from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m05_signing.exceptions import (
    IntentExpiredError,
    IntentNotFoundError,
    InvalidIntentStateError,
    OtpExpiredError,
    OtpMaxAttemptsError,
    StepUpOtpRequiredError,
)
from backend.app.motors.m05_signing.models import SigningIntent
from backend.app.motors.m05_signing.schemas import (
    AdminRequestSignatureRequest,
    ChainIntegrityResponse,
    CreateSigningIntentRequest,
    PendingSignatureCard,
    PendingSignaturesResponse,
    RejectIntentRequest,
    RequestOtpResponse,
    SignatureCardView,
    SignCanvasRequest,
    SignedDocumentResponse,
    SigningHistoryClientResponse,
    SigningIntentResponse,
    VerifyOtpRequest,
    VerifySignatureResponse,
)
from backend.app.motors.m05_signing.service import SigningService
from backend.app.motors.m05_signing.signable_types import (
    SIGNABLE_TYPE_LABELS,
    SIGNABLE_TYPES,
)
from backend.app.motors.m21_portal_cliente.api import get_current_client_user


logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# Cliente firmas hub · MB-6 atom 0.2
# ════════════════════════════════════════════════════════════════════

# Signable types operativos · expand cuando MB-6 atoms 2-6 abran nuevos workflows.
# Determina cuáles cards mostrar en /client-portal/firmas-hub (total_expected).
# Chain principal cliente · ENS lifecycle (DdA → MAGERIT → Policies → Pentest →
# Conformidad → DPC anual) · ordered for ChainVisualizer.
_OPERATIVE_SIGNABLE_TYPES: tuple[str, ...] = (
    "dda",
    "magerit_validation",
    "policy_approval",
    "pentest_authorization",
    "conformidad_ens",
    "dpc_anual",
)

# Transient signatures · NOT en main chain (Q6 cement MB-6 atom 3 + 4).
# Periodic/transient · NO lifecycle ENS one-time (incidents · comités retainer).
_TRANSIENT_SIGNABLE_TYPES: tuple[str, ...] = (
    "incident_close",
    "retainer_quarterly_signoff",
)

_PORTAL_PATH_BY_SIGNABLE: dict[str, str] = {
    "dda": "/client-portal/dda",
    "magerit_validation": "/client-portal/magerit",
    "policy_approval": "/client-portal/policies",
    "pentest_authorization": "/client-portal/pentest-authorization",
    "conformidad_ens": "/client-portal/conformidad",
    "dpc_anual": "/client-portal/dpc-anual",
    "incident_close": "/client-portal/incidents",
    "retainer_quarterly_signoff": "/client-portal/retainer-checkin",
    # MB-6 atom 5 · acta_comite outside chain (Q6 c cement) · solo navegación
    # generic firmas-hub si linkea (NO en _OPERATIVE ni _TRANSIENT).
    "acta_comite": "/client-portal/actas",
    # F0-3 (Ejecutable 8 Pasada 16): firmables de gobierno FASE 0 · fuera del
    # main chain (one-time governance) · navegación a firmas pendientes.
    "acta_nombramiento_roles": "/client-portal/firmas-pendientes",
    "plan_adecuacion": "/client-portal/firmas-pendientes",
    "documento_alcance": "/client-portal/firmas-pendientes",
}


client_router = APIRouter(
    prefix="/portal/signing",
    tags=["Motor 05 - In-portal signing (cliente)"],
)


admin_router = APIRouter(
    prefix="/admin/signing",
    tags=["Motor 05 - In-portal signing (admin)"],
    dependencies=[Depends(require_owner)],
)


def _service(db: AsyncSession) -> SigningService:
    return SigningService(db)


async def _ensure_project_belongs_to_client(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: ClientUser,
) -> None:
    """Verify project_id pertenece al client_id del usuario portal · sets tenant context."""
    # FIX(RLS): resolve owner vía get_project_owner (SECURITY DEFINER) ANTES de
    # cualquier query sobre tabla RLS-protegida. El raw SELECT client_id FROM
    # projects corría como fulkro_app (RLS) sin tenant context → 0 filas → 404
    # espurio en proyecto válido. SECURITY DEFINER lee el owner saltando RLS.
    owner = (
        await db.execute(
            sa_text("SELECT get_project_owner(:pid)"),
            {"pid": str(project_id)},
        )
    ).scalar()
    if not owner:
        raise HTTPException(status_code=404, detail="Project no existe")
    if owner != user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project no pertenece al cliente del usuario",
        )
    await set_tenant_context(
        db, client_id=owner, project_id=project_id,
    )


# =====================================================================
# Cliente endpoints
# =====================================================================


@client_router.post(
    "/intents",
    response_model=SigningIntentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_signing_intent(
    body: CreateSigningIntentRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> SigningIntentResponse:
    """Cliente inicia signing intent · validate signable_type + project ownership."""
    if body.signable_type not in SIGNABLE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"signable_type invalid · debe ser uno de {SIGNABLE_TYPES}",
        )
    await _ensure_project_belongs_to_client(db, body.project_id, user)

    intent = await _service(db).create_intent(
        project_id=body.project_id,
        signable_type=body.signable_type,  # type: ignore[arg-type]
        document_hash_sha256=body.document_hash_sha256,
        created_by_user_id=user.id,
        document_id=body.document_id,
        signable_ref_id=body.signable_ref_id,
        signable_ref_type=body.signable_ref_type,
        document_version_id=body.document_version_id,
        intent_payload=body.intent_payload,
    )
    await db.commit()
    return SigningIntentResponse.model_validate(intent)


@client_router.post(
    "/intents/{intent_id}/request-otp",
    response_model=RequestOtpResponse,
)
async def request_step_up_otp(
    intent_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> RequestOtpResponse:
    """Generate 6-digit OTP · TTL 5min · enviado SOLO via email.

    Security: el plain code NUNCA se incluye en este response · solo via
    email out-of-band al ``user.email``. Audit log captura masked email
    (NO code). Compatible con E2E real cliente atom 5.3+.
    """
    try:
        intent = await _service(db)._get_intent_or_404(intent_id)
        await _ensure_project_belongs_to_client(
            db, intent.project_id, user,
        )
        result = await _service(db).request_otp(
            intent_id=intent_id,
            user_id=user.id,
            request_ip=request.client.host if request.client else None,
        )
        await db.commit()
    except IntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IntentExpiredError, InvalidIntentStateError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RequestOtpResponse(
        otp_sent=True,
        sent_to_email_masked=result.sent_to_email_masked,
        expires_in_seconds=result.expires_in_seconds,
        expires_at=result.expires_at,
    )


@client_router.post(
    "/intents/{intent_id}/verify-otp",
    response_model=dict,
)
async def verify_step_up_otp(
    intent_id: uuid.UUID,
    body: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> dict:
    """Verify OTP · max 5 attempts · update intent state si correct."""
    try:
        intent = await _service(db)._get_intent_or_404(intent_id)
        await _ensure_project_belongs_to_client(
            db, intent.project_id, user,
        )
        valid = await _service(db).verify_otp(
            intent_id=intent_id, user_id=user.id, otp_code=body.otp_code,
        )
        await db.commit()
    except IntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OtpExpiredError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    except OtpMaxAttemptsError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    return {"otp_verified": valid}


@client_router.post(
    "/intents/{intent_id}/sign",
    response_model=SignedDocumentResponse,
)
async def sign_intent(
    intent_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> SignedDocumentResponse:
    """Generate Ed25519 signature · finalize intent · hash chain link."""
    try:
        intent = await _service(db)._get_intent_or_404(intent_id)
        await _ensure_project_belongs_to_client(
            db, intent.project_id, user,
        )
        event = await _service(db).sign(
            intent_id=intent_id,
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        # Propagar la firma a la declaración de conformidad: el sign genérico crea
        # el signing_event pero NO marcaba basic_declarations.signed_at/signed_hash
        # → la conformidad nunca se cerraba (PostSignSection no aparecía · cierre
        # roto BÁSICA/MEDIA/ALTA · verificación). Antes del commit (RLS is_local
        # aún activo) · idempotente (signed_at IS NULL).
        if intent.signable_ref_type == "basic_declaration" and intent.signable_ref_id:
            await db.execute(
                sa_text(
                    "UPDATE basic_declarations SET signed_at = :sa, "
                    "signed_hash = :sh WHERE id = :did AND signed_at IS NULL"
                ),
                {
                    "sa": event.created_at,
                    "sh": event.event_hash_sha256,
                    "did": str(intent.signable_ref_id),
                },
            )
        await db.commit()
    except IntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StepUpOtpRequiredError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (IntentExpiredError, InvalidIntentStateError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return SignedDocumentResponse(
        intent_id=intent_id,
        signature_event_id=event.id,
        signed_at=event.created_at,
        event_hash_sha256=event.event_hash_sha256,
    )


@client_router.post(
    "/intents/{intent_id}/reject",
    response_model=dict,
)
async def reject_intent(
    intent_id: uuid.UUID,
    body: RejectIntentRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> dict:
    """Cliente rechaza firma · audit log + canonical Sub-atom 5.A signature.declined."""
    try:
        intent = await _service(db)._get_intent_or_404(intent_id)
        await _ensure_project_belongs_to_client(
            db, intent.project_id, user,
        )
        await _service(db).reject(
            intent_id=intent_id, user_id=user.id, reason=body.reason,
        )
        await _emit_signature_audit_log(
            db,
            project_id=intent.project_id,
            client_id=user.client_id,
            accion="signature.declined",
            registro_id=intent.id,
            payload={
                "signable_type": intent.signable_type,
                "reason": body.reason[:500],
            },
            usuario=str(user.id),
        )
        await db.commit()
    except IntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # Ola 3 #12 · payload ENRIQUECIDO (quién rechazó · qué documento · motivo).
    await _emit_signature_sse(
        project_id=intent.project_id,
        event_type="signing.declined",
        payload={
            "intent_id": str(intent_id),
            "signable_type": intent.signable_type,
            "signable_label": SIGNABLE_TYPE_LABELS.get(
                intent.signable_type, intent.signable_type,
            ),
            "signable_ref_id": (
                str(intent.signable_ref_id) if intent.signable_ref_id else None
            ),
            "signable_ref_type": intent.signable_ref_type,
            "signer_name": (user.full_name or user.email),
            "primary_actor": "cliente",
            "project_id": str(intent.project_id),
            "reason": body.reason[:500],
        },
    )
    return {"rejected": True}


@client_router.get(
    "/intents/{intent_id}",
    response_model=dict,
)
async def get_signing_intent_detail(
    intent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> dict:
    """Get intent state + ordered events log."""
    try:
        intent = await _service(db)._get_intent_or_404(intent_id)
        await _ensure_project_belongs_to_client(
            db, intent.project_id, user,
        )
        return await _service(db).get_intent_detail(intent_id)
    except IntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@client_router.get(
    "/projects/{project_id}/history",
    response_model=SigningHistoryClientResponse,
)
async def get_client_signing_history(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> SigningHistoryClientResponse:
    """Firmas hub cliente · history visualization · MB-6 atom 0.2.

    Returns vista per signable_type operativo (DdA · MAGERIT · Pentest · Conformidad)
    + chain integrity status + readiness_snapshot post-conformidad si signed.

    Cards 'pending_creation' los emite el endpoint cuando no existe intent · cliente
    arranca el flow desde el portal correspondiente (portal_path).
    """
    await _ensure_project_belongs_to_client(db, project_id, user)

    history = await _service(db).get_signing_history(project_id)
    chain_status = await _service(db).verify_chain_integrity(project_id)

    history_by_type: dict[str, dict] = {}
    for item in history:
        intent = item["intent"]
        if intent.signable_type not in history_by_type:
            history_by_type[intent.signable_type] = item

    cards: list[SignatureCardView] = []
    total_signed = 0
    for signable_type in _OPERATIVE_SIGNABLE_TYPES:
        item = history_by_type.get(signable_type)
        portal_path = _PORTAL_PATH_BY_SIGNABLE.get(signable_type, "/client-portal/dashboard")
        label = SIGNABLE_TYPE_LABELS.get(signable_type, signable_type)
        if item is None:
            cards.append(SignatureCardView(
                signable_type=signable_type,
                signable_label=label,
                intent_id=None,
                status="pending_creation",
                signed_at=None,
                signature_event_id=None,
                document_hash_sha256=None,
                event_hash_sha256=None,
                chain_position=None,
                portal_path=portal_path,
            ))
            continue
        intent = item["intent"]
        if item["signed_at"] is not None:
            total_signed += 1
        cards.append(SignatureCardView(
            signable_type=signable_type,
            signable_label=label,
            intent_id=intent.id,
            status=intent.status,
            signed_at=item["signed_at"],
            signature_event_id=item["signature_event_id"],
            document_hash_sha256=intent.document_hash_sha256,
            event_hash_sha256=item["event_hash_sha256"],
            chain_position=item["chain_position"],
            portal_path=portal_path,
        ))

    readiness_snapshot = await _get_conformidad_readiness_snapshot(db, project_id)

    return SigningHistoryClientResponse(
        project_id=project_id,
        signatures=cards,
        chain_valid=chain_status["chain_valid"],
        broken_links_count=len(chain_status["broken_links"]),
        total_signed=total_signed,
        total_expected=len(_OPERATIVE_SIGNABLE_TYPES),
        readiness_snapshot=readiness_snapshot,
    )


async def _get_conformidad_readiness_snapshot(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict | None:
    """Returns readiness_snapshot_jsonb de basic_declarations si conformidad signed.

    Pattern audit trail compliance ENAC · captura state DdA+MAGERIT+Pentest+evidencias
    cuando cliente firmó la declaración ENS (atom 5.6.A migration 24cbdeb40cfc).
    """
    from sqlalchemy import text as sa_text
    row = await db.execute(
        sa_text(
            "SELECT readiness_snapshot_jsonb FROM basic_declarations "
            "WHERE project_id = :pid AND signed_at IS NOT NULL "
            "ORDER BY signed_at DESC LIMIT 1"
        ),
        {"pid": str(project_id)},
    )
    hit = row.first()
    if hit is None or hit[0] is None:
        return None
    return hit[0]


# =====================================================================
# Ejecutable 7.7 · canonical audit_log + SSE + accompaniment helpers
# =====================================================================


async def _emit_signature_audit_log(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    client_id: uuid.UUID | None,
    accion: str,
    registro_id: uuid.UUID,
    payload: dict | None = None,
    usuario: str = "system",
) -> None:
    """Sub-atom 5.A 3-way OR audit_log emit · best-effort try/except.

    Canonical events Ejecutable 7.7:
    - signature.requested · signature.signed · signature.declined
    - signature.verified · signature.expired
    """
    try:
        await db.execute(
            sa_text(
                "INSERT INTO audit_log "
                "(id, tabla, registro_id, accion, usuario, "
                "project_id, client_id, payload_new, timestamp) "
                "VALUES (gen_random_uuid(), 'signing_intents', "
                ":rid, :accion, :usuario, :pid, :cid, :payload, now())"
            ),
            {
                "rid": str(registro_id),
                "accion": accion,
                "usuario": usuario[:255],
                "pid": str(project_id),
                "cid": str(client_id) if client_id else None,
                "payload": json.dumps(payload or {}),
            },
        )
        await db.flush()
    except Exception as exc:  # pragma: no cover · best-effort
        logger.warning(
            "audit_log emit signature event %s failed (best-effort): %s",
            accion, exc,
        )


async def _emit_signature_sse(
    *,
    project_id: uuid.UUID,
    event_type: str,
    payload: dict,
) -> None:
    """SSE dispatch project channel · Pattern #14 dual emit · best-effort."""
    try:
        channel = f"project:{project_id}"
        await sse_dispatcher.dispatch(channel, event_type, payload)
    except Exception as exc:
        logger.warning(
            "SSE dispatch %s failed (best-effort): %s",
            event_type, exc,
        )


# Mapping signable_type → required-before accompaniment state
# (block state advance hasta required signatures completed)
SIGNATURE_REQUIRED_FOR_STATE: dict[str, str] = {
    "dda": "docs_collected",
    "magerit_validation": "docs_collected",
    "policy_approval": "internal_audit_scheduled",
    "pentest_authorization": "enac_audit_scheduled",
    "conformidad_ens": "enac_audit_passed",
    "dpc_anual": "periodic_review_scheduled",
}


# =====================================================================
# Cliente endpoint · TIER 1 canvas sign (NO OTP re-prompt)
# =====================================================================


@client_router.post(
    "/intents/{intent_id}/sign-canvas",
    response_model=SignedDocumentResponse,
)
async def sign_intent_canvas(
    intent_id: uuid.UUID,
    body: SignCanvasRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> SignedDocumentResponse:
    """TIER 1 canvas firma · Ed25519 + hash chain + canvas + nombre + apellido.

    NO OTP re-prompt (cliente session already MFA-authenticated portal).
    audit_log canonical event 'signature.signed' Sub-atom 5.A 3-way OR.
    SSE dispatch project channel 'signing.signed' · cliente realtime.
    """
    try:
        intent = await _service(db)._get_intent_or_404(intent_id)
        await _ensure_project_belongs_to_client(
            db, intent.project_id, user,
        )
        event = await _service(db).sign_canvas(
            intent_id=intent_id,
            user_id=user.id,
            signature_canvas_dataurl=body.signature_canvas_dataurl,
            signed_name=body.signed_name,
            signed_surname=body.signed_surname,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        # Sub-atom 5.A audit_log canonical emit
        await _emit_signature_audit_log(
            db,
            project_id=intent.project_id,
            client_id=user.client_id,
            accion="signature.signed",
            registro_id=intent.id,
            payload={
                "signable_type": intent.signable_type,
                "event_id": str(event.id),
                "signed_at": event.created_at.isoformat(),
                "signed_name": body.signed_name,
                "signed_surname": body.signed_surname,
                "event_hash_sha256": event.event_hash_sha256,
                "tier": "TIER_1_CANVAS",
            },
            usuario=str(user.id),
        )
        await db.commit()
    except IntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IntentExpiredError, InvalidIntentStateError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # SSE + Pattern #14 dual emit · best-effort (post-commit)
    # Ola 3 #12 · payload ENRIQUECIDO para que el admin vea "Fulanito firmó
    # {documento}" en realtime, no "alguien firmó algo".
    await _emit_signature_sse(
        project_id=intent.project_id,
        event_type="signing.signed",
        payload={
            "intent_id": str(intent_id),
            "signable_type": intent.signable_type,
            "signable_label": SIGNABLE_TYPE_LABELS.get(
                intent.signable_type, intent.signable_type,
            ),
            "signable_ref_id": (
                str(intent.signable_ref_id) if intent.signable_ref_id else None
            ),
            "signable_ref_type": intent.signable_ref_type,
            "signer_name": f"{body.signed_name} {body.signed_surname}".strip(),
            "primary_actor": "cliente",
            "project_id": str(intent.project_id),
            "signed_at": event.created_at.isoformat(),
            "event_hash_sha256": event.event_hash_sha256,
        },
    )

    return SignedDocumentResponse(
        intent_id=intent_id,
        signature_event_id=event.id,
        signed_at=event.created_at,
        event_hash_sha256=event.event_hash_sha256,
    )


# =====================================================================
# Cliente endpoint · pending signatures hub
# =====================================================================


@client_router.get(
    "/projects/{project_id}/pending",
    response_model=PendingSignaturesResponse,
)
async def list_pending_signatures(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> PendingSignaturesResponse:
    """Cliente pending signatures action list · project-scoped.

    Returns intents en estado pending/otp_required/otp_verified · NO signed
    NO rejected NO expired.
    """
    await _ensure_project_belongs_to_client(db, project_id, user)

    stmt = (
        select(SigningIntent)
        .where(
            SigningIntent.project_id == project_id,
            SigningIntent.status.in_(
                ("pending", "otp_required", "otp_verified"),
            ),
        )
        .order_by(SigningIntent.created_at.desc())
    )
    intents = (await db.execute(stmt)).scalars().all()

    cards: list[PendingSignatureCard] = []
    for intent in intents:
        cards.append(PendingSignatureCard(
            intent_id=intent.id,
            signable_type=intent.signable_type,
            signable_label=SIGNABLE_TYPE_LABELS.get(
                intent.signable_type, intent.signable_type,
            ),
            document_id=intent.document_id,
            document_hash_sha256=intent.document_hash_sha256,
            requires_step_up_otp=intent.requires_step_up_otp,
            expires_at=intent.expires_at,
            created_at=intent.created_at,
            portal_path=_PORTAL_PATH_BY_SIGNABLE.get(
                intent.signable_type, "/client-portal/firmas-pendientes",
            ),
        ))

    return PendingSignaturesResponse(
        cliente_user_id=user.id,
        total_pending=len(cards),
        pending=cards,
    )


# =====================================================================
# Admin endpoints
# =====================================================================


@admin_router.get(
    "/projects/{project_id}/chain-integrity",
    response_model=ChainIntegrityResponse,
)
async def admin_verify_chain_integrity(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ChainIntegrityResponse:
    """Admin verify entire project signing chain integrity · audit purpose."""
    # signing_* es fail-CLOSED (RLS project-scoped · R06). Este endpoint admin
    # (require_owner) verifica la cadena de un proyecto SIN fijar contexto de tenant,
    # así que se eleva a BYPASSRLS para leer las filas (auditoría read-only).
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    result = await _service(db).verify_chain_integrity(project_id)
    return ChainIntegrityResponse(**result)


@admin_router.post(
    "/intents/request",
    response_model=SigningIntentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_request_signature(
    body: AdminRequestSignatureRequest,
    db: AsyncSession = Depends(get_db),
) -> SigningIntentResponse:
    """Admin trigger signature intent on behalf of cliente.

    audit_log canonical event 'signature.requested' Sub-atom 5.A 3-way OR.
    SSE dispatch project channel 'signing.requested' · cliente realtime
    notification pending firma.
    """
    if body.signable_type not in SIGNABLE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"signable_type invalid · debe ser uno de {SIGNABLE_TYPES}",
        )
    # Resolve client_id from project_id
    proj_row = await db.execute(
        sa_text("SELECT client_id FROM projects WHERE id = :pid"),
        {"pid": str(body.project_id)},
    )
    proj_hit = proj_row.first()
    if proj_hit is None:
        raise HTTPException(status_code=404, detail="Project no existe")
    client_id = proj_hit[0]
    await set_tenant_context(
        db, client_id=client_id, project_id=body.project_id,
    )

    intent = await _service(db).create_intent(
        project_id=body.project_id,
        signable_type=body.signable_type,  # type: ignore[arg-type]
        document_hash_sha256=body.document_hash_sha256,
        created_by_user_id=body.cliente_user_id,
        document_id=body.document_id,
        signable_ref_id=body.signable_ref_id,
        signable_ref_type=body.signable_ref_type,
        intent_payload=body.intent_payload,
    )
    await _emit_signature_audit_log(
        db,
        project_id=body.project_id,
        client_id=client_id,
        accion="signature.requested",
        registro_id=intent.id,
        payload={
            "signable_type": body.signable_type,
            "document_id": str(body.document_id) if body.document_id else None,
            "cliente_user_id": str(body.cliente_user_id),
            "requested_by": "admin",
        },
        usuario="admin",
    )
    await db.commit()

    await _emit_signature_sse(
        project_id=body.project_id,
        event_type="signing.requested",
        payload={
            "intent_id": str(intent.id),
            "signable_type": body.signable_type,
            "expires_at": intent.expires_at.isoformat(),
            "portal_path": _PORTAL_PATH_BY_SIGNABLE.get(
                body.signable_type, "/client-portal/firmas-pendientes",
            ),
        },
    )
    return SigningIntentResponse.model_validate(intent)


@admin_router.get(
    "/intents/{intent_id}/verify",
    response_model=VerifySignatureResponse,
)
async def admin_verify_intent_signature(
    intent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> VerifySignatureResponse:
    """Admin verify Ed25519 signature integrity for a specific intent.

    audit_log canonical event 'signature.verified' Sub-atom 5.A · best-effort.
    """
    # signing_* fail-CLOSED (R06) · endpoint admin (require_owner) sin contexto de
    # tenant → eleva a BYPASSRLS para resolver el intent por id (auditoría read-only).
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        intent = await _service(db)._get_intent_or_404(intent_id)
    except IntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    result = await _service(db).verify_intent_signature(intent_id)

    # Resolve client_id for audit emit
    proj_row = await db.execute(
        sa_text("SELECT client_id FROM projects WHERE id = :pid"),
        {"pid": str(intent.project_id)},
    )
    proj_hit = proj_row.first()
    client_id = proj_hit[0] if proj_hit else None

    await _emit_signature_audit_log(
        db,
        project_id=intent.project_id,
        client_id=client_id,
        accion="signature.verified",
        registro_id=intent.id,
        payload={
            "valid": result.get("valid"),
            "signature_verify": result.get("signature_verify"),
            "verified_by": "admin",
        },
        usuario="admin",
    )
    await db.commit()

    from datetime import datetime
    signed_at_str = result.get("signed_at")
    signed_at_dt = (
        datetime.fromisoformat(signed_at_str)
        if signed_at_str else None
    )
    return VerifySignatureResponse(
        intent_id=intent_id,
        valid=result.get("valid", False),
        event_id=(
            uuid.UUID(result["event_id"])
            if result.get("event_id") else None
        ),
        signed_at=signed_at_dt,
        signature_hex_8chars=result.get("signature_hex_8chars"),
        event_hash_sha256=result.get("event_hash_sha256"),
        signature_verify=result.get("signature_verify"),
        reason=result.get("reason"),
    )
