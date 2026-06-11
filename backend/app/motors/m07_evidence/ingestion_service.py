"""Evidence ingestion pipeline: validate, hash, sign, persist."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m07_evidence.catalog_loader import get_type_by_id
from backend.app.motors.m07_evidence.signing import sign_payload
from backend.app.motors.m07_evidence.ingestion_types import (
    IngestionRequest,
    IngestionOutcome,
    IngestionError,
)

# Evidence storage root: repo_root / var / evidences /
_REPO_ROOT = Path(__file__).resolve().parents[3].parent
_EVIDENCES_DIR = _REPO_ROOT / "var" / "evidences"


def _extension_from_name(file_name: str) -> str:
    """Extract lowercased file extension including the dot."""
    idx = file_name.rfind(".")
    if idx == -1:
        return ""
    return file_name[idx:].lower()


async def ingest_evidence(
    session: AsyncSession,
    request: IngestionRequest,
) -> IngestionOutcome:
    """Full ingestion pipeline for a single evidence file.

    Steps:
    1. Validate evidence_type_id exists in catalog
    2. Validate MIME type and file size
    3. Validate measure_code exists in ens_measures
    4. Calculate SHA-256 of file bytes
    5. Persist file to disk
    6. Build and sign payload with Ed25519
    7. Calculate expiry date
    8. Persist Evidence row
    9. Return IngestionOutcome
    """
    # 0. Reject empty files
    if len(request.file_bytes) == 0:
        raise IngestionError("EMPTY_FILE", "File is empty (0 bytes)")

    # 1. Validate evidence type
    ev_type = get_type_by_id(request.evidence_type_id)
    if ev_type is None:
        raise IngestionError(
            "UNKNOWN_TYPE",
            f"Evidence type '{request.evidence_type_id}' not found in catalog",
        )

    # 2. Validate MIME type
    if request.mime_type not in ev_type.mime_types_permitidos:
        raise IngestionError(
            "INVALID_MIME",
            f"MIME type '{request.mime_type}' not allowed for {ev_type.id}. "
            f"Allowed: {ev_type.mime_types_permitidos}",
        )

    # 2b. Validate file size
    max_bytes = ev_type.tamano_max_mb * 1024 * 1024
    if len(request.file_bytes) > max_bytes:
        raise IngestionError(
            "FILE_TOO_LARGE",
            f"File is {len(request.file_bytes)} bytes, max is {max_bytes} "
            f"({ev_type.tamano_max_mb} MB) for {ev_type.id}",
        )

    # 3. Validate measure_code exists in ens_measures
    result = await session.execute(
        text("SELECT id FROM ens_measures WHERE codigo = :code"),
        {"code": request.measure_code},
    )
    measure_row = result.fetchone()
    if measure_row is None:
        raise IngestionError(
            "UNKNOWN_MEASURE",
            f"Measure code '{request.measure_code}' not found in ens_measures",
        )
    measure_id = measure_row[0]

    # 4. Calculate SHA-256
    file_hash = hashlib.sha256(request.file_bytes).hexdigest()

    # 5. Persist file to disk
    evidence_id = uuid.uuid4()
    ext = _extension_from_name(request.file_name)
    project_dir = _EVIDENCES_DIR / str(request.project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    file_path = project_dir / f"{evidence_id}{ext}"
    file_path.write_bytes(request.file_bytes)

    # 6. Build signing payload and sign
    timestamp = datetime.now(timezone.utc).isoformat()
    payload_str = f"{file_hash}|{timestamp}|{request.project_id}|{request.evidence_type_id}"
    payload_bytes = payload_str.encode("utf-8")
    signature = sign_payload(payload_bytes)
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()

    # 7. Expiry date
    fecha_evidencia = request.fecha_evidencia or date.today()
    if ev_type.caducidad_dias is not None:
        fecha_caducidad = fecha_evidencia + timedelta(days=ev_type.caducidad_dias)
    else:
        fecha_caducidad = None

    # 7.bis · LECTURA IA del documento que sube el cliente.
    # Extrae el texto del fichero (PDF/Word/Excel/CSV/TXT · imagen y PDF
    # escaneado por OCR best-effort) y sugiere la clasificación ENS a partir del
    # CONTENIDO (no sólo del nombre). Best-effort: si falla, la evidencia se
    # guarda igual (sin lectura) · nunca rompe la subida.
    from .ai_classifier_service import suggest_classification
    from .content_extraction_service import extract_text

    extraction = extract_text(request.file_bytes, request.mime_type, request.file_name)
    suggestion = suggest_classification(
        request.file_name, content_preview=extraction.get("text") or None,
    )
    metadata_merged: dict = dict(request.metadata_extra or {})
    metadata_merged["lectura_ia"] = {
        "texto_extraido": (extraction["text"] or "")[:4000],
        "chars": extraction["chars"],
        "metodo": extraction["method"],
        "ocr_usado": extraction["ocr_used"],
        "ocr_disponible": extraction["ocr_available"],
        "clasificacion_sugerida": suggestion.to_dict(),
    }

    # 8. Persist Evidence row
    relative_path = f"var/evidences/{request.project_id}/{evidence_id}{ext}"

    await session.execute(
        text("""
            INSERT INTO evidence (
                id, project_id, measure_id, control_id,
                tipo, fuente, fichero_path, hash_sha256,
                fecha_evidencia, fecha_caducidad, vigente,
                firma_ed25519, metadata_extra,
                evidence_type_id, nombre_tipo,
                fichero_nombre_original, fichero_mime_type,
                fichero_tamano_bytes, firma_payload_sha256,
                measure_code, obligation_id,
                created_at
            ) VALUES (
                :id, :project_id, :measure_id, NULL,
                :tipo, :fuente, :fichero_path, :hash_sha256,
                :fecha_evidencia, :fecha_caducidad, TRUE,
                :firma_ed25519, :metadata_extra,
                :evidence_type_id, :nombre_tipo,
                :fichero_nombre_original, :fichero_mime_type,
                :fichero_tamano_bytes, :firma_payload_sha256,
                :measure_code, :obligation_id,
                now()
            )
        """),
        {
            "id": str(evidence_id),
            "project_id": str(request.project_id),
            "measure_id": str(measure_id),
            "tipo": ev_type.categoria,
            "fuente": "motor_m07",
            "fichero_path": relative_path,
            "hash_sha256": file_hash,
            "fecha_evidencia": fecha_evidencia,
            "fecha_caducidad": fecha_caducidad,
            "firma_ed25519": signature.hex(),
            "metadata_extra": json.dumps(metadata_merged) if metadata_merged else None,
            "evidence_type_id": request.evidence_type_id,
            "nombre_tipo": ev_type.nombre,
            "fichero_nombre_original": request.file_name,
            "fichero_mime_type": request.mime_type,
            "fichero_tamano_bytes": len(request.file_bytes),
            "firma_payload_sha256": payload_hash,
            "measure_code": request.measure_code,
            "obligation_id": str(request.obligation_id) if request.obligation_id else None,
        },
    )
    await session.flush()

    # 9. Queue async antivirus scan (MB-6 atom 6 · ENS mp.s.5 · Q3 B async Celery).
    # Evidence row inserted con scan_status='scanning' (server default migration).
    # Celery task transitions a clean / quarantined / error post-scan.
    # Best-effort enqueue: si Celery worker down · evidence persists con
    # scan_status='scanning' visible cliente · janitor task future-bis recupera.
    try:
        from backend.app.motors.m07_evidence.tasks import scan_evidence_file_task
        scan_evidence_file_task.delay(str(evidence_id))
    except Exception:
        # Celery stub or broker unreachable · evidence still persists.
        # Operationally: alert admin if scan_status stuck en 'scanning' >5min.
        pass

    # 10. Return outcome
    return IngestionOutcome(
        evidence_id=evidence_id,
        hash_sha256=file_hash,
        firma_ed25519_hex=signature.hex(),
        firma_payload_sha256=payload_hash,
        fichero_path=relative_path,
        fecha_caducidad=fecha_caducidad,
        evidence_type_id=request.evidence_type_id,
        nombre_tipo=ev_type.nombre,
    )
