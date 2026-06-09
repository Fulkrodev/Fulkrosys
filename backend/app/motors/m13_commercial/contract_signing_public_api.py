"""Public magic-link contract signing confirm endpoint · #43.

El lead firma el contrato comercial SIN cuenta: la PUERTA es el magic-link
``FIRMA_CONTRATO`` (OTP + geo · decisión A) y la FIRMA es canvas Ed25519 (m05).
Router PÚBLICO (sin ``require_owner`` / ``require_client_user``): el token del
magic-link es la credencial. La firma promociona el proyecto ligero y crea el
ClientUser (#7) en la MISMA transacción atómica que la firma (refuerzo 1).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.database import get_db
from backend.app.motors.m13_commercial.services.contract_signing_flow import (
    ContractNotFoundError,
    ContractSigningFlow,
    ContractSigningFlowError,
)


logger = logging.getLogger(__name__)

public_router = APIRouter(
    prefix="/contract-signing",
    tags=["Contract signing (público · #43)"],
)


class ConfirmContractSignatureBody(BaseModel):
    token: str = Field(..., min_length=10)
    otp: str = Field(..., min_length=4, max_length=10)
    signature_canvas_dataurl: str = Field(..., min_length=20)
    signed_name: str = Field(..., min_length=1, max_length=120)
    signed_surname: str = Field(..., min_length=1, max_length=120)
    geo_lat: float | None = None
    geo_lon: float | None = None


@public_router.get("/preview")
async def preview_contract_document(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """#34 (FRENTE B) · el lead descarga/lee el DOCX EXACTO que va a firmar
    ANTES de firmar (cierra el "contrato mudo": hoy se firma sin ver el texto y
    el documento solo va por email). WYSIWYS: los bytes entregados tienen
    content_hash == documento_sha256 (lo que firma es lo que lee). El token del
    magic-link FIRMA_CONTRATO es la credencial · READ-ONLY · NO consume usos.
    """
    from io import BytesIO

    from fastapi.responses import StreamingResponse

    try:
        info = await ContractSigningFlow(db).get_contract_document_for_preview(
            token,
        )
    except (ContractSigningFlowError, ContractNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Error generando preview de contrato")
        raise HTTPException(
            status_code=500, detail="No se pudo recuperar el contrato",
        )
    return StreamingResponse(
        BytesIO(info["binary"]),
        media_type=info["media_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{info["filename"]}"',
            "X-Document-Sha256": info.get("documento_sha256") or "",
        },
    )


@public_router.post("/confirm")
async def confirm_contract_signature(
    body: ConfirmContractSignatureBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Confirma la firma del contrato vía canvas Ed25519 tras la puerta
    magic-link FIRMA_CONTRATO. Atómico: si algo falla, rollback TOTAL (incluida
    la promoción del proyecto + ClientUser · refuerzo 1)."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        result = await ContractSigningFlow(db).confirm_signing(
            token=body.token,
            otp=body.otp,
            signature_canvas_dataurl=body.signature_canvas_dataurl,
            signed_name=body.signed_name,
            signed_surname=body.signed_surname,
            ip_address=ip,
            user_agent=ua,
            geo_lat=body.geo_lat,
            geo_lon=body.geo_lon,
        )
    except (ContractSigningFlowError, ContractNotFoundError) as exc:
        # Atomicidad (refuerzo 1): un fallo deshace TAMBIÉN conversión #7.
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        # Atomicidad ROBUSTA (refuerzo 1): CUALQUIER fallo inesperado (DB, m05,
        # IDMS…) deshace TODA la transacción — incluida la promoción del proyecto
        # y el ClientUser — sin dejar commit parcial. NO depende de la limpieza
        # de get_db; el rollback es explícito aquí.
        await db.rollback()
        logger.exception(
            "Error inesperado firmando contrato · rollback total aplicado"
        )
        raise HTTPException(status_code=500, detail="Error al firmar el contrato")
    await db.commit()

    # Ola 3 #12 · cierra el sub-gap del "contrato mudo": el admin ve la firma
    # del contrato en realtime, como el resto de firmas (m05 endpoints).
    # POST-COMMIT + BEST-EFFORT REAL: la firma YA quedó commiteada · un fallo
    # del SSE JAMÁS la revierte (el SSE es notificación, no transacción).
    # Payload enriquecido: "{firmante} firmó Contrato comercial {C-001}".
    if result.get("status") == "signed":
        try:
            await sse_dispatcher.dispatch(
                channel=f"project:{result['project_id']}",
                event_type="signing.signed",
                data={
                    "intent_id": result["signing_intent_id"],
                    "signable_type": "contrato_comercial",
                    "signable_label": "Contrato comercial",
                    "signable_ref_id": result["contract_id"],
                    "signable_ref_type": "contract",
                    "contract_id": result["contract_id"],
                    "plantilla_id": result.get("plantilla_id"),
                    "signer_name": (
                        f"{body.signed_name} {body.signed_surname}".strip()
                    ),
                    "primary_actor": "cliente",
                    "project_id": result["project_id"],
                    "signed_at": result["signed_at"],
                    "event_hash_sha256": result["event_hash_sha256"],
                },
            )
        except Exception:  # noqa: BLE001 · SSE best-effort · firma NO revertida
            logger.warning(
                "SSE signing.signed (contrato) best-effort falló · contract=%s "
                "(firma NO revertida)",
                result.get("contract_id"),
                exc_info=True,
            )
    return result
