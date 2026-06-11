"""M31 WhatsApp API · admin + cliente + webhook · atom 8.1."""
from __future__ import annotations

import hmac
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.config import get_settings
from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m31_whatsapp.dialog_360_client import get_default_client
from backend.app.motors.m31_whatsapp.models import (
    WhatsAppMessage,
    WhatsAppThread,
)
from backend.app.motors.m31_whatsapp.service import (
    WhatsAppError,
    WhatsAppService,
)


# ─── Admin router (Marcos-only) ─────────────────────────────────────

admin_router = APIRouter(
    prefix="/admin/whatsapp",
    tags=["admin - WhatsApp"],
    dependencies=[Depends(require_owner)],
)


class InviteOptInBody(BaseModel):
    phone_raw: str = Field(..., min_length=6, max_length=30)


@admin_router.post("/invite/{client_user_id}")
async def admin_invite_opt_in(
    client_user_id: uuid.UUID,
    body: InviteOptInBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Marcos initiates opt-in · sends OTP to a cliente's phone."""
    svc = WhatsAppService()
    try:
        result = await svc.initiate_opt_in(
            db, client_user_id=client_user_id, phone_raw=body.phone_raw,
        )
    except WhatsAppError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return {
        "client_user_id": result.client_user_id,
        "phone_e164": result.phone_e164,
        "otp_sent": result.otp_sent,
        "error": result.error,
    }


@admin_router.get("/threads")
async def admin_list_threads(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Cross-cliente threads list · admin bypass RLS via SET LOCAL ROLE fulkro_app_bypassrls."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    rows = (await db.execute(
        select(WhatsAppThread).where(
            WhatsAppThread.deleted_at.is_(None),
        ).order_by(WhatsAppThread.last_inbound_at.desc().nulls_last())
    )).scalars().all()
    return {
        "threads": [
            {
                "id": str(t.id),
                "project_id": str(t.project_id),
                "client_user_id": (
                    str(t.client_user_id) if t.client_user_id else None
                ),
                "status": t.status,
                "last_outbound_at": (
                    t.last_outbound_at.isoformat()
                    if t.last_outbound_at else None
                ),
                "last_inbound_at": (
                    t.last_inbound_at.isoformat()
                    if t.last_inbound_at else None
                ),
                "last_message_preview": t.last_message_preview,
                "messages_count": t.messages_count or 0,
            }
            for t in rows
        ]
    }


