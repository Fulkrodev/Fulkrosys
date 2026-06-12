"""R26 · persistencia + adjunto del Distintivo de Conformidad (CCN-STIC 809).

Al alcanzar ``RouteState.REGISTERED`` se genera y persiste como ``Document``
descargable el DISTINTIVO de Conformidad con el ENS (CCN-STIC 809) que produce
FULKRO (autopublicable · nº + vigencia 2 años). La palabra «certificado» queda
RESERVADA al documento emitido por la entidad de certificación acreditada
(MEDIA/ALTA), que se persiste por separado vía el slot de adjunto
``external_cert_document_id`` y que FULKRO NUNCA genera.

Reusa ``distintivo_generator`` (DRY · OPS-026) + el patrón de persistencia MinIO
de M06. Idempotente por ``template_codigo = E-049``.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit_writer import emit_audit_log
from backend.app.models.conformity_lifecycle import ConformityRouteRow
from backend.app.models.documents import Document
from backend.app.motors.m27_conformity.distintivo_generator import (
    build_distintivo_context,
    generate_declaration_docx,
)
from backend.app.motors.m27_conformity.route_machine import (
    RouteState,
    RouteType,
    can_transition,
    transition,
)

DISTINTIVO_TEMPLATE_CODIGO = "E-049"
EXTERNAL_CERT_TEMPLATE_CODIGO = "E-049-EXT"
DISTINTIVO_DOC_NOMBRE = "Distintivo de Conformidad con el ENS (CCN-STIC 809)"
EXTERNAL_CERT_DOC_NOMBRE = (
    "Certificado de Conformidad ENS (Entidad de Certificación Acreditada)"
)
_DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

# Estados desde los que el distintivo es emitible (conformidad confirmada).
_ISSUABLE_FROM = {
    RouteState.CONFORMANT, RouteState.REGISTERED, RouteState.ACTIVE,
    RouteState.RENEWAL_DUE, RouteState.RENEWAL_PENDING,
}

_ROUTE_TYPE_FROM_DB = {
    "declaracion_basica": RouteType.DECLARATION,
    "certificacion_enac": RouteType.CERTIFICATION,
}


class DistintivoIssueError(ValueError):
    """Errores del flujo de emisión/adjunto del distintivo o del certificado."""


def _route_type(route: ConformityRouteRow) -> RouteType | None:
    return _ROUTE_TYPE_FROM_DB.get(route.route_type)


async def _latest_route(
    db: AsyncSession, project_id: uuid.UUID,
) -> ConformityRouteRow | None:
    return (await db.execute(
        select(ConformityRouteRow)
        .where(ConformityRouteRow.project_id == project_id)
        .order_by(ConformityRouteRow.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()


async def _existing_doc(
    db: AsyncSession, project_id: uuid.UUID, template_codigo: str,
) -> Document | None:
    return (await db.execute(
        select(Document).where(
            Document.project_id == project_id,
            Document.template_codigo == template_codigo,
            Document.deleted_at.is_(None),
        ).order_by(Document.created_at.desc()).limit(1)
    )).scalar_one_or_none()


async def _persist_minio(
    project_id: uuid.UUID, doc: Document, data: bytes, ext: str, mime: str,
    db: AsyncSession,
) -> None:
    """Copia durable en MinIO (best-effort · OPS-049 honest path)."""
    try:
        rh = (doc.rendered_hash or "nohash")[:12]
        object_key = (
            f"fulkro/projects/{project_id}/m27/{rh}_{doc.template_codigo}{ext}"
        )
        from backend.app.core.storage.minio_client import (
            BUCKET_DOCUMENTS,
            put_object,
        )
        put_object(BUCKET_DOCUMENTS, object_key, data, mime)
        doc.storage_path = f"minio://{BUCKET_DOCUMENTS}/{object_key}"
        await db.flush()
    except Exception as exc:  # noqa: BLE001 — copia durable best-effort
        logger.warning("m27 MinIO persist failed (non-fatal) · doc={} · {}", doc.id, exc)


async def _safe_audit(
    db: AsyncSession, *, accion: str, registro_id, project_id, payload: dict,
    usuario: str,
) -> None:
    try:
        await emit_audit_log(
            db, tabla="documents", registro_id=registro_id, accion=accion,
            project_id=project_id, payload_new=payload, usuario=usuario,
        )
    except Exception as exc:  # noqa: BLE001 — audit best-effort, nunca bloquea
        logger.warning("m27 audit_log emit failed (non-fatal): {}", exc)


async def issue_distintivo_document(
    db: AsyncSession, project_id: uuid.UUID, *, generated_by: str = "system",
) -> Document:
    """Genera y persiste el Document del distintivo (idempotente por E-049)."""
    existing = await _existing_doc(db, project_id, DISTINTIVO_TEMPLATE_CODIGO)
    if existing is not None:
        return existing

    ctx = await build_distintivo_context(db, project_id)
    data = generate_declaration_docx(ctx).getvalue()
    rendered_hash = hashlib.sha256(data).hexdigest()
    now = datetime.now(timezone.utc)

    doc = Document(
        project_id=project_id,
        tipo="distintivo_conformidad",
        nombre=f"{DISTINTIVO_TEMPLATE_CODIGO} - {DISTINTIVO_DOC_NOMBRE}",
        estado="generado",
        template_codigo=DISTINTIVO_TEMPLATE_CODIGO,
        clasificacion="conformidad",
        rendered_hash=rendered_hash,
        file_size_bytes=len(data),
        generated_by=generated_by,
        generated_at=now,
        context_snapshot={
            "cert_id": str(ctx.cert_id),
            "system_category": ctx.system_category,
            "expiry_date": ctx.expiry_date,
            "pct_conformidad": ctx.pct_conformidad,
            "norm": "CCN-STIC 809",
        },
    )
    db.add(doc)
    await db.flush()
    await _persist_minio(project_id, doc, data, ".docx", _DOCX_MIME, db)
    await _safe_audit(
        db, accion="conformity.distintivo.issued", registro_id=str(doc.id),
        project_id=str(project_id), usuario=generated_by,
        payload={"cert_id": str(ctx.cert_id), "template_codigo": DISTINTIVO_TEMPLATE_CODIGO},
    )
    return doc


async def attach_distintivo_on_registered(
    db: AsyncSession, project_id: uuid.UUID, *, generated_by: str = "system",
) -> dict:
    """Emite el distintivo y lo adjunta a la ruta (idempotente).

    Si la ruta está en CONFORMANT la transiciona a REGISTERED (CCN-STIC 809: el
    distintivo se publica una vez registrada la conformidad).
    """
    route = await _latest_route(db, project_id)
    if route is None:
        raise DistintivoIssueError(
            "No existe ruta de conformidad para el proyecto. Bloquea la ruta "
            "(lock_route) antes de emitir el distintivo."
        )
    cur = RouteState(route.status)
    if cur not in _ISSUABLE_FROM:
        raise DistintivoIssueError(
            f"El distintivo solo se emite con la conformidad confirmada (estado "
            f"actual: {cur.value}; requiere CONFORMANT o posterior)."
        )

    transitioned = False
    if cur == RouteState.CONFORMANT and can_transition(
        cur, RouteState.REGISTERED, _route_type(route)
    ):
        route.status = transition(
            cur, RouteState.REGISTERED, _route_type(route)
        ).value
        transitioned = True

    doc = await issue_distintivo_document(db, project_id, generated_by=generated_by)
    route.distintivo_document_id = doc.id
    await db.flush()
    return {
        "route_state": route.status,
        "transitioned_to_registered": transitioned,
        "distintivo_document_id": str(doc.id),
        "cert_id": (doc.context_snapshot or {}).get("cert_id"),
    }


async def attach_external_certificate(
    db: AsyncSession, project_id: uuid.UUID, *, filename: str, content: bytes,
    content_type: str | None, generated_by: str = "system",
) -> dict:
    """Adjunta el CERTIFICADO de la entidad de certificación acreditada (MEDIA/ALTA).

    FULKRO NUNCA emite este documento: es el certificado oficial de la entidad
    acreditada. Aquí solo se persiste como ``Document`` y se enlaza a la ruta.
    Solo válido para rutas de CERTIFICACIÓN (MEDIA/ALTA).
    """
    route = await _latest_route(db, project_id)
    if route is None:
        raise DistintivoIssueError(
            "No existe ruta de conformidad para el proyecto."
        )
    if _route_type(route) != RouteType.CERTIFICATION:
        raise DistintivoIssueError(
            "El certificado de entidad acreditada solo aplica a rutas de "
            "certificación (categorías MEDIA/ALTA). La categoría BÁSICA se cierra "
            "por autodeclaración (distintivo CCN-STIC 809)."
        )
    if not content:
        raise DistintivoIssueError("El fichero del certificado está vacío.")

    rendered_hash = hashlib.sha256(content).hexdigest()
    now = datetime.now(timezone.utc)
    ext = ".pdf"
    safe_name = (filename or "").lower()
    is_pdf = (content_type or "").lower() == "application/pdf" or safe_name.endswith(".pdf")
    if not (is_pdf and content[:5] == b"%PDF-"):
        raise DistintivoIssueError(
            "El certificado debe ser un PDF válido emitido por la entidad acreditada."
        )

    doc = Document(
        project_id=project_id,
        tipo="certificado_externo",
        nombre=f"{EXTERNAL_CERT_TEMPLATE_CODIGO} - {EXTERNAL_CERT_DOC_NOMBRE}",
        estado="aprobado",
        template_codigo=EXTERNAL_CERT_TEMPLATE_CODIGO,
        clasificacion="certificado",
        rendered_hash=rendered_hash,
        file_size_bytes=len(content),
        generated_by=generated_by,
        generated_at=now,
        context_snapshot={
            "origen": "entidad_certificacion_acreditada",
            "filename_original": filename,
        },
    )
    db.add(doc)
    await db.flush()
    await _persist_minio(project_id, doc, content, ext, "application/pdf", db)
    route.external_cert_document_id = doc.id
    await db.flush()
    await _safe_audit(
        db, accion="conformity.external_certificate.attached",
        registro_id=str(doc.id), project_id=str(project_id), usuario=generated_by,
        payload={"template_codigo": EXTERNAL_CERT_TEMPLATE_CODIGO, "sha256": rendered_hash},
    )
    return {
        "external_cert_document_id": str(doc.id),
        "sha256": rendered_hash,
        "file_size_bytes": len(content),
    }


def _parse_minio(storage_path: str | None) -> tuple[str, str] | None:
    if not storage_path or not storage_path.startswith("minio://"):
        return None
    bucket, _, key = storage_path[len("minio://"):].partition("/")
    if not bucket or not key:
        return None
    return bucket, key


async def read_distintivo_bytes(
    db: AsyncSession, project_id: uuid.UUID,
) -> tuple[bytes, str]:
    """Devuelve (bytes, filename) del distintivo. Regenera si MinIO no responde."""
    route = await _latest_route(db, project_id)
    doc: Document | None = None
    if route is not None and route.distintivo_document_id is not None:
        doc = await db.get(Document, route.distintivo_document_id)
    if doc is None:
        doc = await _existing_doc(db, project_id, DISTINTIVO_TEMPLATE_CODIGO)

    if doc is not None:
        cert8 = str((doc.context_snapshot or {}).get("cert_id", ""))[:8] or "doc"
        parsed = _parse_minio(doc.storage_path)
        if parsed:
            try:
                from backend.app.core.storage.minio_client import get_object
                return get_object(*parsed), f"Distintivo_Conformidad_ENS_{cert8}.docx"
            except Exception as exc:  # noqa: BLE001 — fallback regen
                logger.warning("m27 distintivo MinIO read failed, regenerating: {}", exc)

    # Fallback determinista: regenerar on-the-fly (nunca 503).
    ctx = await build_distintivo_context(db, project_id)
    data = generate_declaration_docx(ctx).getvalue()
    return data, f"Distintivo_Conformidad_ENS_{str(ctx.cert_id)[:8]}.docx"


async def read_external_certificate_bytes(
    db: AsyncSession, project_id: uuid.UUID,
) -> tuple[bytes, str] | None:
    """Devuelve (bytes, filename) del certificado externo, o None si no adjunto."""
    route = await _latest_route(db, project_id)
    if route is None or route.external_cert_document_id is None:
        return None
    doc = await db.get(Document, route.external_cert_document_id)
    if doc is None:
        return None
    parsed = _parse_minio(doc.storage_path)
    if not parsed:
        return None
    try:
        from backend.app.core.storage.minio_client import get_object
        return get_object(*parsed), "Certificado_Conformidad_ENS_acreditada.pdf"
    except Exception as exc:  # noqa: BLE001
        logger.warning("m27 external cert MinIO read failed: {}", exc)
        return None
