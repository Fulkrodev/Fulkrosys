"""Motor 29 — Attachments service.

Gestiona presigned URLs MinIO upload + download para adjuntos de mensajes.

Flujo upload (cliente o admin):
  1. POST /messages/{id}/attachments con AttachmentUploadRequest
     (filename + mime_type + size_bytes).
  2. Service valida (MIME whitelist + size <= 10MB) y crea row
     ClientMessageAttachment con ``uploaded_at = NULL`` (placeholder).
  3. Service genera presigned PUT URL TTL 5 min al bucket
     ``fulkro-client-messages``.
  4. Cliente PUT directo al MinIO con el body file.
  5. POST /messages/{id}/attachments/{attachment_id}/complete
     verifica existencia object via HEAD MinIO + setea ``uploaded_at``.

Flujo download:
  1. GET /messages/{id}/attachments/{attachment_id}/download
  2. Service verifica que message es accesible al solicitante (RLS hace
     trabajo principal; helper service-side por mensaje claro).
  3. Genera presigned GET URL TTL ``signed_url_ttl_seconds`` (default 7d).

Lifecycle: tareas Celery limpian rows con ``uploaded_at + signed_url_ttl_seconds < now()``
(plan v4.2 6.15 — sub-fase 6.A.5).

Defensa profunda:
  - MIME re-check en service (además de CHECK BD + Pydantic schema).
  - Size re-check en service.
  - Post-upload HEAD MinIO verifica que el object realmente existe
    antes de marcar ``uploaded_at`` (defensa contra cliente que firma
    el upload pero no hace PUT real).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.storage.minio_client import get_minio_client
from backend.app.motors.m29_client_messaging.models import (
    ALLOWED_MIME_TYPES,
    DEFAULT_MINIO_BUCKET,
    DEFAULT_SIGNED_URL_TTL_SECONDS,
    MAX_ATTACHMENT_BYTES,
    ClientMessage,
    ClientMessageAttachment,
)
from backend.app.motors.m29_client_messaging.schemas import (
    AttachmentOut,
    AttachmentUploadRequest,
    AttachmentUploadResponse,
)


logger = logging.getLogger(__name__)


# Presigned upload URL TTL — corto (cliente debe completar upload pronto)
PRESIGNED_UPLOAD_TTL = timedelta(minutes=5)


# ====================================================================
# Excepciones
# ====================================================================


class AttachmentNotFoundError(Exception):
    """Attachment no encontrado por id (o soft-deleted)."""


class AttachmentValidationError(Exception):
    """MIME no whitelist o size > 10 MB (defensa profunda service-side)."""


class AttachmentUploadIncompleteError(Exception):
    """Cliente solicita download pero ``uploaded_at IS NULL`` — el PUT
    al MinIO no se completó."""


# ====================================================================
# Servicio
# ====================================================================


class AttachmentService:
    """Servicio attachments M29 (MinIO presigned URLs + lifecycle)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_upload(
        self,
        message_id: uuid.UUID,
        request: AttachmentUploadRequest,
    ) -> AttachmentUploadResponse:
        """Crea row attachment + presigned PUT URL.

        Validación profunda (Pydantic schema ya validó, pero re-check
        defense-in-depth en caso de bypass via API directa).
        """
        # Defensa profunda
        if request.mime_type not in ALLOWED_MIME_TYPES:
            raise AttachmentValidationError(
                f"MIME '{request.mime_type}' no permitido."
            )
        if request.size_bytes > MAX_ATTACHMENT_BYTES:
            raise AttachmentValidationError(
                f"size_bytes {request.size_bytes} excede 10 MB."
            )
        if request.size_bytes <= 0:
            raise AttachmentValidationError(
                f"size_bytes debe ser > 0 (recibido {request.size_bytes})."
            )

        # Validar mensaje existe + no deleted
        msg = await self.db.get(ClientMessage, message_id)
        if msg is None or msg.deleted_at is not None:
            from backend.app.motors.m29_client_messaging.service import (
                MessageNotFoundError,
            )
            raise MessageNotFoundError(
                f"Mensaje {message_id} no existe o eliminado."
            )

        # Generar object_key único: <message_id>/<attachment_uuid>/<filename>
        attachment_id = uuid.uuid4()
        object_key = (
            f"{message_id}/{attachment_id}/{_safe_filename(request.filename)}"
        )

        attachment = ClientMessageAttachment(
            id=attachment_id,
            message_id=message_id,
            filename=request.filename,
            mime_type=request.mime_type,
            size_bytes=request.size_bytes,
            minio_bucket=DEFAULT_MINIO_BUCKET,
            minio_object_key=object_key,
            signed_url_ttl_seconds=DEFAULT_SIGNED_URL_TTL_SECONDS,
            uploaded_at=None,  # placeholder hasta complete()
        )
        self.db.add(attachment)
        await self.db.flush()

        # Presigned PUT URL
        client = get_minio_client()
        upload_url = client.presigned_put_object(
            bucket_name=DEFAULT_MINIO_BUCKET,
            object_name=object_key,
            expires=PRESIGNED_UPLOAD_TTL,
        )

        return AttachmentUploadResponse(
            attachment_id=attachment_id,
            upload_url=upload_url,
            upload_method="PUT",
            upload_headers={"Content-Type": request.mime_type},
        )

    async def mark_upload_complete(
        self,
        message_id: uuid.UUID,
        attachment_id: uuid.UUID,
    ) -> AttachmentOut:
        """Verifica que el PUT al MinIO se completó (HEAD object) y setea
        ``uploaded_at = now()`` con defense-in-depth.

        Defensa: cliente firmó la URL pero podría NO haber hecho el PUT
        real, o el PUT pudo fallar parcialmente. HEAD verifica object
        existe antes de marcar uploaded.
        """
        attachment = await self.db.get(ClientMessageAttachment, attachment_id)
        # Binding anti-IDOR: el adjunto DEBE pertenecer al message_id de la ruta.
        # Sin esto, un cliente con un mensaje propio podia pedir el adjunto de
        # otro tenant (client_message_attachments no tiene client_id y el portal
        # corre con RLS desactivada). 404 para no filtrar existencia cross-tenant.
        if (
            attachment is None
            or attachment.deleted_at is not None
            or attachment.message_id != message_id
        ):
            raise AttachmentNotFoundError(
                f"Attachment {attachment_id} no existe."
            )

        # HEAD verify object existe en MinIO
        try:
            client = get_minio_client()
            stat = client.stat_object(
                bucket_name=attachment.minio_bucket,
                object_name=attachment.minio_object_key,
            )
        except Exception as exc:
            logger.warning(
                "Attachment %s: HEAD MinIO falló — upload incompleto: %s",
                attachment_id, exc,
            )
            raise AttachmentUploadIncompleteError(
                f"Object {attachment.minio_object_key} no encontrado en "
                f"MinIO (PUT incompleto o fallido)."
            ) from exc

        # Defensa: validar size_bytes coincide con lo declarado en
        # create_upload (cliente NO debe hacer upload de file mayor)
        if hasattr(stat, "size") and stat.size > attachment.size_bytes:
            logger.warning(
                "Attachment %s: size MinIO %d > declarado %d. Posible "
                "bypass cliente. Marcando como inválido.",
                attachment_id, stat.size, attachment.size_bytes,
            )
            raise AttachmentValidationError(
                f"Object MinIO size {stat.size} excede declared "
                f"{attachment.size_bytes}."
            )

        attachment.uploaded_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(attachment)

        return _to_attachment_out(attachment)

    async def get_download_url(
        self,
        message_id: uuid.UUID,
        attachment_id: uuid.UUID,
    ) -> AttachmentOut:
        """Genera presigned GET URL TTL ``signed_url_ttl_seconds``.

        Llamador (endpoint) ya validó acceso al mensaje vía RLS o
        owner check.
        """
        attachment = await self.db.get(ClientMessageAttachment, attachment_id)
        # Binding anti-IDOR: el adjunto DEBE pertenecer al message_id de la ruta.
        # Sin esto, un cliente con un mensaje propio podia pedir el adjunto de
        # otro tenant (client_message_attachments no tiene client_id y el portal
        # corre con RLS desactivada). 404 para no filtrar existencia cross-tenant.
        if (
            attachment is None
            or attachment.deleted_at is not None
            or attachment.message_id != message_id
        ):
            raise AttachmentNotFoundError(
                f"Attachment {attachment_id} no existe."
            )
        if attachment.uploaded_at is None:
            raise AttachmentUploadIncompleteError(
                f"Attachment {attachment_id} upload no completado "
                f"(uploaded_at IS NULL)."
            )

        return _to_attachment_out(attachment)

    async def soft_delete(
        self,
        attachment_id: uuid.UUID,
    ) -> None:
        """Soft-delete row + remove object MinIO best-effort (idempotente).

        El delete real del object MinIO sucede en Celery cleanup task
        (sub-fase 6.A.5) para no bloquear el endpoint.
        """
        attachment = await self.db.get(ClientMessageAttachment, attachment_id)
        if attachment is None or attachment.deleted_at is not None:
            return  # idempotente
        attachment.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()


# ====================================================================
# Helpers
# ====================================================================


def _safe_filename(filename: str) -> str:
    """Sanitiza filename para uso como minio_object_key.

    Reemplaza caracteres no-ASCII / no-safe con `_`. Preserva la
    extensión. Trunca a 200 chars.
    """
    import re
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    if len(safe) > 200:
        # Preservar extensión
        ext = ""
        if "." in safe[-10:]:
            ext = "." + safe.rsplit(".", 1)[1]
        safe = safe[: 200 - len(ext)] + ext
    return safe or "unnamed"


def _to_attachment_out(att: ClientMessageAttachment) -> AttachmentOut:
    """Convierte row a AttachmentOut + signed download URL si uploaded."""
    download_url: str | None = None
    if att.uploaded_at is not None:
        client = get_minio_client()
        download_url = client.presigned_get_object(
            bucket_name=att.minio_bucket,
            object_name=att.minio_object_key,
            expires=timedelta(seconds=att.signed_url_ttl_seconds),
        )
    return AttachmentOut(
        id=att.id,
        filename=att.filename,
        mime_type=att.mime_type,
        size_bytes=att.size_bytes,
        download_url=download_url,
        uploaded_at=att.uploaded_at,
    )
