"""Motor 7 -- Evidence API endpoints.

Provides evidence upload, listing, freshness checking, renewal,
and cryptographic verification endpoints.
"""
from __future__ import annotations

import contextvars
import uuid
from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_marcos_or_client, require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m07_evidence.catalog_loader import load_catalog
from backend.app.motors.m07_evidence.ingestion_service import ingest_evidence
from backend.app.motors.m07_evidence.ingestion_types import (
    IngestionRequest,
    IngestionError,
)
from backend.app.motors.m07_evidence.freshness_service import (
    check_freshness_for_project,
)
from backend.app.motors.m07_evidence.renewal_service import (
    create_renewal_request,
)
from backend.app.motors.m07_evidence.verification_service import (
    verify_evidence,
)

# Aislamiento cross-tenant (auditoría seguridad 2026-06-07 · paridad con m24):
# contextvar fijado por _capture_subject (router-level) para que _set_project_rls
# sepa quién llama y un ClientUser SOLO opere sobre SU proyecto.
_current_subject: contextvars.ContextVar = contextvars.ContextVar(
    "m07_current_subject", default=None,
)


async def _capture_subject(request: Request) -> None:
    """Router-level dep · stash el AuthSubject del request (request.state)."""
    _current_subject.set(getattr(request.state, "auth_subject", None))


