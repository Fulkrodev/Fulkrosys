"""M27 Conformity Lifecycle Paso 5 — endpoints API persistentes.

16 endpoints sobre las 13 tablas nuevas:

  POST /projects/{id}/conformity/initialize
  GET  /projects/{id}/conformity/status
  POST /projects/{id}/conformity/basic-declaration/submit
  POST /projects/{id}/conformity/enac-certification/prepare
  POST /projects/{id}/conformity/material-change/register
  GET  /projects/{id}/conformity/material-changes
  POST /projects/{id}/conformity/recategorize
  POST /projects/{id}/conformity/extraordinary-audit/schedule
  POST /projects/{id}/conformity/pce-overlay/apply
  GET  /projects/{id}/conformity/role-topology
  POST /projects/{id}/conformity/role-topology/generate
  POST /projects/{id}/conformity/renewal/trigger
  GET  /projects/{id}/conformity/submissions
  POST /projects/{id}/conformity/adapters/pilar/export-mgr
  POST /projects/{id}/conformity/adapters/ines/snapshot
  POST /projects/{id}/conformity/adapters/clara/ingest
"""
from __future__ import annotations

import base64
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.conformity_lifecycle import (
    ConformitySubmissionRow,
    MaterialChangeRow,
    RoleTopologyRow,
)

from backend.app.auth.dependencies import require_owner

from .adapters.clara_ingester import ingest_clara_output
from .adapters.ines_adapter import generate_ines_snapshot
from .adapters.pilar_adapter import generate_mgr_file
from .conformity_service_paso5 import (
    ConformityError,
    ConformityServicePaso5,
    MATERIALITY_QUESTIONS,
)


router = APIRouter(
    tags=["Motor 27 - Conformity Paso 5"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession) -> uuid.UUID:
    cid = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"),
        {"pid": str(project_id)},
    )).scalar()
    if not cid:
        raise HTTPException(404, "Project not found")
    cid_uuid = cid if isinstance(cid, uuid.UUID) else uuid.UUID(str(cid))
    await set_tenant_context(db, client_id=cid_uuid, project_id=project_id)
    return cid_uuid


# ══════════════════════════════════════════════════════════════════════
# Schemas
# ══════════════════════════════════════════════════════════════════════


class InitializeRouteBody(BaseModel):
    overlay_hints: list[str] = Field(default_factory=list)


class BasicDeclarationBody(BaseModel):
    responsible_person_name: str = Field(..., min_length=3, max_length=255)
    responsible_person_email: EmailStr
    published_url: str | None = None
    self_assessment_report_id: uuid.UUID | None = None


class EnacCertificationBody(BaseModel):
    auditor_entity: str = Field(..., min_length=3, max_length=200)
    dossier_run_id: uuid.UUID | None = None


class MaterialChangeBody(BaseModel):
    change_type: str
    description: str = Field(..., min_length=10)
    answers: dict[str, bool]
    detected_by: str = "marcos"


class RecategorizeBody(BaseModel):
    old_category: str
    new_category: str
    trigger_material_change_id: uuid.UUID | None = None
    approved_by: str | None = None


class ExtraordinaryAuditBody(BaseModel):
    scope_description: str
    performed_by: str | None = None


class ApplyOverlayBody(BaseModel):
    overlay_type: str
    assessment_report_id: uuid.UUID | None = None


class RoleTopologyBody(BaseModel):
    total_persons: int = Field(..., ge=1)
    roles_assigned: dict[str, Any]
    sector: str | None = None
    approved_by: str | None = None


class ClaraIngestBody(BaseModel):
    content_b64: str = Field(..., description="Base64 del XML/HTML CLARA")
    report_filename: str = "clara_report.xml"


# ══════════════════════════════════════════════════════════════════════
# Route + status
# ══════════════════════════════════════════════════════════════════════


