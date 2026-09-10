"""M25 lifecycle - API publica /public/download/{token} (sin login).

Dispatcher por purpose para magic links de descarga. Patron coherente con
m08_verification/public_api.py: validacion peek-no-consume + audit log
per descarga + RLS bypass solo para lookup token.

3 purposes soportados:
- DESCARGA_BACKUP_ARCHIVO              · stream ZIP backup archivado (M25)
- DESCARGA_CERTIFICADO_CONFORMIDAD     · stub 501 hasta integracion M27
- DESCARGA_DOSSIER_FINAL               · stub 501 hasta integracion M09

Estado MB-4.A.4: backup completo (1 row BD activa), cert+dossier wired
en dispatcher con 501 explicito (0 rows BD · feature pre-cliente).
Reapertura cuando primer cliente certifique/cierre.

TODO-MB-4-CLEANUP-VALIDATE-PEEK-001: refactor `_validate_token_peek` +
`_log_portal_access` a `m12_magic_link/portal_validation.py` compartido
(actualmente duplicado entre m08 public_api y este modulo).
"""
from __future__ import annotations

import io
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, status as http_status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.operations import ClientInteraction, MagicLink
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.service import _hash_token, _verify_jwt
from backend.app.motors.m25_lifecycle.lifecycle_paso4 import (
    LifecyclePaso4Error,
    LifecyclePaso4Service,
    VALID_DECISIONS,
    VALID_RETAINER_TIERS,
    get_archived_backup,
)
from backend.app.motors.m23_retainer.paso2_extensions import get_tier_price
from pydantic import BaseModel, Field


router = APIRouter(prefix="/public", tags=["Public Download Portal (M25)"])


def _no_disponible_todavia(purpose: str, referencia_interna: str) -> HTTPException:
    """501 para una descarga aun no integrada, SIN filtrar el motivo interno.

    Hasta 2026-09-11 estos 501 devolvian el `detail` completo con el codigo de
    ticket dentro, y el portal de descarga —que ve el CLIENTE, sin login, con un
    magic link— lo pintaba tal cual. Quien recibia el enlace leia esto en su
    pantalla:

        «descarga_dossier_final pendiente de integracion M09 dossier_generator
         (TODO-FASE-9-MAGIC-LINK-DOSSIER-DOWNLOAD-001)»

    Lo encontro el recorrido automatico del bloque E: fue la UNICA aparicion de
    texto fabricado en las 167 paginas. Es la misma familia que el «[MOCK] Agent
    12» del bloque D: un artefacto interno que se escapa a la interfaz de alguien
    de fuera. Ademas de feo es informacion de arquitectura interna regalada a
    cualquiera que tenga un enlace.

    Ahora el motivo interno va al log, con el purpose, y el cliente recibe un
    mensaje que le dice lo unico que le sirve: que no es culpa suya y que no
    tiene que hacer nada (R29 · nada de jerga interna, nada de urgencia).
    """
    logger.warning(
        "descarga no integrada · purpose={} · {}", purpose, referencia_interna
    )
    return HTTPException(
        status_code=http_status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Este documento todavia no esta listo para descargar. "
            "No hace falta que hagas nada: te avisaremos en cuanto lo este."
        ),
    )


# ════════════════════════════════════════════════════════════════════
# Validation peek-no-consume + rate limiter (duplicado m08 · ver TODO)
# ════════════════════════════════════════════════════════════════════

_RATE_WINDOW_SECONDS = 60
_RATE_LIMIT = 20
_RATE_STATE: dict[str, deque[float]] = {}


def _check_rate_limit(token_hash: str, ip: str | None) -> None:
    key = f"{token_hash}:{ip or 'noip'}"
    now = datetime.now(timezone.utc).timestamp()
    bucket = _RATE_STATE.setdefault(key, deque())
    while bucket and now - bucket[0] > _RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit",
        )
    bucket.append(now)


