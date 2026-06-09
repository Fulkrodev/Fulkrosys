"""Motor 27 — FastAPI router (15 endpoints, addendum §7.11).

Sub-fase 5.5.F.0.G refactor: in-memory dicts → DB-backed reusando
13 tablas ``conformity_lifecycle`` existing pre-S11 + tabla nueva
polimórfica ``conformity_state_snapshots`` para route history y
external exports (TODO-COMMIT-PATTERN-001 + TODO-M27-STATE-MACHINE-PERSISTENCE-001).

Mapping:
  _PROJECT_ROUTES   → ConformityRouteRow (status=RouteState.value)
  _PROJECT_OVERLAYS → PceOverlayRow (futura: ahora compute-only en api.py)
  _SUBMISSIONS      → ConformitySubmissionRow
  _RENEWALS         → RenewalCampaignRow
  _DECLARATIONS     → BasicDeclarationRow
  _ROUTE_HISTORY    → ConformityStateSnapshotRow(snapshot_type='route_transition')
  _EXPORTS          → ConformityStateSnapshotRow(snapshot_type='external_export')

Pattern uniform commit() coherente con 5.5.F.0.B/C/D batch.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import text as sa_text

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.models.conformity_lifecycle import (
    BasicDeclarationRow,
    ConformityRouteRow,
    ConformityStateSnapshotRow,
    ConformitySubmissionRow,
    PceOverlayRow,
    RenewalCampaignRow,
)
from backend.app.motors.m27_conformity import service
from backend.app.motors.m27_conformity.adapters import (
    ines_adapter,
    lucia_adapter,
    pilar_adapter,
    registry_adapter,
)
from backend.app.motors.m27_conformity.route_machine import (
    InvalidRouteTransitionError,
    RouteState,
    RouteType,
    can_transition,
    transition,
)
from backend.app.motors.m27_conformity.schemas import (
    ConformityRouteOut,
    ConformityStatus,
    DeclarationGenerateRequest,
    DeclarationOut,
    ExternalExportCreate,
    ExternalExportOut,
    PceOverlayOut,
    RenewalCampaignOut,
    RouteLockRequest,
    SubmissionCreate,
    SubmissionOut,
    SubmissionProofUpload,
)
from backend.app.motors.m27_conformity.submission_machine import SubmissionState


router = APIRouter(
    prefix="/api/v1/conformity", tags=["Motor 27 - Conformity"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


# Mapping RouteType enum (api.py business) → CHECK constraint values
# en migración pre-S11 e3f7a5b2d412 (declaracion_basica/certificacion_enac).
_ROUTE_TYPE_TO_DB = {
    RouteType.DECLARATION.value: "declaracion_basica",
    RouteType.CERTIFICATION.value: "certificacion_enac",
}
_ROUTE_TYPE_FROM_DB = {v: k for k, v in _ROUTE_TYPE_TO_DB.items()}


def _route_type_to_db(rt: RouteType) -> str:
    return _ROUTE_TYPE_TO_DB[rt.value]


def _route_type_from_db(db_value: str) -> RouteType:
    return RouteType(_ROUTE_TYPE_FROM_DB.get(db_value, db_value))


# Mapping target API (6 valores en SubmissionCreate) → CHECK constraint
# valores migración (basic_declaration/enac_dossier/renewal/overlay_assessment).
# Preservamos el target API original en metadata_jsonb["target_api"] para
# round-trip en serialización.
_TARGET_API_TO_DB = {
    "AUDITOR": "enac_dossier",
    "REGISTRO": "basic_declaration",
    "AAPP": "renewal",
    "PILAR": "overlay_assessment",
    "LUCIA": "overlay_assessment",
    "INES": "overlay_assessment",
}


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _set_project_rls(
    project_id: uuid.UUID, db: AsyncSession,
) -> uuid.UUID | None:
    """Set RLS tenant context for project-scoped tables.

    Las tablas conformity_lifecycle (pre-S11) tienen policy
    ``project_isolation`` USING ``project_id = current_project_id()``.
    Sin set_config previo, los INSERT fallan con
    InsufficientPrivilegeError.

    Devuelve el client_id propietario o None si proyecto no existe.
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


