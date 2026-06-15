"""Endpoint PÚBLICO de firma de documento (``firma_documento``) vía magic-link.

El firmante (Responsable de la Información/Servicio, Dirección, RSEG…) firma SIN
cuenta: la PUERTA es el magic-link ``FIRMA_DOCUMENTO`` (OTP por canal aparte).

§3.1 audit-2026-06-15 · ANTES este flujo era un MOCK en el frontend
(``LegacyDocumentSignFlow`` · ``setTimeout`` → "Documento firmado") que NO
registraba NADA pese a prometer al firmante "tu firma Ed25519 quedó registrada".
Era el agujero más grave del ciclo: la firma del acta E-012 (categorización), del
informe MAGERIT E-028, de la DdA E-040 y de la conformidad —firmas legales ENS
de autoridades competentes (art. 11/40.2 RD 311/2022)— NUNCA se registraban.

Ahora, atómico (rollback total ante cualquier fallo):
  1. consume el magic-link (valida JWT EdDSA + OTP + caducidad + usos · audit log
     inmutable en ``client_interactions`` · ``MagicLinkService.consume_magic_link``),
  2. verifica purpose FIRMA_DOCUMENTO + resuelve el documento firmado del scope,
  3. registra la firma Ed25519 REAL sobre el hash congelado del snapshot del
     documento (``SigningService.sign_document_external`` · hash chain R6),
+ SSE best-effort post-commit (la firma YA quedó commiteada · NO se revierte).

Cada productor de magic-link FIRMA_DOCUMENTO (m01/m02/m03/m_meetings/m19/m27)
deja en el scope un discriminador ``document_type`` + el hash del snapshot
congelado; este endpoint los mapea al ``SignableType`` correspondiente.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.database import get_db
from backend.app.motors.m05_signing.service import SigningService
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkConsumeRequest
from backend.app.motors.m12_magic_link.service import (
    MagicLinkError,
    MagicLinkService,
)

logger = logging.getLogger(__name__)

public_router = APIRouter(
    prefix="/document-signing",
    tags=["Document signing (público · FIRMA_DOCUMENTO)"],
)


class SignDocumentBody(BaseModel):
    token: str = Field(..., min_length=10, description="JWT del magic-link")
    otp: str | None = Field(None, max_length=10)
    accepted: bool = Field(..., description="Conformidad explícita del firmante")


def _hash_scope(scope: dict) -> str:
    """SHA-256 determinista del scope (fallback cuando el productor no incluye un
    hash de snapshot explícito · liga la firma al contenido congelado del link)."""
    canonical = json.dumps(
        scope or {}, sort_keys=True, separators=(",", ":"),
        default=str, ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _as_uuid(value) -> _uuid.UUID | None:
    try:
        return _uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _resolve_document(
    scope: dict,
) -> tuple[str, str, _uuid.UUID | None, str | None, str]:
    """scope → (signable_type, label, signable_ref_id, signable_ref_type, doc_hash).

    Mapea el ``document_type`` del scope al ``SignableType`` del catálogo m05.
    Los productores genéricos (reunión K.6, cambio de fase, conformidad) caen a
    ``document_generic`` con el hash del snapshot si lo traen, o del scope."""
    scope = scope or {}
    dtype = scope.get("document_type")

    if dtype == "acta_e012":
        return (
            "acta_comite",
            "Acta de categorización (E-012)",
            _as_uuid(scope.get("categorization_id")),
            "categorization",
            scope.get("acta_snapshot_hash") or _hash_scope(scope),
        )
    if dtype == "informe_e028_magerit":
        return (
            "magerit_validation",
            "Informe de análisis MAGERIT (E-028)",
            _as_uuid(scope.get("analysis_id")),
            "magerit_analysis",
            scope.get("report_snapshot_hash") or _hash_scope(scope),
        )
    if dtype == "dda_e040_rseg":
        return (
            "dda",
            "Declaración de Aplicabilidad (DdA · E-040)",
            _as_uuid(scope.get("project_id")),
            "dda_project",
            scope.get("dda_snapshot_hash") or _hash_scope(scope),
        )

    # Genérico (k6 reunión, cambio de fase a implantación, conformidad…).
    label = (
        scope.get("title")
        or scope.get("doc_titulo")
        or scope.get("doc_codigo")
        or "Documento"
    )
    ref_id = _as_uuid(scope.get("meeting_id")) or _as_uuid(scope.get("document_id"))
    ref_type = (
        "minutes" if scope.get("meeting_id")
        else ("document" if scope.get("document_id") else None)
    )
    doc_hash = (
        scope.get("acta_snapshot_hash")
        or scope.get("report_snapshot_hash")
        or scope.get("dda_snapshot_hash")
        or scope.get("document_sha256")
        or _hash_scope(scope)
    )
    return ("document_generic", label, ref_id, ref_type, doc_hash)


@public_router.post("/sign")
async def sign_document(
    body: SignDocumentBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Firma un documento vía magic-link FIRMA_DOCUMENTO (consume + Ed25519 real)."""
    if not body.accepted:
        raise HTTPException(
            status_code=422,
            detail="Debes marcar la conformidad para firmar el documento.",
        )
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    # Lookup por token_hash bypasea la RLS project_isolation de magic_links
    # (igual que /consume y /minutes-signing/approve · el token ES la credencial).
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

    if ml.purpose != MagicLinkPurpose.FIRMA_DOCUMENTO:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Este enlace no corresponde a la firma de un documento.",
        )

    scope = ml.scope or {}
    sig_type, label, ref_id, ref_type, doc_hash = _resolve_document(scope)

    # Email del firmante: vive en la columna del link (NO en el scope).
    signer_email = (
        await db.execute(
            sa_text("SELECT recipient_email FROM magic_links WHERE id = :i"),
            {"i": str(ml.magic_link_id)},
        )
    ).scalar() or "desconocido@external"
    signer_name = scope.get("recipient_name")
    signer_role = scope.get("recipient_role") or scope.get("etapa_k")

    try:
        event = await SigningService(db).sign_document_external(
            project_id=ml.project_id,
            signable_type=sig_type,
            document_hash_sha256=doc_hash,
            signer_email=str(signer_email),
            signer_name=signer_name,
            signer_role=signer_role,
            signable_ref_id=ref_id,
            signable_ref_type=ref_type,
            magic_link_id=ml.magic_link_id,
            ip_address=ip,
            user_agent=ua,
            extras={"document_type": scope.get("document_type"), "label": label},
        )
    except Exception:
        await db.rollback()
        logger.exception("Error inesperado firmando documento · rollback total")
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar la firma del documento.",
        )
    await db.commit()

    # SSE best-effort post-commit (la firma YA quedó commiteada · NO se revierte).
    try:
        await sse_dispatcher.dispatch(
            channel=f"project:{ml.project_id}",
            event_type="signing.signed",
            data={
                "signable_type": sig_type,
                "signable_label": label,
                "signable_ref_id": str(ref_id) if ref_id else None,
                "signable_ref_type": ref_type,
                "primary_actor": "cliente",
                "project_id": str(ml.project_id),
                "event_hash": event.event_hash_sha256,
            },
        )
    except Exception:  # noqa: BLE001 · SSE best-effort · firma NO revertida
        logger.warning(
            "SSE signing.signed (documento) best-effort falló · project=%s",
            ml.project_id, exc_info=True,
        )

    return {
        "status": "signed",
        "document_type": scope.get("document_type"),
        "label": label,
        "event_hash": event.event_hash_sha256[:16],
    }