@dataclass
class DownloadTokenContext:
    magic_link: MagicLink
    purpose: MagicLinkPurpose
    project_id: uuid.UUID
    scope: dict[str, Any]
    client_ip: str | None
    user_agent: str | None


DOWNLOAD_PURPOSES: set[MagicLinkPurpose] = {
    MagicLinkPurpose.DESCARGA_BACKUP_ARCHIVO,
    MagicLinkPurpose.DESCARGA_CERTIFICADO_CONFORMIDAD,
    MagicLinkPurpose.DESCARGA_DOSSIER_FINAL,
}

RETAINER_OFFER_PURPOSES: set[MagicLinkPurpose] = {
    MagicLinkPurpose.OFERTA_RETAINER,
    MagicLinkPurpose.RECONSIDERACION_RETAINER,
}


async def _validate_token_peek_for(
    token: str, request: Request, db: AsyncSession,
    *, allowed_purposes: set[MagicLinkPurpose],
) -> DownloadTokenContext:
    """Valida token sin consumir. Verifica purpose en allowed_purposes."""
    try:
        _verify_jwt(token)
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid token")

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    token_hash = _hash_token(token)

    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    result = await db.execute(
        select(MagicLink).where(
            MagicLink.token_hash == token_hash,
            MagicLink.deleted_at.is_(None),
        )
    )
    link = result.scalars().first()
    if not link:
        _check_rate_limit(token_hash, client_ip)
        raise HTTPException(status_code=403, detail="Invalid token")

    _check_rate_limit(token_hash, client_ip)

    try:
        purpose = MagicLinkPurpose(link.tipo_operacion)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid token")
    if purpose not in allowed_purposes:
        logger.warning(
            "Public token purpose mismatch: got {} expected one of {}",
            purpose, allowed_purposes,
        )
        raise HTTPException(status_code=403, detail="Invalid token")

    if link.revocado or link.revoked_at is not None:
        raise HTTPException(status_code=403, detail="Invalid token")
    now = datetime.now(timezone.utc)
    expira = link.expira_at
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    if now > expira:
        raise HTTPException(status_code=403, detail="Invalid token")
    max_usos = link.max_usos or 1
    if link.usos >= max_usos:
        raise HTTPException(status_code=403, detail="Invalid token")

    return DownloadTokenContext(
        magic_link=link, purpose=purpose,
        project_id=link.project_id, scope=link.scope or {},
        client_ip=client_ip, user_agent=user_agent,
    )


async def _log_download_access(
    db: AsyncSession, ctx: DownloadTokenContext, action: str,
    payload: dict[str, Any] | None = None,
) -> None:
    interaction = ClientInteraction(
        magic_link_id=ctx.magic_link.id,
        accion=action,
        ip=ctx.client_ip,
        user_agent=ctx.user_agent,
        timestamp=datetime.now(timezone.utc),
        payload=payload,
    )
    db.add(interaction)
    await db.flush()


# ════════════════════════════════════════════════════════════════════
# Endpoints publicos /public/download/{token}
# ════════════════════════════════════════════════════════════════════


