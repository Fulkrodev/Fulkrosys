"""Endpoint PÚBLICO de aprobación/firma de acta (E-005) vía magic-link.

El asistente aprueba el acta SIN cuenta: la PUERTA es el magic-link
``APROBACION_ACTA`` (OTP). Router PÚBLICO (sin ``require_owner``): el token del
magic-link es la credencial.

Antes este flujo era un MOCK en el frontend (``LegacyDocumentSignFlow``) que NO
registraba nada (``setTimeout`` → "firmado"). Ahora:
  1. consume el magic-link (valida JWT/OTP/caducidad/usos · MagicLinkService),
  2. verifica purpose APROBACION_ACTA + minutes_id del scope,
  3. registra la firma REAL del asistente en ``committee_meetings.firmas`` vía
     ``MinutesService.register_signature`` (el MISMO registro que el endpoint
     admin ``/minutes/{id}/sign``),
todo atómico (rollback total ante cualquier fallo) + SSE best-effort post-commit.
"""
from __future__ import annotations

import logging
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.database import get_db
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkConsumeRequest
from backend.app.motors.m12_magic_link.service import (
    MagicLinkError,
    MagicLinkService,
)
from backend.app.motors.m18_communication.minutes_service import (
    MinutesError,
    MinutesService,
    MinutesStateError,
    MinutesValidationError,
)

logger = logging.getLogger(__name__)

public_router = APIRouter(
    prefix="/minutes-signing",
    tags=["Minutes signing (público · APROBACION_ACTA)"],
)


class ApproveActaBody(BaseModel):
    token: str = Field(..., min_length=10, description="JWT del magic-link")
    otp: str | None = Field(None, max_length=10)
    accepted: bool = Field(..., description="Conformidad explícita del asistente")


@public_router.post("/approve")
async def approve_acta(
    body: ApproveActaBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Aprueba/firma el acta vía magic-link APROBACION_ACTA (consume + registro)."""
    if not body.accepted:
        raise HTTPException(
            status_code=422,
            detail="Debes marcar la conformidad para aprobar el acta.",
        )
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    # Lookup por token_hash bypasea la RLS project_isolation de magic_links
    # (igual que el endpoint público /consume de m12). Token = credencial.
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    ml_service = MagicLinkService(db)
    try:
        ml = await ml_service.consume_magic_link(
            MagicLinkConsumeRequest(
                token=body.token, otp=body.otp, client_ip=ip, user_agent=ua,
            )
        )
    except MagicLinkError:
        await db.commit()  # persiste el posible otp_failures++ (igual que /consume)
        raise HTTPException(
            status_code=403,
            detail="Enlace inválido, caducado o código OTP incorrecto.",
        )

    if ml.purpose != MagicLinkPurpose.APROBACION_ACTA:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Este enlace no corresponde a la aprobación de un acta.",
        )
    minutes_id = (ml.scope or {}).get("minutes_id")
    if not minutes_id:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Enlace sin acta asociada.")

    try:
        m = await MinutesService(db).register_signature(
            _uuid.UUID(str(minutes_id)),
            magic_link_id=ml.magic_link_id,
            ip=ip,
            action_proof={"accepted": True, "via": "magic_link_public"},
        )
    except MinutesStateError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except MinutesValidationError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except MinutesError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        await db.rollback()
        logger.exception("Error inesperado aprobando acta · rollback total")
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar la aprobación del acta.",
        )
    await db.commit()

    # SSE best-effort post-commit (la firma YA quedó commiteada · NO se revierte).
    try:
        await sse_dispatcher.dispatch(
            channel=f"project:{m.project_id}",
            event_type="signing.signed",
            data={
                "signable_type": "acta",
                "signable_label": "Acta de reunión",
                "signable_ref_id": str(m.id),
                "signable_ref_type": "minutes",
                "primary_actor": "cliente",
                "project_id": str(m.project_id),
                "estado": m.estado,
            },
        )
    except Exception:  # noqa: BLE001 · SSE best-effort · firma NO revertida
        logger.warning(
            "SSE signing.signed (acta) best-effort falló · minutes=%s",
            m.id, exc_info=True,
        )

    return {
        "status": "approved",
        "minutes_id": str(m.id),
        "estado": m.estado,
        "codigo": getattr(m, "codigo", None),
    }
