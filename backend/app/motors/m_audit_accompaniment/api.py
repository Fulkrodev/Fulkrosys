"""m_audit_accompaniment REST API · Sesión 3B-4 Ejecutable 7.5 (2026-05-27).

Routes admin (require_owner ADR-013):
- POST /admin/projects/{id}/accompaniment/advance · advance state machine
- POST /admin/projects/{id}/accompaniment/artifacts · upload artifact
- GET  /admin/projects/{id}/accompaniment/timeline · admin timeline render

Routes cliente (require_client_user ADR-013 cliente pool · read-only):
- GET  /client-portal/accompaniment/timeline · cliente read-only timeline R29
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.core.workflow_gates import WorkflowGateError
from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m_audit_accompaniment.service import (
    AccompanimentTimeline,
    InvalidAccompanimentTransition,
    get_timeline,
    transition_state,
    upload_artifact,
)


router = APIRouter(tags=["Audit Accompaniment (Sesión 3B-4 Ejecutable 7.5)"])


# Local file storage path for artifacts (MVP · S3 post-piloto enrichment)
ARTIFACTS_BASE_PATH = Path(
    os.environ.get(
        "FULKRO_ACCOMPANIMENT_ARTIFACTS_PATH",
        "/tmp/fulkro_accompaniment_artifacts",
    )
)


class TransitionAdvanceBody(BaseModel):
    target_state: str = Field(min_length=1, max_length=64)
    transition_metadata: dict = Field(default_factory=dict)
    # GATE-7 (#40 · FRENTE D) escape-hatch administrativo justificado: permite
    # solicitar ENAC / firmar conformidad pese a NC mayores abiertas. Queda
    # trazado en audit_log (nc_override=True). Úsese solo con justificación.
    allow_open_nc: bool = False


class TransitionAdvanceResponse(BaseModel):
    project_id: str
    from_state: str
    to_state: str
    category_branch: str
    is_terminal: bool


class ArtifactUploadResponse(BaseModel):
    artifact_id: str
    state: str
    artifact_type: str
    sha256: str
    size_bytes: int


class TimelineResponse(BaseModel):
    project_id: str
    category_branch: str
    current_state: str
    last_advanced_at: str | None
    is_terminal: bool
    transitions: list
    artifacts: list


@router.post(
    "/admin/projects/{project_id}/accompaniment/advance",
    response_model=TransitionAdvanceResponse,
)
async def advance_state(
    project_id: UUID,
    body: TransitionAdvanceBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> TransitionAdvanceResponse:
    """Advance accompaniment state machine to target_state · admin only."""
    try:
        result = await transition_state(
            db, project_id, body.target_state,
            usuario=current_user.email,
            transition_metadata=body.transition_metadata,
            allow_open_nc=body.allow_open_nc,
        )
    except WorkflowGateError as exc:
        # GATE-7 (#40/#43): parón pre-ENAC · 409 Conflict (precondición no cumplida).
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc),
        )
    except InvalidAccompanimentTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    return TransitionAdvanceResponse(**result)


@router.post(
    "/admin/projects/{project_id}/accompaniment/artifacts",
    response_model=ArtifactUploadResponse,
)
async def upload_artifact_endpoint(
    project_id: UUID,
    state: str = Form(...),
    artifact_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> ArtifactUploadResponse:
    """Upload artifact per state · stored local filesystem MVP + sha256 + audit_log."""
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file body",
        )

    project_dir = ARTIFACTS_BASE_PATH / str(project_id) / state
    project_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = (file.filename or "artifact.bin").replace("/", "_").replace("\\", "_")
    file_path = project_dir / f"{uuid.uuid4().hex[:8]}_{safe_filename}"
    file_path.write_bytes(contents)

    result = await upload_artifact(
        db, project_id,
        state=state,
        artifact_type=artifact_type,
        file_bytes=contents,
        file_path=str(file_path),
        usuario=current_user.email,
    )
    return ArtifactUploadResponse(**result)


@router.get(
    "/admin/projects/{project_id}/accompaniment/timeline",
    response_model=TimelineResponse,
)
async def admin_timeline(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> TimelineResponse:
    """Admin timeline render · full transitions + artifacts chronological."""
    timeline: AccompanimentTimeline = await get_timeline(db, project_id)
    return TimelineResponse(
        project_id=timeline.project_id,
        category_branch=timeline.category_branch,
        current_state=timeline.current_state,
        last_advanced_at=timeline.last_advanced_at,
        is_terminal=timeline.is_terminal,
        transitions=[t.__dict__ for t in timeline.transitions],
        artifacts=[a.__dict__ for a in timeline.artifacts],
    )


@router.get(
    "/client-portal/accompaniment/timeline",
    response_model=TimelineResponse,
)
async def cliente_timeline(
    db: AsyncSession = Depends(get_db),
    client_user: ClientUser = Depends(get_current_client_user),
) -> TimelineResponse:
    """Cliente read-only timeline · R29 friendly · single-project per cliente LIMIT 1."""
    from sqlalchemy import text as sa_text

    row = (await db.execute(sa_text(
        "SELECT id FROM projects "
        "WHERE client_id = :cid AND deleted_at IS NULL "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"cid": str(client_user.client_id)})).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No project found for this client",
        )
    project_id = row[0]

    timeline = await get_timeline(db, project_id)
    return TimelineResponse(
        project_id=timeline.project_id,
        category_branch=timeline.category_branch,
        current_state=timeline.current_state,
        last_advanced_at=timeline.last_advanced_at,
        is_terminal=timeline.is_terminal,
        transitions=[t.__dict__ for t in timeline.transitions],
        artifacts=[a.__dict__ for a in timeline.artifacts],
    )