@router.get("/download/{token}")
async def download_metadata(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
):
    """Metadata del recurso descargable (sin streaming bytes).

    Frontend llama este endpoint primero para mostrar nombre/tamano +
    boton "Descargar" que apunta a /public/download/{token}/file.
    """
    ctx = await _validate_token_peek_for(
        token, request, db, allowed_purposes=DOWNLOAD_PURPOSES,
    )
    await _log_download_access(db, ctx, "portal_download_metadata_view")
    await db.commit()

    if ctx.purpose == MagicLinkPurpose.DESCARGA_BACKUP_ARCHIVO:
        backup_id_raw = ctx.scope.get("archived_backup_id")
        if not backup_id_raw:
            raise HTTPException(
                status_code=500,
                detail="Magic link scope sin archived_backup_id",
            )
        backup = await get_archived_backup(db, uuid.UUID(str(backup_id_raw)))
        if backup is None or backup.deleted_at is not None:
            raise HTTPException(status_code=410, detail="Backup ya no disponible")
        if backup.expires_at and backup.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Backup expirado")
        return {
            "purpose": ctx.purpose.value,
            "filename": f"backup_{backup.id}.zip",
            "size_bytes": int(ctx.scope.get("zip_size_bytes") or 0) or None,
            "content_type": "application/zip",
            "sha256": backup.sha256_hash,
            "ed25519_signature": backup.ed25519_signature,
            "expires_at": backup.expires_at.isoformat() if backup.expires_at else None,
            "download_url": f"/api/v1/public/download/{token}/file",
        }

    if ctx.purpose == MagicLinkPurpose.DESCARGA_CERTIFICADO_CONFORMIDAD:
        # 0 rows BD · pre-cliente. Wiring real cuando primer certificado
        # ENS emitido. Scope esperado: {"certificate_id": str, "issued_at": str}.
        raise _no_disponible_todavia(
            ctx.purpose.value,
            "M27 storage backend · TODO-FASE-9-MAGIC-LINK-CERT-DOWNLOAD-001 · "
            "disparador: primer certificado ENS emitido en produccion",
        )

    if ctx.purpose == MagicLinkPurpose.DESCARGA_DOSSIER_FINAL:
        # 0 rows BD · pre-cliente. Reusar m09 dossier_generator + signed URL.
        raise _no_disponible_todavia(
            ctx.purpose.value,
            "M09 dossier_generator · TODO-FASE-9-MAGIC-LINK-DOSSIER-DOWNLOAD-001 · "
            "disparador: primer dossier de auditoria final generado en produccion",
        )

    raise HTTPException(status_code=403, detail="Invalid token")


