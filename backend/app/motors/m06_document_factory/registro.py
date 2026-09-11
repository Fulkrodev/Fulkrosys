"""Registrar un documento ya generado · el medio paso que faltaba.

EL DEFECTO
    Seis productores documentales construyen su fichero en memoria y lo
    devuelven como ``Response`` sin dejar rastro:

        m02_magerit/api.py      informe E-028 (PDF y DOCX)
        m17_planning/api.py     plan de adecuacion E-150
        m27_conformity/api.py   declaracion de conformidad E-180/E-041
        m06_document_factory/api.py   manual SGSI E-160, plan director E-170

    Y los dos consumidores del expediente leen EXCLUSIVAMENTE la tabla
    ``documents``:

        m09_audit_prep/checklist_service.check_deliverables  -> lo que no este
            ahi sale `missing` con severidad `error` y bloquea el dossier
        m09_audit_prep/dossier_generator._collect_documents  -> sin filas, las
            carpetas del expediente salen con solo su `.keep`

    Es decir: el consultor genera el plan de adecuacion, se lo descarga, y el
    expediente sigue diciendo que no existe.

POR QUE NO VALE LLAMAR A generate_document
    ``DocumentFactoryService.generate_document`` RENDERIZA desde la plantilla
    DOCX del catalogo. Estos seis no renderizan plantillas: construyen el
    documento con python-docx a partir de datos del proyecto. Lo que les falta
    no es el render, es la mitad de atras -- huella, firma, fila, copia
    durable, registro de auditoria. Eso es lo que hay aqui, y es el MISMO
    codigo: ``generate_document`` tambien lo llama.

IDEMPOTENCIA
    Por (proyecto, codigo de plantilla). Son descargas: el consultor pulsa el
    boton N veces y sin esto ``documents`` se llena de duplicados y el
    checklist empieza a contar basura. Se actualiza la fila en sitio.

    Con una excepcion que no se negocia: si la fila existente ya esta FIRMADA
    (``client_signing_intent_id``) o APROBADA (``fecha_aprobacion``), no se
    toca. Se inserta una nueva. Sobrescribir un documento firmado seria borrar
    la prueba de lo que se firmo.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.documents import Document

_DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


async def registrar_documento_generado(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    template_codigo: str,
    nombre: str | None = None,
    docx_bytes: bytes | None = None,
    pdf_bytes: bytes | None = None,
    context: dict[str, Any] | None = None,
    generated_by: str | None = None,
    tipo: str | None = None,
) -> Document:
    """Deja constancia de un documento ya construido y devuelve su fila.

    Guarda los binarios donde la fabrica guarda los suyos, calcula la huella,
    firma, sube copia durable a MinIO y emite el registro de auditoria. Nada de
    esto interrumpe la descarga: la firma y MinIO son best-effort, igual que en
    ``generate_document``.
    """
    from backend.app.motors.m06_document_factory.service import (
        _DOCUMENTS_DIR,
        _emit_audit_log,
        DocumentEstado,
    )
    from backend.app.motors.m06_document_factory.signing import (
        SigningError,
        hash_sha256,
        sign_document,
    )

    if not docx_bytes and not pdf_bytes:
        raise ValueError("registrar_documento_generado sin bytes que registrar")

    ahora = datetime.now(timezone.utc)
    sello = ahora.strftime("%Y%m%d_%H%M%S")
    destino = _DOCUMENTS_DIR / str(project_id) / template_codigo
    destino.mkdir(parents=True, exist_ok=True)

    docx_path = pdf_path = None
    if docx_bytes:
        docx_path = destino / f"{template_codigo}_{sello}.docx"
        docx_path.write_bytes(docx_bytes)
    if pdf_bytes:
        pdf_path = destino / f"{template_codigo}_{sello}.pdf"
        pdf_path.write_bytes(pdf_bytes)

    # La huella es la del artefacto principal: el PDF si lo hay -- que es lo
    # que se entrega y se firma -- y si no, el DOCX.
    principal = pdf_path or docx_path
    assert principal is not None
    rendered_hash = hash_sha256(principal.read_bytes())
    signature_hex = None
    try:
        rendered_hash, signature_hex = sign_document(principal)
    except SigningError as exc:  # pragma: no cover — clave ausente en test env
        logger.warning("m06 registro · firma no disponible (no fatal): {}", exc)

    tpl = await _plantilla(db, template_codigo)
    fila = await _fila_reutilizable(db, project_id, template_codigo)

    if fila is None:
        fila = Document(
            project_id=project_id,
            template_codigo=template_codigo,
            plantilla_id=getattr(tpl, "id", None),
        )
        db.add(fila)

    fila.tipo = tipo or getattr(tpl, "categoria", None) or "entregable"
    fila.nombre = (
        nombre
        or (f"{tpl.codigo} - {tpl.nombre}" if tpl is not None else template_codigo)
    )
    fila.version_actual = getattr(tpl, "version_actual", None)
    fila.estado = DocumentEstado.GENERADO.value
    fila.docx_path = str(docx_path) if docx_path else None
    fila.pdf_path = str(pdf_path) if pdf_path else None
    fila.rendered_hash = rendered_hash
    fila.signature_ed25519 = signature_hex
    fila.context_snapshot = context
    fila.generated_by = generated_by
    fila.generated_at = ahora
    await db.flush()

    await _subir_copia_durable(db, fila, principal, sello, template_codigo)

    await _emit_audit_log(
        db,
        project_id=str(project_id),
        client_id=None,
        accion="document.generated",
        registro_id=str(fila.id),
        usuario=generated_by or "system",
        payload={
            "template_codigo": template_codigo,
            "nombre": fila.nombre,
            "rendered_hash": rendered_hash,
            "signed": bool(signature_hex),
            "via": "registro",
        },
    )
    return fila


async def _plantilla(db: AsyncSession, template_codigo: str):
    """La plantilla del catalogo, si la hay. No todos los codigos la tienen:
    el manual SGSI y el plan director se construyen con python-docx."""
    from backend.app.models.document_factory import Template

    try:
        return (await db.execute(
            select(Template).where(
                Template.codigo == template_codigo,
            ).limit(1)
        )).scalar_one_or_none()
    except Exception:  # pragma: no cover — catalogo ausente en entornos minimos
        logger.debug("m06 registro · catalogo no consultable", exc_info=True)
        return None


async def _fila_reutilizable(
    db: AsyncSession, project_id: uuid.UUID, template_codigo: str,
) -> Document | None:
    """La fila que se puede actualizar en sitio, o ``None`` si hay que crear.

    Una fila firmada o aprobada NO se reutiliza: sobrescribirla borraria la
    prueba de que bytes se firmaron.
    """
    return (await db.execute(
        select(Document).where(
            Document.project_id == project_id,
            Document.template_codigo == template_codigo,
            Document.deleted_at.is_(None),
            Document.client_signing_intent_id.is_(None),
            Document.fecha_aprobacion.is_(None),
        ).order_by(Document.generated_at.desc().nulls_last()).limit(1)
    )).scalar_one_or_none()


async def _subir_copia_durable(
    db: AsyncSession,
    fila: Document,
    principal: Path,
    sello: str,
    template_codigo: str,
) -> None:
    """Copia durable en MinIO · best-effort, igual que en la fabrica.

    Las rutas locales son efimeras: en produccion un reinicio del contenedor
    las borra y el cliente o el auditor recibian 503 sobre una ruta muerta.
    """
    try:
        from backend.app.core.storage.minio_client import (
            BUCKET_DOCUMENTS,
            put_object,
        )

        sufijo = principal.suffix
        clave = (
            f"fulkro/projects/{fila.project_id}/m06/"
            f"{(fila.rendered_hash or 'nohash')[:12]}_{template_codigo}_{sello}"
            f"{sufijo}"
        )
        put_object(
            BUCKET_DOCUMENTS,
            clave,
            principal.read_bytes(),
            "application/pdf" if sufijo == ".pdf" else _DOCX_MIME,
        )
        fila.storage_path = f"minio://{BUCKET_DOCUMENTS}/{clave}"
        await db.flush()
    except Exception as exc:  # noqa: BLE001 — copia durable best-effort
        logger.warning(
            "m06 registro · MinIO no disponible (no fatal) · doc={} · {}",
            fila.id, exc,
        )