router = APIRouter(
    tags=["Motor 7 - Evidence"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat C: cliente sube pruebas, Marcos
    # lista/modera. Ambos pools válidos · pero un ClientUser SOLO puede operar
    # sobre SU propio proyecto (enforce cross-tenant en _set_project_rls).
    dependencies=[
        Depends(require_marcos_or_client),
        Depends(_capture_subject),
    ],
)


# ── Response schemas ─────────────────────────────────────────────────


class UploadResponse(BaseModel):
    evidence_id: uuid.UUID
    hash_sha256: str
    firma_ed25519_hex: str
    fichero_path: str
    fecha_caducidad: date | None


class EvidenceListItem(BaseModel):
    id: uuid.UUID
    evidence_type_id: str | None
    nombre_tipo: str | None
    measure_code: str | None
    fichero_nombre_original: str | None
    fichero_mime_type: str | None
    fecha_evidencia: date | None
    fecha_caducidad: date | None
    vigente: bool
    hash_sha256: str | None


class EvidenceListResponse(BaseModel):
    total: int
    items: list[EvidenceListItem]


class FreshnessItemResponse(BaseModel):
    evidence_id: uuid.UUID
    measure_code: str | None
    fecha_caducidad: date | None
    estado: str
    dias_restantes: int | None


class FreshnessResponse(BaseModel):
    project_id: uuid.UUID
    total: int
    vigentes: int
    proxima_caducidad: int
    caducadas: int
    sin_caducidad: int
    items: list[FreshnessItemResponse]


class RenewalResponse(BaseModel):
    renewal_id: uuid.UUID | None
    evidence_id: uuid.UUID
    created: bool
    already_pending: bool
    motivo: str | None
    error: str | None = None


class VerificationResponse(BaseModel):
    evidence_id: uuid.UUID
    verdict: str
    hash_matches: bool | None = None
    signature_valid: bool | None = None
    detail: str | None = None


class EvidenceTypeOption(BaseModel):
    id: str
    label: str
    descripcion: str
    categoria: str
    allowed_mime: list[str]
    allowed_extensions: list[str]
    max_size_mb: int
    caducidad_dias: int | None = None
    medidas_asociadas: list[str]


class MeasureOption(BaseModel):
    codigo: str
    nombre: str
    familia: str | None = None


class UploadCatalogResponse(BaseModel):
    project_id: uuid.UUID
    categoria: str | None
    evidence_types: list[EvidenceTypeOption]
    measures: list[MeasureOption]


# ── Helpers ──────────────────────────────────────────────────────────


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    """Set RLS context for evidence table via project owner lookup."""
    client_id = (
        await db.execute(
            text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
        )
    ).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    # Aislamiento cross-tenant (#5 · paridad m24): si el caller es un ClientUser,
    # su client_id DEBE coincidir con el owner del proyecto de la URL. Antes el
    # RLS se fijaba al owner del project de la URL sin mirar quién llamaba → un
    # cliente del tenant A podía leer/subir evidencias del tenant B pasando el
    # project_id de B. 404 (no 403) para no revelar existencia cross-tenant.
    subject = _current_subject.get()
    if subject is not None and getattr(subject, "role_pool", None) == "cliente":
        caller_client_id = getattr(getattr(subject, "user", None), "client_id", None)
        if caller_client_id is None or str(caller_client_id) != str(client_id):
            raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


# ── 1. GET /evidence/public-key MOVIDO a public_router.py (H53 fix) ──
# Endpoint publico sin auth -- separado del router con dependencies=[
# require_marcos_or_client] router-level. Ver public_router.py.


# ── 2. POST /evidence/projects/{project_id}/upload ───────────────────


@router.post(
    "/evidence/projects/{project_id}/upload",
    response_model=UploadResponse,
)
async def upload_evidence(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    evidence_type_id: str = Form(...),
    measure_code: str = Form(...),
    obligation_id: uuid.UUID | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new evidence file (multipart)."""
    await _set_project_rls(project_id, db)

    file_bytes = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    file_name = file.filename or "unknown"

    # Magic-bytes: rechaza contenido suplantado antes de ingerir/escanear
    # (auditoría 2026-06-07 · complementa el AV clamd del pipeline m07).
    from pathlib import Path as _Path
    from backend.app.core.upload_validation import (
        MagicByteMismatch,
        validate_magic_bytes,
    )
    try:
        validate_magic_bytes(file_bytes, _Path(file_name).suffix)
    except MagicByteMismatch as exc:
        raise HTTPException(status_code=415, detail=str(exc))

    request = IngestionRequest(
        project_id=project_id,
        evidence_type_id=evidence_type_id,
        measure_code=measure_code,
        file_bytes=file_bytes,
        file_name=file_name,
        mime_type=mime_type,
        obligation_id=obligation_id,
    )

    try:
        outcome = await ingest_evidence(db, request)
    except IngestionError as e:
        raise HTTPException(status_code=422, detail=f"[{e.code}] {e.detail}")

    await db.commit()

    return UploadResponse(
        evidence_id=outcome.evidence_id,
        hash_sha256=outcome.hash_sha256,
        firma_ed25519_hex=outcome.firma_ed25519_hex,
        fichero_path=outcome.fichero_path,
        fecha_caducidad=outcome.fecha_caducidad,
    )


# ── 3. GET /evidence/projects/{project_id}/list ─────────────────────


@router.get(
    "/evidence/projects/{project_id}/list",
    response_model=EvidenceListResponse,
)
async def list_evidence(
    project_id: uuid.UUID,
    measure_code: str | None = Query(None),
    evidence_type_id: str | None = Query(None),
    vigente: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List evidence for a project with optional filters."""
    await _set_project_rls(project_id, db)

    clauses = ["project_id = :pid", "deleted_at IS NULL"]
    params: dict = {"pid": str(project_id)}

    if measure_code is not None:
        clauses.append("measure_code = :mc")
        params["mc"] = measure_code
    if evidence_type_id is not None:
        clauses.append("evidence_type_id = :etid")
        params["etid"] = evidence_type_id
    if vigente is not None:
        clauses.append("vigente = :vig")
        params["vig"] = vigente

    where = " AND ".join(clauses)
    result = await db.execute(
        text(
            f"SELECT id, evidence_type_id, nombre_tipo, measure_code, "
            f"fichero_nombre_original, fichero_mime_type, "
            f"fecha_evidencia, fecha_caducidad, vigente, hash_sha256 "
            f"FROM evidence WHERE {where} ORDER BY created_at DESC"
        ),
        params,
    )
    rows = result.fetchall()

    items = [
        EvidenceListItem(
            id=r[0],
            evidence_type_id=r[1],
            nombre_tipo=r[2],
            measure_code=r[3],
            fichero_nombre_original=r[4],
            fichero_mime_type=r[5],
            fecha_evidencia=r[6],
            fecha_caducidad=r[7],
            vigente=r[8],
            hash_sha256=r[9],
        )
        for r in rows
    ]
    return EvidenceListResponse(total=len(items), items=items)


# ── 4. GET /evidence/projects/{project_id}/expiring ──────────────────


@router.get(
    "/evidence/projects/{project_id}/expiring",
    response_model=FreshnessResponse,
)
async def get_expiring_evidence(
    project_id: uuid.UUID,
    warning_days: int = Query(30, ge=0, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Return freshness report for the project's evidence."""
    await _set_project_rls(project_id, db)

    report = await check_freshness_for_project(db, project_id, warning_days)

    return FreshnessResponse(
        project_id=report.project_id,
        total=report.total,
        vigentes=report.vigentes,
        proxima_caducidad=report.proxima_caducidad,
        caducadas=report.caducadas,
        sin_caducidad=report.sin_caducidad,
        items=[
            FreshnessItemResponse(
                evidence_id=i.evidence_id,
                measure_code=i.measure_code,
                fecha_caducidad=i.fecha_caducidad,
                estado=i.estado,
                dias_restantes=i.dias_restantes,
            )
            for i in report.items
        ],
    )


# ── 5. POST /evidence/projects/{project_id}/evidence/{evidence_id}/renew


@router.post(
    "/evidence/projects/{project_id}/evidence/{evidence_id}/renew",
    response_model=RenewalResponse,
)
async def renew_evidence(
    project_id: uuid.UUID,
    evidence_id: uuid.UUID,
    motivo: str | None = Query(None, max_length=80),
    db: AsyncSession = Depends(get_db),
):
    """Create a renewal request for an evidence item."""
    await _set_project_rls(project_id, db)

    outcome = await create_renewal_request(db, evidence_id, motivo)

    if outcome.error:
        raise HTTPException(status_code=404, detail=outcome.error)

    await db.commit()

    return RenewalResponse(
        renewal_id=outcome.renewal_id,
        evidence_id=evidence_id,
        created=outcome.created,
        already_pending=outcome.already_pending,
        motivo=outcome.motivo,
    )


# ── 6. GET /evidence/projects/{project_id}/evidence/{evidence_id}/verify


@router.get(
    "/evidence/projects/{project_id}/evidence/{evidence_id}/verify",
    response_model=VerificationResponse,
)
async def verify_evidence_endpoint(
    project_id: uuid.UUID,
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Verify cryptographic integrity of an evidence item."""
    await _set_project_rls(project_id, db)

    report = await verify_evidence(db, evidence_id)

    return VerificationResponse(
        evidence_id=report.evidence_id,
        verdict=report.verdict,
        hash_matches=report.hash_matches,
        signature_valid=report.signature_valid,
        detail=report.detail,
    )


# ── Admin-only catalog (powers the admin EvidenceVault upload form) ──
# Separate router: the upload/list endpoints accept both pools
# (require_marcos_or_client) so the cliente can aportar pruebas, but the
# admin upload FORM (file + evidence_type + measure selectors) is Marcos-only,
# hence require_owner. Returns the evidence_types catalog + the project's
# applicable ENS measures so the FE can populate both selectors.


admin_router = APIRouter(
    tags=["Motor 7 - Evidence (admin)"],
    dependencies=[Depends(require_owner)],
)


_CATEGORIA_COLUMN = {
    "BASICA": "aplica_basica",
    "MEDIA": "aplica_media",
    "ALTA": "aplica_alta",
}


@admin_router.get(
    "/evidence/projects/{project_id}/upload-catalog",
    response_model=UploadCatalogResponse,
)
async def get_upload_catalog(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Catalog of evidence types + applicable ENS measures for the admin form."""
    # Resolve project (existence + category). require_owner already gated auth.
    row = (
        await db.execute(
            text(
                "SELECT categoria_objetivo FROM projects "
                "WHERE id = :pid AND deleted_at IS NULL"
            ),
            {"pid": str(project_id)},
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    categoria = (row[0] or "").upper() or None

    catalog = load_catalog()
    evidence_types = [
        EvidenceTypeOption(
            id=t.id,
            label=t.nombre,
            descripcion=t.descripcion,
            categoria=t.categoria,
            allowed_mime=t.mime_types_permitidos,
            allowed_extensions=t.extensiones_permitidas,
            max_size_mb=t.tamano_max_mb,
            caducidad_dias=t.caducidad_dias,
            medidas_asociadas=t.medidas_asociadas,
        )
        for t in catalog.types
    ]

    # Applicable measures for the project's category. When the category is
    # unknown (project not yet categorized) we return the full set so the
    # admin is never blocked — ingestion validates the code on upload anyway.
    col = _CATEGORIA_COLUMN.get(categoria or "")
    if col:
        measure_rows = (
            await db.execute(
                text(
                    f"SELECT codigo, nombre, familia FROM ens_measures "
                    f"WHERE {col} IS TRUE ORDER BY codigo"
                )
            )
        ).fetchall()
    else:
        measure_rows = (
            await db.execute(
                text(
                    "SELECT codigo, nombre, familia FROM ens_measures "
                    "ORDER BY codigo"
                )
            )
        ).fetchall()
    measures = [
        MeasureOption(codigo=r[0], nombre=r[1], familia=r[2]) for r in measure_rows
    ]

    return UploadCatalogResponse(
        project_id=project_id,
        categoria=categoria,
        evidence_types=evidence_types,
        measures=measures,
    )