async def _get_route_row(
    db: AsyncSession, project_id: uuid.UUID,
) -> ConformityRouteRow | None:
    stmt = (
        select(ConformityRouteRow)
        .where(ConformityRouteRow.project_id == project_id)
        .order_by(desc(ConformityRouteRow.created_at))
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


def _route_to_out(row: ConformityRouteRow) -> ConformityRouteOut:
    metadata = dict(row.metadata_jsonb or {})
    next_review_str = metadata.get("next_review_due")
    next_review = (
        date.fromisoformat(next_review_str) if next_review_str else None
    )
    return ConformityRouteOut(
        project_id=row.project_id,
        route_type=_route_type_from_db(row.route_type),
        state=RouteState(row.status),
        category=metadata.get("category", ""),
        overlay_code=metadata.get("overlay_code"),
        locked_at=row.initiated_at,
        next_review_due=next_review,
    )


async def _record_history(
    db: AsyncSession,
    project_id: uuid.UUID,
    prev: str,
    new: str,
    reason: str,
) -> None:
    now = datetime.now(timezone.utc)
    snap = ConformityStateSnapshotRow(
        project_id=project_id,
        snapshot_type="route_transition",
        metadata_jsonb={
            "from": prev, "to": new, "reason": reason,
            "at": now.isoformat(),
        },
        created_at=now,
    )
    db.add(snap)
    await db.flush()


# ════════════════════════════════════════════════════════════════════
# Route
# ════════════════════════════════════════════════════════════════════


@router.post("/projects/{project_id}/route/lock", response_model=ConformityRouteOut)
async def lock_route(
    project_id: uuid.UUID,
    body: RouteLockRequest,
    db: AsyncSession = Depends(get_db),
) -> ConformityRouteOut:
    if await _set_project_rls(project_id, db) is None:
        raise HTTPException(404, "Project not found")
    existing = await _get_route_row(db, project_id)
    if existing is not None:
        raise HTTPException(409, "Route already locked for this project")

    if body.category == "BASICA" and body.route_type != RouteType.DECLARATION:
        raise HTTPException(422, "BASICA requires route_type=DECLARATION")
    if body.category in ("MEDIA", "ALTA") and body.route_type != RouteType.CERTIFICATION:
        raise HTTPException(422, f"{body.category} requires route_type=CERTIFICATION")

    new_state = RouteState.ROUTE_LOCKED
    locked_at = datetime.now(timezone.utc)
    next_review_due = date.today() + timedelta(days=730)

    row = ConformityRouteRow(
        project_id=project_id,
        route_type=_route_type_to_db(body.route_type),
        status=new_state.value,
        initiated_at=locked_at,
        expiration_date=next_review_due,
        metadata_jsonb={
            "category": body.category,
            "overlay_code": body.overlay_code,
            "rationale": body.rationale,
            "next_review_due": next_review_due.isoformat(),
        },
        created_at=locked_at,
    )
    db.add(row)
    await db.flush()
    await _record_history(
        db, project_id, "ROUTE_PENDING", new_state.value, body.rationale,
    )
    await db.commit()
    return _route_to_out(row)


@router.post("/projects/{project_id}/route/revalidate", response_model=ConformityRouteOut)
async def revalidate_route(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ConformityRouteOut:
    if await _set_project_rls(project_id, db) is None:
        raise HTTPException(404, "Project not found")
    row = await _get_route_row(db, project_id)
    if row is None:
        raise HTTPException(404, f"No conformity route for project {project_id}")

    cur_state = RouteState(row.status)
    if cur_state in (RouteState.ACTIVE, RouteState.RENEWAL_DUE):
        new = (
            RouteState.UNDER_REVIEW if cur_state == RouteState.RENEWAL_DUE
            else RouteState.RENEWAL_DUE
        )
    elif can_transition(cur_state, RouteState.UNDER_REVIEW):
        new = RouteState.UNDER_REVIEW
    else:
        raise HTTPException(409, f"Cannot revalidate from state {cur_state.value}")

    try:
        new_state = transition(cur_state, new, route_type=_route_type_from_db(row.route_type))
    except InvalidRouteTransitionError as exc:
        raise HTTPException(409, str(exc)) from exc

    row.status = new_state.value
    await db.flush()
    await _record_history(
        db, project_id, cur_state.value, new_state.value, "manual revalidation",
    )
    await db.commit()
    return _route_to_out(row)


@router.get("/projects/{project_id}/status", response_model=ConformityStatus)
async def get_status(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ConformityStatus:
    await _set_project_rls(project_id, db)
    route_row = await _get_route_row(db, project_id)

    subs_stmt = select(ConformitySubmissionRow).where(
        ConformitySubmissionRow.project_id == project_id,
    )
    submissions = list((await db.execute(subs_stmt)).scalars())

    renewal_stmt = (
        select(RenewalCampaignRow)
        .where(RenewalCampaignRow.project_id == project_id)
        .order_by(desc(RenewalCampaignRow.created_at))
        .limit(1)
    )
    renewal_row = (await db.execute(renewal_stmt)).scalar_one_or_none()

    overlays_stmt = select(PceOverlayRow).where(
        PceOverlayRow.project_id == project_id,
    )
    overlays_rows = list((await db.execute(overlays_stmt)).scalars())

    snapshot = {
        "project_phase": 1 if route_row else 0,
        "route": (
            {"state": route_row.status} if route_row else None
        ),
        "overlays": [{"is_primary": True} for _ in overlays_rows[:1]],
        "submissions": [
            {"state": (s.submission_payload_jsonb or {}).get("state", "GENERATED"),
             "payload_present": True,
             "proof_present": bool((s.response_jsonb or {}).get("proof_reference"))}
            for s in submissions
        ],
        "renewals": (
            [{"state": (renewal_row.result_jsonb or {}).get("state", "PLANNED"),
              "target_renewal_date": (renewal_row.result_jsonb or {}).get(
                  "target_renewal_date"
              )}]
            if renewal_row else []
        ),
    }
    violations = service.check_invariants(snapshot)
    pending = sum(1 for s in submissions
                  if (s.submission_payload_jsonb or {}).get("state", "GENERATED")
                  not in ("COMPLETED", "REJECTED", "WITHDRAWN"))

    target_date_str = (renewal_row.result_jsonb or {}).get(
        "target_renewal_date"
    ) if renewal_row else None
    return ConformityStatus(
        project_id=project_id,
        route=_route_to_out(route_row) if route_row else None,
        submissions_count=len(submissions),
        pending_submissions=pending,
        renewal_state=(renewal_row.result_jsonb or {}).get("state") if renewal_row else None,
        next_renewal_due=date.fromisoformat(target_date_str) if target_date_str else None,
        invariants_ok=not violations,
        invariant_violations=violations,
    )


@router.get("/projects/{project_id}/route/history")
async def route_history(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _set_project_rls(project_id, db)
    stmt = (
        select(ConformityStateSnapshotRow)
        .where(
            ConformityStateSnapshotRow.project_id == project_id,
            ConformityStateSnapshotRow.snapshot_type == "route_transition",
        )
        .order_by(ConformityStateSnapshotRow.created_at)
    )
    rows = list((await db.execute(stmt)).scalars())
    return {
        "project_id": str(project_id),
        "history": [r.metadata_jsonb for r in rows],
    }


# ════════════════════════════════════════════════════════════════════
# Declaration
# ════════════════════════════════════════════════════════════════════


@router.post(
    "/projects/{project_id}/declaration/generate",
    response_model=DeclarationOut,
    status_code=status.HTTP_201_CREATED,
)
async def generate_declaration(
    project_id: uuid.UUID,
    body: DeclarationGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> DeclarationOut:
    if await _set_project_rls(project_id, db) is None:
        raise HTTPException(404, "Project not found")
    route_row = await _get_route_row(db, project_id)
    if route_row is None:
        raise HTTPException(404, f"No conformity route for project {project_id}")
    if _route_type_from_db(route_row.route_type) != RouteType.DECLARATION:
        raise HTTPException(422, "Declaration only valid for route_type=DECLARATION")

    decl_data = service.generate_declaration(project_id, body.requested_by)
    declaration_id = decl_data["declaration_id"]
    generated_at = decl_data["generated_at"]

    row = BasicDeclarationRow(
        id=declaration_id,
        project_id=project_id,
        declaration_type="initial",
        responsible_person_name=body.requested_by,
        status="draft",
        signed_at=None,
        created_at=generated_at if isinstance(generated_at, datetime) else datetime.now(timezone.utc),
    )
    db.add(row)
    await db.flush()
    await db.commit()
    return DeclarationOut(
        project_id=project_id,
        declaration_id=declaration_id,
        documents=decl_data["documents"],
        generated_at=generated_at,
        state="draft",
    )


# ════════════════════════════════════════════════════════════════════
# Submissions
# ════════════════════════════════════════════════════════════════════


def _submission_to_out(row: ConformitySubmissionRow) -> SubmissionOut:
    metadata = row.submission_payload_jsonb or {}
    response = row.response_jsonb or {}
    state_str = metadata.get(
        "state",
        SubmissionState.GENERATED.value,
    )
    completed_at_str = metadata.get("completed_at")
    completed_at = (
        datetime.fromisoformat(completed_at_str) if completed_at_str else None
    )
    # target_api preservado en metadata; fallback a row.external_system.
    target_api = metadata.get("target_api") or row.external_system or row.submission_type
    return SubmissionOut(
        submission_id=row.id,
        project_id=row.project_id,
        target=target_api,
        state=SubmissionState(state_str),
        payload_present=bool(metadata),
        proof_present=bool(response.get("proof_reference")),
        created_at=row.created_at or datetime.now(timezone.utc),
        submitted_at=row.submitted_at,
        completed_at=completed_at,
    )


@router.post(
    "/projects/{project_id}/submissions",
    response_model=SubmissionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_submission(
    project_id: uuid.UUID,
    body: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
) -> SubmissionOut:
    if await _set_project_rls(project_id, db) is None:
        raise HTTPException(404, "Project not found")
    route_row = await _get_route_row(db, project_id)
    if route_row is None:
        raise HTTPException(404, f"No conformity route for project {project_id}")

    sub_data = service.create_submission(project_id, body.target, body.payload_template)
    sub_id = sub_data["submission_id"]
    created_at = sub_data["created_at"]
    state_value = sub_data["state"].value if hasattr(sub_data["state"], "value") else sub_data["state"]

    row = ConformitySubmissionRow(
        id=sub_id,
        project_id=project_id,
        submission_type=_TARGET_API_TO_DB.get(body.target, "enac_dossier"),
        external_system=body.target,
        submitted_by="marcos",
        external_ref_id=None,
        submission_payload_jsonb={
            "payload_template": body.payload_template,
            "justification": body.justification,
            "state": state_value,
            "target_api": body.target,
        },
        response_jsonb=None,
        status="generated",
        errors_jsonb=None,
        created_at=created_at if isinstance(created_at, datetime) else datetime.now(timezone.utc),
    )
    db.add(row)
    await db.flush()
    await db.commit()
    return _submission_to_out(row)


@router.post(
    "/projects/{project_id}/submissions/{sid}/submit-proof",
    response_model=SubmissionOut,
)
async def submit_proof(
    project_id: uuid.UUID,
    sid: uuid.UUID,
    body: SubmissionProofUpload,
    db: AsyncSession = Depends(get_db),
) -> SubmissionOut:
    if await _set_project_rls(project_id, db) is None:
        raise HTTPException(404, "Project not found")
    stmt = select(ConformitySubmissionRow).where(
        ConformitySubmissionRow.id == sid,
        ConformitySubmissionRow.project_id == project_id,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, f"Submission {sid} not found in project {project_id}")

    metadata = dict(row.submission_payload_jsonb or {})
    response = dict(row.response_jsonb or {})
    response.update({
        "proof_type": body.proof_type,
        "proof_reference": body.proof_reference,
    })
    if body.completed:
        metadata["state"] = SubmissionState.COMPLETED.value
        metadata["completed_at"] = datetime.now(timezone.utc).isoformat()
        row.status = "completed"
    row.submission_payload_jsonb = metadata
    row.response_jsonb = response
    await db.flush()
    await db.commit()
    return _submission_to_out(row)


# ════════════════════════════════════════════════════════════════════
# Renewal
# ════════════════════════════════════════════════════════════════════


def _renewal_to_out(row: RenewalCampaignRow) -> RenewalCampaignOut:
    result = row.result_jsonb or {}
    target_date_str = result.get("target_renewal_date")
    return RenewalCampaignOut(
        project_id=row.project_id,
        state=result.get("state", "T-180"),
        target_renewal_date=(
            date.fromisoformat(target_date_str) if target_date_str else date.today()
        ),
        days_remaining=int(result.get("days_remaining", 0)),
        actions_required=list(result.get("actions_required", [])),
    )


@router.post("/projects/{project_id}/renewal/start", response_model=RenewalCampaignOut)
async def start_renewal(
    project_id: uuid.UUID,
    target_date: date,
    db: AsyncSession = Depends(get_db),
) -> RenewalCampaignOut:
    if await _set_project_rls(project_id, db) is None:
        raise HTTPException(404, "Project not found")
    state = service.compute_renewal_state(target_date)

    payload = {
        "state": state["state"],
        "target_renewal_date": (
            state["target_renewal_date"].isoformat()
            if isinstance(state["target_renewal_date"], date)
            else state["target_renewal_date"]
        ),
        "days_remaining": state["days_remaining"],
        "actions_required": state["actions_required"],
    }

    row = RenewalCampaignRow(
        project_id=project_id,
        campaign_type="recertification_bianual",
        scheduled_for=datetime.combine(target_date, datetime.min.time(), timezone.utc),
        auto_triggered=False,
        result_jsonb=payload,
        status="planned",
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    await db.flush()
    await db.commit()
    return _renewal_to_out(row)


@router.get("/projects/{project_id}/renewal", response_model=RenewalCampaignOut)
async def get_renewal(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RenewalCampaignOut:
    await _set_project_rls(project_id, db)
    stmt = (
        select(RenewalCampaignRow)
        .where(RenewalCampaignRow.project_id == project_id)
        .order_by(desc(RenewalCampaignRow.created_at))
        .limit(1)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, f"No renewal campaign for {project_id}")
    return _renewal_to_out(row)


# ════════════════════════════════════════════════════════════════════
# External Exports
# ════════════════════════════════════════════════════════════════════


_ADAPTERS = {
    "PILAR": pilar_adapter.export,
    "LUCIA": lucia_adapter.export,
    "INES": ines_adapter.export,
    "Registro": registry_adapter.export,
}


def _export_to_out(row: ConformityStateSnapshotRow) -> ExternalExportOut:
    md = row.metadata_jsonb or {}
    return ExternalExportOut(
        export_id=row.id,
        tool=md.get("tool", "unknown"),
        artifact_path=md.get("artifact_path", ""),
        artifact_hash=md.get("artifact_hash", ""),
        checklist=list(md.get("checklist", [])),
        created_at=row.created_at or datetime.now(timezone.utc),
        proof_uploaded=bool(md.get("proof_uploaded", False)),
    )


@router.post(
    "/projects/{project_id}/external-exports",
    response_model=ExternalExportOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_export(
    project_id: uuid.UUID,
    body: ExternalExportCreate,
    db: AsyncSession = Depends(get_db),
) -> ExternalExportOut:
    if await _set_project_rls(project_id, db) is None:
        raise HTTPException(404, "Project not found")
    adapter = _ADAPTERS.get(body.tool)
    if not adapter:
        raise HTTPException(422, f"Unknown tool {body.tool}")
    artifact = adapter(project_id, body.params)

    # Sanitizar UUIDs y datetimes a strings para JSONB-safe.
    def _jsonable(value):
        if isinstance(value, uuid.UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: _jsonable(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_jsonable(v) for v in value]
        return value

    metadata = {
        "tool": body.tool,
        "params": _jsonable(body.params),
        **{k: _jsonable(v) for k, v in artifact.items()
           if k not in ("export_id", "created_at")},
        "proof_uploaded": False,
    }

    row = ConformityStateSnapshotRow(
        project_id=project_id,
        snapshot_type="external_export",
        metadata_jsonb=metadata,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    await db.flush()
    await db.commit()
    return _export_to_out(row)


@router.get("/projects/{project_id}/external-exports")
async def list_exports(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ExternalExportOut]:
    await _set_project_rls(project_id, db)
    stmt = (
        select(ConformityStateSnapshotRow)
        .where(
            ConformityStateSnapshotRow.project_id == project_id,
            ConformityStateSnapshotRow.snapshot_type == "external_export",
        )
        .order_by(desc(ConformityStateSnapshotRow.created_at))
    )
    rows = list((await db.execute(stmt)).scalars())
    return [_export_to_out(r) for r in rows]


@router.post(
    "/projects/{project_id}/external-exports/{eid}/upload-proof",
    response_model=ExternalExportOut,
)
async def upload_export_proof(
    project_id: uuid.UUID,
    eid: uuid.UUID,
    proof_reference: str,
    db: AsyncSession = Depends(get_db),
) -> ExternalExportOut:
    if await _set_project_rls(project_id, db) is None:
        raise HTTPException(404, "Project not found")
    stmt = select(ConformityStateSnapshotRow).where(
        ConformityStateSnapshotRow.id == eid,
        ConformityStateSnapshotRow.project_id == project_id,
        ConformityStateSnapshotRow.snapshot_type == "external_export",
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Export not found")

    md = dict(row.metadata_jsonb or {})
    md["proof_uploaded"] = True
    md["proof_reference"] = proof_reference
    row.metadata_jsonb = md
    await db.flush()
    await db.commit()
    return _export_to_out(row)


# ════════════════════════════════════════════════════════════════════
# PCE Overlay
# ════════════════════════════════════════════════════════════════════


@router.get("/projects/{project_id}/pce-overlay", response_model=PceOverlayOut)
async def get_overlay(
    project_id: uuid.UUID,
    sector: str = "generico",
    category: str = "BASICA",
) -> PceOverlayOut:
    """Pure compute: detecta overlay aplicable. NO persiste — la
    persistencia se hace via endpoint dedicado en api_paso5
    ``apply_overlay``. Llamadas idempotentes."""
    detected = service.detect_overlay(sector, category)
    return PceOverlayOut(
        project_id=project_id,
        overlay_code=detected["overlay_code"],
        overlay_name=detected["overlay_name"],
        extra_controls=detected["extra_controls"],
        detection_confidence=detected["detection_confidence"],
        rationale=detected["rationale"],
    )


@router.post("/projects/{project_id}/pce-overlay/validate")
async def validate_overlay(
    project_id: uuid.UUID,
    overlay_code: str,
    project_category: str,
) -> dict:
    """Pure compute: valida overlay vs categoría. NO persiste."""
    return service.validate_overlay(overlay_code, project_category)


# ================================================================
# DISTINTIVO + DECLARACIÓN CCN-STIC 809 (SAN-C.MB-9.2)
# ================================================================


@router.post("/projects/{project_id}/declaration/generate-docx")
async def generate_declaration_docx_endpoint(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Genera Declaración Conformidad Básica E-180 (CCN-STIC 809) DOCX.

    Aglutina M01 categorización + M03 DdA totales + M30 RSEG +
    metadata distintivo (cert_id determinístico + URL pública).

    NOTA SAN-C.MB-9.bis.0: ruta es ``/declaration/generate-docx`` (no
    ``/declaration/generate``) para evitar colisión con el endpoint
    paso5 ``submit_basic_declaration_paso5`` que ya ocupa la ruta
    ``/declaration/generate`` con response_model JSON.

    Refs: SAN-C.MB-9.2
    """
    from fastapi.responses import Response

    from .distintivo_generator import (
        DECLARATION_DOCUMENT_KIND,
        build_distintivo_context,
        generate_declaration_docx,
    )

    ctx = await build_distintivo_context(db, project_id)
    bio = generate_declaration_docx(ctx)
    return Response(
        content=bio.getvalue(),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="declaracion_conformidad_{project_id}.docx"'
            ),
            "X-Cert-Id": str(ctx.cert_id),
            "X-Document-Kind": DECLARATION_DOCUMENT_KIND,
        },
    )


@router.get("/projects/{project_id}/cert-id")
async def get_cert_id_endpoint(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Devuelve cert_id determinístico + URL pública del distintivo.

    Frontend usa este endpoint en /conformity tab para resolver el
    cert_id sin re-implementar uuid5 derivation client-side.

    Refs: SAN-C.MB-9.bis.0
    """
    from .distintivo_generator import (
        build_distintivo_context,
        derive_cert_id,
    )

    cert_id = derive_cert_id(project_id)
    try:
        ctx = await build_distintivo_context(db, project_id)
        category = ctx.system_category
        public_badge_url = ctx.public_badge_url
        issued_date = ctx.today
        expiry_date = ctx.expiry_date
    except ValueError:
        category = None
        public_badge_url = (
            f"/api/v1/public/conformity/badge/{cert_id}/badge.svg"
        )
        issued_date = None
        expiry_date = None

    return {
        "project_id": str(project_id),
        "cert_id": str(cert_id),
        "category": category,
        "public_badge_url": public_badge_url,
        "issued_date": issued_date,
        "expiry_date": expiry_date,
    }


# ================================================================
# Audit schedules art. 31 (SAN-C.MB-10.6)
# ================================================================


@router.get("/projects/{project_id}/audit-schedule")
async def get_audit_schedule(
    project_id: uuid.UUID,
    horizon_days: int = 365,
    db: AsyncSession = Depends(get_db),
):
    """Lista auditorías programadas (bienal / extraordinaria) en horizonte N días.

    Refs: SAN-C.MB-10.6 · art. 31 RD 311/2022
    """
    from .audit_schedule_service import list_upcoming_audits

    await set_tenant_context(db, project_id=project_id)
    upcoming = await list_upcoming_audits(db, project_id, horizon_days=horizon_days)
    return [
        {
            "id": str(e.id),
            "audit_type": e.audit_type,
            "next_audit_due": e.next_audit_due.isoformat(),
            "last_audit_completed": e.last_audit_completed.isoformat()
            if e.last_audit_completed
            else None,
            "last_audit_result": e.last_audit_result,
            "triggered_by": e.triggered_by,
            "days_until_due": e.days_until_due,
        }
        for e in upcoming
    ]


# ================================================================
# INES Annual Report (SAN-C.MB-10.4) · CCN-STIC 824/844
# ================================================================


@router.get("/organizations/{organization_id}/ines/{year}/json")
async def ines_annual_json(
    organization_id: uuid.UUID,
    year: int,
    db: AsyncSession = Depends(get_db),
):
    """Genera JSON canónico INES (CCN-STIC 824) para subida portal."""
    from .ines_generator import collect_ines_data, generate_ines_json

    report = await collect_ines_data(db, organization_id, year)
    return generate_ines_json(report)


@router.post("/organizations/{organization_id}/ines/{year}/docx")
async def ines_annual_docx(
    organization_id: uuid.UUID,
    year: int,
    db: AsyncSession = Depends(get_db),
):
    """Genera DOCX legible INES anual para Dirección + auditor."""
    from fastapi.responses import Response

    from .ines_generator import collect_ines_data, generate_ines_docx

    report = await collect_ines_data(db, organization_id, year)
    bio = generate_ines_docx(report)
    return Response(
        content=bio.getvalue(),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="ines_{year}_{organization_id}.docx"'
            ),
        },
    )


# ================================================================
# LUCIA federación CCN-CERT (SAN-C.MB-10.3)
# ================================================================


@router.get("/projects/{project_id}/lucia/submissions")
async def list_lucia_submissions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Lista submissions LUCIA del proyecto (con status)."""
    await set_tenant_context(db, project_id=project_id)
    rows = await db.execute(
        sa_text(
            "SELECT id::text, incident_id::text, submission_id_remote, "
            "       status, submitted_at, last_status_check, "
            "       LEFT(COALESCE(error_detail, ''), 300), created_at "
            "FROM lucia_submissions WHERE project_id = :pid "
            "ORDER BY created_at DESC LIMIT 100"
        ),
        {"pid": str(project_id)},
    )
    return [
        {
            "id": r[0],
            "incident_id": r[1],
            "submission_id_remote": r[2],
            "status": r[3],
            "submitted_at": r[4].isoformat() if r[4] else None,
            "last_status_check": r[5].isoformat() if r[5] else None,
            "error_detail": r[6] or None,
            "created_at": r[7].isoformat(),
        }
        for r in rows.fetchall()
    ]


@router.get("/projects/{project_id}/lucia/credentials-status")
async def lucia_credentials_status(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Estado de credenciales LUCIA del proyecto (sin exponer secret)."""
    await set_tenant_context(db, project_id=project_id)
    row = await db.execute(
        sa_text(
            "SELECT organization_id_lucia, endpoint_base_url, verified_at, "
            "       expires_at, created_at "
            "FROM lucia_credentials WHERE project_id = :pid"
        ),
        {"pid": str(project_id)},
    )
    record = row.first()
    if record is None:
        return {
            "configured": False,
            "fallback_mode": "pending_credentials",
            "next_step": (
                "Cliente debe registrarse en LUCIA CCN-CERT y aportar "
                "credenciales OAuth (organization_id + client_id + client_secret) "
                "vía POST /lucia/credentials. Mientras tanto los incidentes "
                "se generan en JSON canónico para subida manual al portal."
            ),
        }
    return {
        "configured": True,
        "organization_id": record[0],
        "endpoint_base_url": record[1],
        "verified_at": record[2].isoformat() if record[2] else None,
        "expires_at": record[3].isoformat() if record[3] else None,
        "created_at": record[4].isoformat(),
    }


@router.get("/projects/{project_id}/badge.svg")
async def admin_badge_svg(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Sirve distintivo SVG (admin · auth-protected) para preview pre-publicación.

    El cliente publicará el badge desde el endpoint público
    ``/api/v1/public/conformity/badge/{cert_id}/badge.svg`` (sin auth).

    Refs: SAN-C.MB-9.2
    """
    from fastapi.responses import Response

    from .distintivo_generator import (
        build_distintivo_context,
        generate_distintivo_svg,
    )

    ctx = await build_distintivo_context(db, project_id)
    svg = generate_distintivo_svg(ctx)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "X-Cert-Id": str(ctx.cert_id),
            "X-Public-URL": ctx.public_badge_url,
        },
    )