@router.post(
    "/projects/{project_id}/conformity/initialize",
    status_code=status.HTTP_201_CREATED,
)
async def initialize(
    project_id: uuid.UUID,
    body: InitializeRouteBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    try:
        route = await ConformityServicePaso5().initialize_conformity_route(
            db, project_id, detected_overlay_hints=body.overlay_hints,
        )
    except ConformityError as exc:
        raise HTTPException(400, str(exc))
    await db.commit()
    return {
        "route_id": str(route.id),
        "route_type": route.route_type,
        "status": route.status,
        "expiration_date": (
            route.expiration_date.isoformat() if route.expiration_date else None
        ),
        "metadata": route.metadata_jsonb,
    }


@router.get("/projects/{project_id}/conformity/status")
async def conformity_status(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    return await ConformityServicePaso5().get_conformity_status(db, project_id)


# ══════════════════════════════════════════════════════════════════════
# Declaration + Certification
# ══════════════════════════════════════════════════════════════════════


@router.post(
    "/projects/{project_id}/conformity/basic-declaration/submit",
    status_code=status.HTTP_201_CREATED,
)
async def submit_basic_declaration(
    project_id: uuid.UUID,
    body: BasicDeclarationBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    try:
        decl = await ConformityServicePaso5().process_basic_declaration(
            db, project_id,
            responsible_person_name=body.responsible_person_name,
            responsible_person_email=str(body.responsible_person_email),
            published_url=body.published_url,
            self_assessment_report_id=body.self_assessment_report_id,
        )
    except ConformityError as exc:
        raise HTTPException(400, str(exc))
    await db.commit()
    return {
        "declaration_id": str(decl.id),
        "signed_hash": decl.signed_hash,
        "status": decl.status,
    }


@router.post("/projects/{project_id}/conformity/enac-certification/prepare")
async def prepare_enac(
    project_id: uuid.UUID,
    body: EnacCertificationBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    try:
        sub = await ConformityServicePaso5().prepare_enac_certification(
            db, project_id,
            auditor_entity=body.auditor_entity,
            dossier_run_id=body.dossier_run_id,
        )
    except ConformityError as exc:
        raise HTTPException(400, str(exc))
    await db.commit()
    return {
        "submission_id": str(sub.id),
        "status": sub.status,
        "auditor_entity": sub.external_system,
    }


# ══════════════════════════════════════════════════════════════════════
# Material changes + recategorization
# ══════════════════════════════════════════════════════════════════════


@router.post(
    "/projects/{project_id}/conformity/material-change/register",
    status_code=status.HTTP_201_CREATED,
)
async def register_material_change(
    project_id: uuid.UUID,
    body: MaterialChangeBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    try:
        mc = await ConformityServicePaso5().detect_material_change(
            db, project_id,
            change_type=body.change_type,
            description=body.description,
            answers=body.answers,
            detected_by=body.detected_by,
        )
    except ConformityError as exc:
        raise HTTPException(400, str(exc))
    await db.commit()
    return {
        "material_change_id": str(mc.id),
        "materiality_score": float(mc.materiality_score or 0.0),
        "is_material": mc.is_material,
        "triggered_extraordinary_audit": mc.triggered_extraordinary_audit,
        "extraordinary_audit_id": (
            str(mc.extraordinary_audit_id) if mc.extraordinary_audit_id else None
        ),
    }


@router.get("/projects/{project_id}/conformity/material-changes")
async def list_material_changes(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    res = await db.execute(
        select(MaterialChangeRow).where(
            MaterialChangeRow.project_id == project_id,
        ).order_by(MaterialChangeRow.detected_at.desc().nulls_last())
    )
    rows = list(res.scalars().all())
    return {
        "count": len(rows),
        "materiality_tree_questions": [
            {"key": k, "weight": w, "text": t}
            for k, w, t in MATERIALITY_QUESTIONS
        ],
        "items": [
            {
                "id": str(r.id),
                "change_type": r.change_type,
                "is_material": r.is_material,
                "materiality_score": float(r.materiality_score or 0.0),
                "description": r.description[:200],
                "detected_at": r.detected_at.isoformat() if r.detected_at else None,
            }
            for r in rows
        ],
    }


@router.post(
    "/projects/{project_id}/conformity/recategorize",
    status_code=status.HTTP_201_CREATED,
)
async def recategorize(
    project_id: uuid.UUID,
    body: RecategorizeBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    try:
        row = await ConformityServicePaso5().create_recategorization(
            db, project_id,
            old_category=body.old_category,
            new_category=body.new_category,
            trigger_material_change_id=body.trigger_material_change_id,
            approved_by=body.approved_by,
        )
    except ConformityError as exc:
        raise HTTPException(400, str(exc))
    await db.commit()
    return {
        "recategorization_id": str(row.id),
        "status": row.status,
        "old": row.old_category,
        "new": row.new_category,
    }


# ══════════════════════════════════════════════════════════════════════
# PCE overlay
# ══════════════════════════════════════════════════════════════════════


@router.post(
    "/projects/{project_id}/conformity/pce-overlay/apply",
    status_code=status.HTTP_201_CREATED,
)
async def apply_overlay(
    project_id: uuid.UUID,
    body: ApplyOverlayBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    try:
        row = await ConformityServicePaso5().apply_pce_overlay(
            db, project_id,
            overlay_type=body.overlay_type,
            assessment_report_id=body.assessment_report_id,
        )
    except ConformityError as exc:
        raise HTTPException(400, str(exc))
    measures = (row.extra_measures_jsonb or {}).get("measures", [])
    await db.commit()
    return {
        "overlay_id": str(row.id),
        "overlay_type": row.overlay_type,
        "overlay_spec_version": row.overlay_spec_version,
        "extra_measures_count": len(measures),
        "compliance_status": row.compliance_status,
    }


# ══════════════════════════════════════════════════════════════════════
# Role topology
# ══════════════════════════════════════════════════════════════════════


@router.post(
    "/projects/{project_id}/conformity/role-topology/generate",
    status_code=status.HTTP_201_CREATED,
)
async def generate_role_topology(
    project_id: uuid.UUID,
    body: RoleTopologyBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    topo = await ConformityServicePaso5().generate_role_topology(
        db, project_id,
        total_persons=body.total_persons,
        roles_assigned=body.roles_assigned,
        sector=body.sector,
        approved_by=body.approved_by,
    )
    await db.commit()
    return {
        "role_topology_id": str(topo.id),
        "pattern": topo.pattern,
        "total_persons": topo.total_persons,
        "exceptions_count": topo.exceptions_count,
    }


@router.get("/projects/{project_id}/conformity/role-topology")
async def get_role_topology(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    res = await db.execute(
        select(RoleTopologyRow).where(
            RoleTopologyRow.project_id == project_id,
        ).order_by(RoleTopologyRow.created_at.desc().nulls_last()).limit(1)
    )
    topo = res.scalar_one_or_none()
    if topo is None:
        raise HTTPException(404, "No role topology for this project")
    return {
        "role_topology_id": str(topo.id),
        "pattern": topo.pattern,
        "total_persons": topo.total_persons,
        "exceptions_count": topo.exceptions_count,
        "approved_at": topo.approved_at.isoformat() if topo.approved_at else None,
        "revision_date": topo.revision_date.isoformat() if topo.revision_date else None,
        "roles_assigned": topo.ens_roles_assigned_jsonb,
    }


# ══════════════════════════════════════════════════════════════════════
# Renewal campaign
# ══════════════════════════════════════════════════════════════════════


@router.post("/projects/{project_id}/conformity/renewal/trigger")
async def trigger_renewal(
    project_id: uuid.UUID,
    auto: bool = True,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    try:
        row = await ConformityServicePaso5().trigger_renewal_campaign(
            db, project_id, auto_triggered=auto,
        )
    except ConformityError as exc:
        raise HTTPException(400, str(exc))
    await db.commit()
    return {
        "campaign_id": str(row.id),
        "campaign_type": row.campaign_type,
        "scheduled_for": row.scheduled_for.isoformat() if row.scheduled_for else None,
        "status": row.status,
    }


# ══════════════════════════════════════════════════════════════════════
# Submissions list
# ══════════════════════════════════════════════════════════════════════


@router.get("/projects/{project_id}/conformity/submissions")
async def list_submissions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    res = await db.execute(
        select(ConformitySubmissionRow).where(
            ConformitySubmissionRow.project_id == project_id,
        ).order_by(ConformitySubmissionRow.submitted_at.desc().nulls_last())
    )
    rows = list(res.scalars().all())
    return {
        "count": len(rows),
        "items": [
            {
                "id": str(r.id),
                "submission_type": r.submission_type,
                "external_system": r.external_system,
                "status": r.status,
                "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
                "external_ref_id": r.external_ref_id,
            }
            for r in rows
        ],
    }


# ══════════════════════════════════════════════════════════════════════
# Adapters
# ══════════════════════════════════════════════════════════════════════


@router.post("/projects/{project_id}/conformity/adapters/pilar/export-mgr")
async def pilar_export_mgr(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    artifact = await generate_mgr_file(db, project_id)
    await db.commit()
    return {
        "tool": artifact["tool"],
        "artifact_path": artifact["artifact_path"],
        "artifact_hash": artifact["artifact_hash"],
        "content_b64": base64.b64encode(
            artifact["artifact_content"],
        ).decode("ascii"),
        "checklist": artifact["checklist"],
    }


@router.post("/projects/{project_id}/conformity/adapters/ines/snapshot")
async def ines_snapshot(
    project_id: uuid.UUID,
    year: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    artifact = await generate_ines_snapshot(db, project_id, year=year)
    # No incluir content_b64 en response HTTP por tamano; solo metadata
    await db.commit()
    return {
        "tool": artifact["tool"],
        "artifact_path": artifact["artifact_path"],
        "artifact_hash": artifact["artifact_hash"],
        "year": artifact["year"],
        "size_bytes": len(artifact["artifact_content"]),
        "sheets": artifact["sheets"],
        "checklist": artifact["checklist"],
    }


@router.post(
    "/projects/{project_id}/conformity/adapters/clara/ingest",
    status_code=status.HTTP_201_CREATED,
)
async def clara_ingest(
    project_id: uuid.UUID,
    body: ClaraIngestBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    try:
        content_bytes = base64.b64decode(body.content_b64)
    except Exception as exc:
        raise HTTPException(400, f"content_b64 invalido: {exc}")
    result = await ingest_clara_output(
        db, project_id,
        content=content_bytes,
        report_filename=body.report_filename,
    )
    await db.commit()
    return result