@router.get("/download/{token}/file")
async def download_file(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream de bytes del recurso. Audit log per descarga."""
    ctx = await _validate_token_peek_for(
        token, request, db, allowed_purposes=DOWNLOAD_PURPOSES,
    )

    if ctx.purpose != MagicLinkPurpose.DESCARGA_BACKUP_ARCHIVO:
        # Cert + dossier todavia no implementados (ver download_metadata)
        raise HTTPException(
            status_code=http_status.HTTP_501_NOT_IMPLEMENTED,
            detail="Descarga aun no implementada para este purpose",
        )

    backup_id_raw = ctx.scope.get("archived_backup_id")
    if not backup_id_raw:
        raise HTTPException(
            status_code=500, detail="Magic link scope sin archived_backup_id",
        )
    backup = await get_archived_backup(db, uuid.UUID(str(backup_id_raw)))
    if backup is None or backup.deleted_at is not None:
        raise HTTPException(status_code=410, detail="Backup ya no disponible")
    if backup.expires_at and backup.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Backup expirado")

    zip_path = backup.zip_path
    if zip_path.startswith("minio://"):
        from backend.app.core.storage.minio_client import get_object
        rest = zip_path[len("minio://"):]
        bucket, _, key = rest.partition("/")
        try:
            zip_bytes = get_object(bucket, key)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"MinIO unreachable: {exc}")
    else:
        raise HTTPException(
            status_code=503,
            detail=(
                "ZIP no disponible en este entorno (local://). "
                "Verifique la configuracion de MinIO."
            ),
        )

    # Increment download counter + audit log (similar a download_archived_backup)
    await db.execute(
        sa_text(
            "UPDATE project_archived_backups "
            "SET downloaded_at = now(), "
            "download_count = COALESCE(download_count, 0) + 1 "
            "WHERE id = :bid"
        ),
        {"bid": str(backup.id)},
    )
    await _log_download_access(
        db, ctx, "portal_download_backup_streamed",
        {"archived_backup_id": str(backup.id), "size_bytes": len(zip_bytes)},
    )
    await db.commit()

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=backup_{backup.id}.zip",
            "X-Backup-SHA256": backup.sha256_hash,
            "X-Backup-Signature-Ed25519": backup.ed25519_signature,
        },
    )


# ════════════════════════════════════════════════════════════════════
# Retainer offer · OFERTA_RETAINER + RECONSIDERACION_RETAINER (A.5+6)
# ════════════════════════════════════════════════════════════════════


class RetainerOfferRespondBody(BaseModel):
    decision: str = Field(..., description="accept|decline|thinking")
    tier: str | None = Field(
        None, description="Required if decision==accept · uno de VALID_RETAINER_TIERS",
    )
    comentario: str | None = Field(None, max_length=2000)


@router.get("/retainer-offer/{token}")
async def retainer_offer_metadata(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
):
    """Metadata oferta retainer · purpose-aware (oferta vs reconsideracion).

    Devuelve scope (tiers recomendados, project name) + flag
    is_reconsideration para que el frontend muestre copy contextual.
    """
    ctx = await _validate_token_peek_for(
        token, request, db, allowed_purposes=RETAINER_OFFER_PURPOSES,
    )
    await _log_download_access(db, ctx, "portal_retainer_offer_view")
    await db.commit()

    is_reconsideration = ctx.purpose == MagicLinkPurpose.RECONSIDERACION_RETAINER

    return {
        "purpose": ctx.purpose.value,
        "is_reconsideration": is_reconsideration,
        "project_name": ctx.scope.get("project_name"),
        "recommended_tiers": ctx.scope.get(
            "recommended_tiers", list(VALID_RETAINER_TIERS),
        ),
        "previous_decline_reason": ctx.scope.get("previous_decline_reason")
        if is_reconsideration else None,
    }


@router.post("/retainer-offer/{token}/respond")
async def retainer_offer_respond(
    token: str, body: RetainerOfferRespondBody,
    request: Request, db: AsyncSession = Depends(get_db),
):
    """Cliente registra decision sobre la oferta retainer.

    Wrappea LifecyclePaso4Service.handle_retainer_decision con auth via
    magic link en lugar de session Marcos. Lookup precio_mensual desde
    pricing catalog (M23) cuando decision=accept.
    """
    ctx = await _validate_token_peek_for(
        token, request, db, allowed_purposes=RETAINER_OFFER_PURPOSES,
    )

    if body.decision not in VALID_DECISIONS:
        raise HTTPException(
            status_code=400,
            detail=f"decision invalida · validas: {VALID_DECISIONS}",
        )

    precio_mensual: float = 0.0
    if body.decision == "accept":
        if not body.tier or body.tier not in VALID_RETAINER_TIERS:
            raise HTTPException(
                status_code=400,
                detail=f"Para accept se requiere tier valido: {VALID_RETAINER_TIERS}",
            )
        catalog_price = await get_tier_price(db, body.tier)
        if catalog_price is None:
            raise HTTPException(
                status_code=500,
                detail=f"No se encontro precio para tier {body.tier} en pricing catalog",
            )
        precio_mensual = float(catalog_price)

    try:
        result = await LifecyclePaso4Service().handle_retainer_decision(
            db, ctx.project_id,
            decision=body.decision, tier=body.tier,
            precio_mensual=precio_mensual,
            performed_by="cliente",
        )
    except LifecyclePaso4Error as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Increment usos manualmente (peek no consume) + log access
    ctx.magic_link.usos += 1
    await _log_download_access(
        db, ctx, "portal_retainer_offer_response",
        {
            "decision": body.decision,
            "tier": body.tier,
            "comentario": body.comentario,
            "is_reconsideration":
                ctx.purpose == MagicLinkPurpose.RECONSIDERACION_RETAINER,
        },
    )
    await db.commit()

    return {
        "status": "recorded",
        "decision": body.decision,
        "tier": body.tier,
        "precio_mensual": precio_mensual,
        "result": result,
    }