@admin_router.get("/threads/{thread_id}/messages")
async def admin_thread_messages(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    rows = (await db.execute(
        select(WhatsAppMessage).where(
            WhatsAppMessage.thread_id == thread_id,
            WhatsAppMessage.deleted_at.is_(None),
        ).order_by(WhatsAppMessage.sent_at.asc())
    )).scalars().all()
    return {
        "messages": [_serialize_message(m) for m in rows],
    }


class SendReplyBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


@admin_router.post("/threads/{thread_id}/send")
async def admin_send_reply(
    thread_id: uuid.UUID,
    body: SendReplyBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    thread = (await db.execute(
        select(WhatsAppThread).where(WhatsAppThread.id == thread_id)
    )).scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    svc = WhatsAppService()
    try:
        msg = await svc.send_outbound(
            db, thread=thread, body=body.content, sender_type="marcos",
        )
    except WhatsAppError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_message(msg)


# ─── Cliente portal router ──────────────────────────────────────────

portal_router = APIRouter(
    prefix="/client-portal/whatsapp",
    tags=["Portal Cliente - WhatsApp"],
)


@portal_router.get("/status")
async def portal_whatsapp_status(
    user: ClientUser = Depends(get_current_client_user),
) -> dict:
    return {
        "whatsapp_number": user.whatsapp_number,
        "verified": user.whatsapp_verified_at is not None,
        "opt_in_active": user.whatsapp_opt_in_at is not None,
        "verified_at": (
            user.whatsapp_verified_at.isoformat()
            if user.whatsapp_verified_at else None
        ),
        "opt_in_at": (
            user.whatsapp_opt_in_at.isoformat()
            if user.whatsapp_opt_in_at else None
        ),
    }


class VerifyPhoneBody(BaseModel):
    phone_raw: str = Field(..., min_length=6, max_length=30)


@portal_router.post("/verify-phone")
async def portal_verify_phone(
    body: VerifyPhoneBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = WhatsAppService()
    try:
        result = await svc.initiate_opt_in(
            db, client_user_id=user.id, phone_raw=body.phone_raw,
        )
    except WhatsAppError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return {
        "phone_e164": result.phone_e164,
        "otp_sent": result.otp_sent,
        "error": result.error,
    }


class VerifyOtpBody(BaseModel):
    otp: str = Field(..., min_length=4, max_length=12)


@portal_router.post("/verify-otp")
async def portal_verify_otp(
    body: VerifyOtpBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = WhatsAppService()
    ok = await svc.verify_otp(
        db, client_user_id=user.id, otp_input=body.otp,
    )
    if not ok:
        raise HTTPException(
            status_code=400, detail="OTP inválido o expirado",
        )
    await db.commit()
    return {"verified": True}


@portal_router.get("/thread")
async def portal_get_thread(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Resolve active project
    proj_row = (await db.execute(text(
        "SELECT id FROM projects WHERE client_id = :cid "
        "AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1"
    ), {"cid": str(user.client_id)})).first()
    if proj_row is None:
        raise HTTPException(status_code=404, detail="No active project")
    project_id = proj_row[0]
    await db.execute(text(
        "SELECT set_config('app.current_project_id', :v, true)"
    ), {"v": str(project_id)})
    thread = (await db.execute(
        select(WhatsAppThread).where(
            WhatsAppThread.project_id == project_id,
            WhatsAppThread.client_user_id == user.id,
            WhatsAppThread.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if thread is None:
        return {"thread": None}
    return {
        "thread": {
            "id": str(thread.id),
            "status": thread.status,
            "messages_count": thread.messages_count or 0,
            "last_inbound_at": (
                thread.last_inbound_at.isoformat()
                if thread.last_inbound_at else None
            ),
            "last_outbound_at": (
                thread.last_outbound_at.isoformat()
                if thread.last_outbound_at else None
            ),
        }
    }


@portal_router.get("/thread/messages")
async def portal_thread_messages(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    proj_row = (await db.execute(text(
        "SELECT id FROM projects WHERE client_id = :cid "
        "AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1"
    ), {"cid": str(user.client_id)})).first()
    if proj_row is None:
        return {"messages": []}
    await db.execute(text(
        "SELECT set_config('app.current_project_id', :v, true)"
    ), {"v": str(proj_row[0])})
    rows = (await db.execute(
        select(WhatsAppMessage).join(
            WhatsAppThread, WhatsAppThread.id == WhatsAppMessage.thread_id,
        ).where(
            WhatsAppThread.client_user_id == user.id,
            WhatsAppMessage.deleted_at.is_(None),
        ).order_by(WhatsAppMessage.sent_at.asc())
    )).scalars().all()
    return {"messages": [_serialize_message(m) for m in rows]}


@portal_router.get("/export")
async def portal_rgpd_export(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """RGPD art.15 · cliente exporta su histórico WhatsApp."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    svc = WhatsAppService()
    payload = await svc.export_rgpd_art15(db, user.id)
    return {
        "client_user_id": payload.client_user_id,
        "threads": [
            {
                "id": t.id, "project_id": t.project_id,
                "status": t.status,
                "messages_count": t.messages_count,
            }
            for t in payload.threads
        ],
        "messages": [
            {
                "id": m.id,
                "thread_id": m.thread_id,
                "direction": m.direction,
                "sender_type": m.sender_type,
                "content": m.content,
                "sent_at": m.sent_at,
            }
            for m in payload.messages
        ],
    }


# ─── Webhook (auth por token compartido · fail-closed si hay secret) ─────────

webhook_router = APIRouter(
    prefix="/webhooks/360dialog", tags=["webhooks - 360dialog"],
)


def _webhook_authorized(request: Request) -> bool:
    """Verifica el token del webhook (anti-spoofing de mensajes entrantes).

    Si ``dialog_360_webhook_secret`` está configurado, EXIGE un token coincidente
    (query ``?token=`` o header ``X-Webhook-Token``) en tiempo constante. Sin
    secret (dev/mock) devuelve True (verificación omitida).
    Configura la URL en 360dialog como
    ``https://<host>/api/v1/webhooks/360dialog?token=<secret>``.
    """
    try:
        secret = get_settings().dialog_360_webhook_secret.get_secret_value()
    except Exception:
        secret = ""
    if not secret:
        return True
    provided = (
        request.query_params.get("token")
        or request.headers.get("X-Webhook-Token", "")
    )
    return hmac.compare_digest(provided or "", secret)


@webhook_router.post("")
async def webhook_360dialog(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """360dialog webhook · inbound messages + delivery receipts (token-auth)."""
    if not _webhook_authorized(request):
        raise HTTPException(status_code=403, detail="invalid webhook token")
    payload = await request.json()
    client = get_default_client()
    event = client.parse_webhook(payload)
    if event.event_type == "inbound_message" and event.body and event.from_phone:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        svc = WhatsAppService(client=client)
        await svc.handle_inbound(
            db,
            from_phone=event.from_phone,
            body=event.body,
            whatsapp_message_id=event.whatsapp_message_id,
        )
        await db.commit()
        return {"handled": "inbound_message"}
    if event.event_type == "delivery_status" and event.whatsapp_message_id:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        from datetime import datetime, timezone
        msg = (await db.execute(
            select(WhatsAppMessage).where(
                WhatsAppMessage.whatsapp_message_id == event.whatsapp_message_id,
            )
        )).scalar_one_or_none()
        if msg is not None:
            now = datetime.now(timezone.utc)
            if event.delivery_status == "delivered":
                msg.delivered_at = now
            elif event.delivery_status == "read":
                msg.read_at = now
                if not msg.delivered_at:
                    msg.delivered_at = now
            elif event.delivery_status == "failed":
                msg.failed_at = now
            await db.commit()
        return {"handled": "delivery_status"}
    return {"handled": "unknown_or_skipped"}


# ─── Helpers ────────────────────────────────────────────────────────


def _serialize_message(m: WhatsAppMessage) -> dict:
    return {
        "id": str(m.id),
        "thread_id": str(m.thread_id),
        "direction": m.direction,
        "sender_type": m.sender_type,
        "content": m.content,
        "whatsapp_message_id": m.whatsapp_message_id,
        "sent_at": m.sent_at.isoformat() if m.sent_at else None,
        "delivered_at": (
            m.delivered_at.isoformat() if m.delivered_at else None
        ),
        "read_at": m.read_at.isoformat() if m.read_at else None,
        "failed_at": m.failed_at.isoformat() if m.failed_at else None,
        "failure_reason": m.failure_reason,
    }
