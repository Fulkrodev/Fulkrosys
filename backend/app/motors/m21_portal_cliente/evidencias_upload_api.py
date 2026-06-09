"""Cliente evidencias upload endpoint (ADR-038 SAN-D MB-14.7).

POST /client-portal/evidencias/upload · multipart file + JSON metadata.
Cliente sube evidencias via portal (alternativa a magic-link
APORTE_EVIDENCIA · DEC-MB14-MAGIC-LINKS-MIGRATION ADR-038).

Storage: ``var/evidences/client_uploads/<project_id>/<uuid>.<ext>``.
Audit: AuditLogService.log_action EVIDENCE_UPLOAD hash chain.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m21_portal_cliente.audit_log_service import (
    AuditLogService,
)


_REPO_ROOT = Path(__file__).resolve().parents[4]
_UPLOADS_DIR = _REPO_ROOT / "var" / "evidences" / "client_uploads"

# 50 MB max upload (DEC-MB14-2FA-WEBAUTHN ADR-038: >100MB requeriría
# 2FA · simplificación scope MB-14 cap a 50MB sin extra friction).
_MAX_SIZE_BYTES = 50 * 1024 * 1024

_ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".png", ".jpg", ".jpeg",
    ".txt", ".csv", ".zip",
}


router = APIRouter(tags=["MB-14 - Client Evidencias Upload"])


@router.post("/client-portal/evidencias/upload")
async def upload_evidencia(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    related_measure: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> dict:
    """Cliente sube evidencia via portal · audit log hash chain."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    ext = Path(file.filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Extension {ext} not allowed. Allowed: {sorted(_ALLOWED_EXTENSIONS)}",
        )

    contents = await file.read()
    if len(contents) > _MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {_MAX_SIZE_BYTES // 1024 // 1024}MB)",
        )

    # Magic-bytes: la extensión está en whitelist pero el CONTENIDO podría estar
    # suplantado (p.ej. ejecutable renombrado a .pdf · auditoría 2026-06-07).
    from backend.app.core.upload_validation import (
        MagicByteMismatch,
        validate_magic_bytes,
    )
    try:
        validate_magic_bytes(contents, ext)
    except MagicByteMismatch as exc:
        raise HTTPException(status_code=415, detail=str(exc))

    # Resolve project_id activo cliente
    project_row = await db.execute(
        text(
            "SELECT id FROM projects WHERE client_id = :cid "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"cid": str(user.client_id)},
    )
    project_id = project_row.scalar_one_or_none()
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sin proyecto activo",
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(user.client_id)},
    )

    # Save file (durable · el volumen vardata:/app/var sobrevive reinicios · P0-1)
    upload_id = uuid.uuid4()
    project_dir = _UPLOADS_DIR / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    dest_path = project_dir / f"{upload_id}{ext}"
    dest_path.write_bytes(contents)
    relative_path = str(dest_path.relative_to(_REPO_ROOT))

    # FIX P2-2: materializar una fila Evidence. Antes el fichero quedaba HUÉRFANO
    # (disco + audit_log pero SIN fila) → invisible para el admin (lista/gap
    # matrix) y SIN escaneo antivirus. Ahora se crea la evidencia (firmada +
    # hash) con scan_status='scanning' por defecto y se encola el escaneo clamd
    # (que además archiva la copia WORM inmutable si pasa · P2-7).
    import hashlib
    from backend.app.motors.m07_evidence.signing import sign_payload

    file_hash = hashlib.sha256(contents).hexdigest()
    measure_id = None
    measure_code = None
    if related_measure:
        mhit = (await db.execute(
            text("SELECT id, codigo FROM ens_measures WHERE codigo = :c"),
            {"c": related_measure},
        )).first()
        if mhit is not None:
            measure_id, measure_code = mhit[0], mhit[1]
    ts_iso = datetime.now(timezone.utc).isoformat()
    signature = sign_payload(
        f"{file_hash}|{ts_iso}|{project_id}|portal_cliente".encode("utf-8")
    )
    await db.execute(
        text(
            "INSERT INTO evidence ("
            "id, project_id, measure_id, tipo, fuente, fichero_path, "
            "hash_sha256, fecha_evidencia, vigente, firma_ed25519, "
            "fichero_nombre_original, fichero_mime_type, fichero_tamano_bytes, "
            "measure_code, nombre_tipo, created_at"
            ") VALUES ("
            ":id, :pid, :mid, 'documento', 'portal_cliente_evidencias', :path, "
            ":hash, CURRENT_DATE, TRUE, :firma, "
            ":nombre, :mime, :size, :mcode, :tnombre, now()"
            ")"
        ),
        {
            "id": str(upload_id),
            "pid": str(project_id),
            "mid": str(measure_id) if measure_id else None,
            "path": relative_path,
            "hash": file_hash,
            "firma": signature.hex(),
            "nombre": file.filename,
            "mime": file.content_type or "application/octet-stream",
            "size": len(contents),
            "mcode": measure_code,
            "tnombre": (description or "Evidencia aportada por el cliente")[:255],
        },
    )

    # Audit log hash chain
    audit_service = AuditLogService(db)
    await audit_service.log_action(
        project_id=project_id,
        client_user_id=user.id,
        action_type="EVIDENCE_UPLOAD",
        action_data={
            "upload_id": str(upload_id),
            "evidence_id": str(upload_id),
            "filename_original": file.filename,
            "size_bytes": len(contents),
            "extension": ext,
            "description": description,
            "related_measure": related_measure,
            "stored_path": relative_path,
        },
        client_id=user.client_id,
    )
    # Auditoría 2026-06-07: get_db NO auto-commitea → commit explícito para
    # persistir el registro inmutable (R6) + la fila Evidence + encolar escaneo.
    await db.commit()

    # Encolar escaneo antivirus (best-effort · transiciona scan_status · archiva
    # WORM si pasa). Si Celery/clamd no están, la evidencia queda 'scanning'
    # visible y el gate de descarga (P1-2) la bloquea hasta que se valide.
    try:
        from backend.app.motors.m07_evidence.tasks import scan_evidence_file_task
        scan_evidence_file_task.delay(str(upload_id))
    except Exception:
        pass

    return {
        "upload_id": str(upload_id),
        "evidence_id": str(upload_id),
        "filename": file.filename,
        "size_bytes": len(contents),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "audit_logged": True,
    }
