"""Motor 28 — FastAPI router (8 endpoints, addendum §8.9).

Sub-fase 5.5.F.0.H refactor: in-memory dicts → DB-backed
(TODO-M28-CHANGE-GOVERNANCE-PERSISTENCE-001 + TODO-COMMIT-PATTERN-001).

Mapping (ADR-023 dominio compartido m27/m28):
  _CHANGES               → Change (operations.changes + metadata_jsonb extended)
  _RECATEGORIZATIONS     → m27.recategorizations cross-motor
  _EXTRAORDINARY_AUDITS  → m27.extraordinary_audits cross-motor
  _TOPOLOGIES            → change_topologies (ChangeTopologyRow nueva)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.models.change_governance import ChangeTopologyRow
from backend.app.models.conformity_lifecycle import (
    ExtraordinaryAuditRow,
    RecategorizationRow,
)
from backend.app.models.operations import Change
from backend.app.motors.m28_change_governance.extraordinary_audit_service import (
    open_extraordinary_audit,
)
from backend.app.motors.m28_change_governance.impact_assessor import assess_change
from backend.app.motors.m28_change_governance.recategorization_service import (
    recategorize_project,
)
from backend.app.motors.m28_change_governance.schemas import (
    ChangeAssessRequest,
    ChangeAssessmentOut,
    ChangeIntake,
    ExtraordinaryAuditCreate,
    ImpactDetailOut,
    RecategorizationCreate,
    TopologyOut,
    TopologyReviewRequest,
)
from backend.app.motors.m28_change_governance.topology_service import (
    get_pattern,
    recommend_pattern,
    requires_memo,
)


router = APIRouter(
    prefix="/api/v1/changes", tags=["Motor 28 - Change Governance"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _jsonable(value):
    """Convert UUIDs / datetimes to JSON-safe primitives recursively."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


async def _set_project_rls(
    project_id: uuid.UUID, db: AsyncSession,
) -> uuid.UUID | None:
    """Set RLS context for project-scoped m27 cross-motor tables.

    Las tablas m27.recategorizations y m27.extraordinary_audits que
    reusamos via ADR-023 tienen RLS project_isolation.
    """
    cid = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"),
        {"pid": str(project_id)},
    )).scalar()
    if not cid:
        return None
    cid_uuid = cid if isinstance(cid, uuid.UUID) else uuid.UUID(str(cid))
    await set_tenant_context(db, client_id=cid_uuid, project_id=project_id)
    return cid_uuid


# ════════════════════════════════════════════════════════════════════
# Changes
# ════════════════════════════════════════════════════════════════════


@router.post(
    "/projects/{project_id}/changes",
    status_code=status.HTTP_201_CREATED,
)
async def intake_change(
    project_id: uuid.UUID,
    body: ChangeIntake,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if await _set_project_rls(project_id, db) is None:
        raise HTTPException(404, "Project not found")

    metadata = {
        "state": "intake",
        "requested_by": body.requested_by,
        "proposed_date": (
            body.proposed_date.isoformat() if body.proposed_date else None
        ),
        "assessment": None,
    }

    row = Change(
        project_id=project_id,
        descripcion=body.description,
        solicitante=body.requested_by,
        metadata_jsonb=metadata,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    await db.commit()
    return {"change_id": str(row.id), "state": "intake"}


@router.post(
    "/projects/{project_id}/changes/{cid}/assess",
    response_model=ChangeAssessmentOut,
)
async def assess_change_endpoint(
    project_id: uuid.UUID,
    cid: uuid.UUID,
    body: ChangeAssessRequest,
    db: AsyncSession = Depends(get_db),
) -> ChangeAssessmentOut:
    if await _set_project_rls(project_id, db) is None:
        raise HTTPException(404, "Project not found")

    stmt = select(Change).where(
        Change.id == cid, Change.project_id == project_id,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, f"Change {cid} not found in project {project_id}")

    try:
        result = assess_change(
            project_id=project_id,
            change_description=row.descripcion or "",
            answers=body.answers,
            requested_by=row.solicitante or "marcos",
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    result["change_id"] = cid
    metadata = dict(row.metadata_jsonb or {})
    metadata["assessment"] = _jsonable(result)
    metadata["state"] = "assessed"
    row.metadata_jsonb = metadata
    await db.flush()

    # FASE C Phase A · materiality MATERIAL cascade hook (graceful)
    await _maybe_cascade_adenda_on_material(
        db=db,
        project_id=project_id,
        assessment_result=result,
    )

    await db.commit()
    return ChangeAssessmentOut(**result)


async def _maybe_cascade_adenda_on_material(
    db: AsyncSession,
    project_id: uuid.UUID,
    assessment_result: dict,
) -> None:
    """Graceful adenda cascade hook · NUNCA rompe assess endpoint.

    Mismo patrón _maybe_dispatch_notifications:
      - ImportError safe (M14 podría no estar disponible en tests)
      - Outer try/except logged warning solamente
    """
    import logging
    try:
        from backend.app.motors.m14_contracts.workflow_hooks import (
            maybe_dispatch_adenda_on_materiality_assessed,
        )
    except ImportError:
        logging.getLogger(__name__).warning(
            "m14_contracts.workflow_hooks unavailable · skip adenda cascade",
        )
        return

    try:
        await maybe_dispatch_adenda_on_materiality_assessed(
            db=db,
            project_id=project_id,
            assessment_result=assessment_result,
        )
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "materiality cascade adenda failed · project=%s err=%s",
            project_id, exc,
        )


@router.get("/projects/{project_id}/changes/open")
async def list_open_changes(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    await _set_project_rls(project_id, db)
    stmt = select(Change).where(Change.project_id == project_id)
    rows = list((await db.execute(stmt)).scalars())
    out = []
    for row in rows:
        meta = row.metadata_jsonb or {}
        if meta.get("state") == "closed":
            continue
        out.append({
            "change_id": str(row.id),
            "state": meta.get("state", "intake"),
            "description": (row.descripcion or "")[:200],
        })
    return out


# ════════════════════════════════════════════════════════════════════
# Recategorizations (cross-motor m27 — ADR-023)
# ════════════════════════════════════════════════════════════════════


@router.post(
    "/projects/{project_id}/recategorizations",
    status_code=status.HTTP_201_CREATED,
)
async def create_recategorization(
    project_id: uuid.UUID,
    body: RecategorizationCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if await _set_project_rls(project_id, db) is None:
        raise HTTPException(404, "Project not found")

    change_stmt = select(Change).where(
        Change.id == body.change_id, Change.project_id == project_id,
    )
    if (await db.execute(change_stmt)).scalar_one_or_none() is None:
        raise HTTPException(404, "Change not found in project")

    # C#55 · recat REAL: cambia categoria_objetivo + regenera borradores
    # (propuesta/plan/gap) con guards por nivel (N3 firmado / N2.5 en vuelo nunca
    # se tocan). Reutiliza floor_elevation_service (OPS-026).
    result = await recategorize_project(
        db, project_id, body.change_id, body.new_category, body.rationale,
    )

    rec_row = RecategorizationRow(
        id=result.recategorization_id,
        project_id=project_id,
        old_category=result.old_category or "BASICA",
        new_category=result.new_category,
        trigger_material_change_id=None,
        analysis_report_id=None,
        approved_at=None,
        approved_by=None,
        new_dda_id=None,
        status=result.state,  # applied | blocked_signed | blocked_in_flight
        created_at=datetime.now(timezone.utc),
    )
    db.add(rec_row)
    await db.flush()
    await db.commit()
    return {
        "recategorization_id": str(result.recategorization_id),
        "state": result.state,
        "level": result.level,
        "old_category": result.old_category,
        "new_category": result.new_category,
        "regenerated": result.regenerated,
        "documents_required": result.documents_required,
    }


# ════════════════════════════════════════════════════════════════════
# Extraordinary Audits (cross-motor m27 — ADR-023)
# ════════════════════════════════════════════════════════════════════


@router.post(
    "/projects/{project_id}/extraordinary-audits",
    status_code=status.HTTP_201_CREATED,
)
async def create_extraordinary_audit(
    project_id: uuid.UUID,
    body: ExtraordinaryAuditCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if await _set_project_rls(project_id, db) is None:
        raise HTTPException(404, "Project not found")

    change_stmt = select(Change).where(
        Change.id == body.change_id, Change.project_id == project_id,
    )
    if (await db.execute(change_stmt)).scalar_one_or_none() is None:
        raise HTTPException(404, "Change not found in project")

    audit_data = open_extraordinary_audit(
        project_id, body.change_id, body.rationale, body.target_date,
    )

    scheduled_for_dt: datetime | None = None
    if body.target_date:
        try:
            from datetime import date as _date
            target_d = _date.fromisoformat(body.target_date)
            scheduled_for_dt = datetime.combine(
                target_d, datetime.min.time(), timezone.utc,
            )
        except (TypeError, ValueError):
            scheduled_for_dt = None

    audit_row = ExtraordinaryAuditRow(
        id=audit_data["audit_id"],
        project_id=project_id,
        trigger_material_change_id=None,
        scope_description=body.rationale,
        scheduled_for=scheduled_for_dt,
        performed_by=None,
        performed_at=None,
        audit_report_id=None,
        findings_count=0,
        status="scheduled",
        created_at=datetime.now(timezone.utc),
    )
    db.add(audit_row)
    await db.flush()
    await db.commit()
    return {
        "audit_id": str(audit_data["audit_id"]),
        "state": audit_data["state"],
        "readiness_required": audit_data["readiness_required"],
    }


# ════════════════════════════════════════════════════════════════════
# Topology
# ════════════════════════════════════════════════════════════════════


@router.post(
    "/projects/{project_id}/roles/topology/review",
    response_model=TopologyOut,
)
async def review_topology(
    project_id: uuid.UUID,
    body: TopologyReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> TopologyOut:
    if await _set_project_rls(project_id, db) is None:
        raise HTTPException(404, "Project not found")

    pid = recommend_pattern(
        sector=body.sector,
        employees=body.employees,
        has_internal_it=body.has_internal_it,
        has_internal_ciso=body.has_internal_ciso,
        multi_site=body.multi_site,
        category=body.category,
    )
    detail = get_pattern(pid) or {}
    needs_memo = requires_memo(pid)

    stmt = (
        select(ChangeTopologyRow)
        .where(ChangeTopologyRow.project_id == project_id)
        .order_by(desc(ChangeTopologyRow.created_at))
        .limit(1)
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if existing is None:
        row = ChangeTopologyRow(
            project_id=project_id,
            pattern_id=pid,
            detail_jsonb=_jsonable(detail),
            requires_memo=needs_memo,
            created_at=now,
        )
        db.add(row)
    else:
        existing.pattern_id = pid
        existing.detail_jsonb = _jsonable(detail)
        existing.requires_memo = needs_memo
        existing.updated_at = now
    await db.flush()
    await db.commit()

    return TopologyOut(
        project_id=project_id,
        recommended_pattern=pid,
        pattern_detail=detail,
        requires_memo=needs_memo,
    )


@router.get("/projects/{project_id}/roles/topology", response_model=TopologyOut)
async def get_topology(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TopologyOut:
    await _set_project_rls(project_id, db)
    stmt = (
        select(ChangeTopologyRow)
        .where(ChangeTopologyRow.project_id == project_id)
        .order_by(desc(ChangeTopologyRow.created_at))
        .limit(1)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, f"No topology recorded for project {project_id}")
    return TopologyOut(
        project_id=project_id,
        recommended_pattern=row.pattern_id,
        pattern_detail=row.detail_jsonb or {},
        requires_memo=row.requires_memo,
    )


# ════════════════════════════════════════════════════════════════════
# Impact detail
# ════════════════════════════════════════════════════════════════════


@router.get(
    "/projects/{project_id}/changes/{cid}/impact",
    response_model=ImpactDetailOut,
)
async def get_impact(
    project_id: uuid.UUID,
    cid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ImpactDetailOut:
    await _set_project_rls(project_id, db)
    stmt = select(Change).where(
        Change.id == cid, Change.project_id == project_id,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, f"Change {cid} not found")
    metadata = row.metadata_jsonb or {}
    assessment = metadata.get("assessment")
    if not assessment:
        raise HTTPException(409, "Change not yet assessed")
    return ImpactDetailOut(
        change_id=cid,
        impact_vector=assessment["impact_vector"],
        materiality_level=assessment["materiality_level"],
        materiality_score=assessment["materiality_score"],
    )
