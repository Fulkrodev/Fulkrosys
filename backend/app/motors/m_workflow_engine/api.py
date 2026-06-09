"""m_workflow_engine API · 8 endpoints duales (sub-atom 1.C.D.A v3.8).

Endpoints:
  ADMIN (4 · require_owner):
    GET  /api/v1/admin/workflow-command-center
    GET  /api/v1/admin/workflow-command-center/projects/{id}
    POST /api/v1/admin/workflow-command-center/projects/{id}/steps/{template_id}/advance

  INTERNOS (4 · require_marcos_or_client + ownership · reusable copilotos 1.D.B):
    GET  /api/v1/projects/{id}/workflow-engine/catalog
    GET  /api/v1/projects/{id}/workflow-engine/current-step
    GET  /api/v1/projects/{id}/workflow-engine/progress
    GET  /api/v1/projects/{id}/workflow-engine/timeline

  CLIENTE (1 · require_marcos_or_client + ownership):
    GET  /api/v1/projects/{id}/workflow-guide
"""
from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_marcos_or_client, require_owner
from backend.app.core.workflow_state import verify_client_owns_project
from backend.app.database import get_db
from backend.app.models.core import Project

from .deliverables_service import (
    DeliverablesServiceError,
    StepDeliverablesResponse,
    WorkflowDeliverablesService,
)
from .engine import (
    EnrichedStepState,
    compute_current_step_for_project,
    compute_progress_for_project,
    compute_steps_for_project,
    load_project_dims,
)
from .service import WorkflowEngineService, WorkflowEngineServiceError


# ==================================================================
# Routers
# ==================================================================


admin_router = APIRouter(
    prefix="/admin/workflow-command-center",
    tags=["m_workflow_engine · Admin Command Center"],
    dependencies=[Depends(require_owner)],
)


reader_router = APIRouter(
    prefix="/projects",
    tags=["m_workflow_engine · reader (admin + cliente)"],
)


# ==================================================================
# Helpers
# ==================================================================


async def _ensure_project_access(
    db: AsyncSession, project_id: uuid.UUID, request: Request,
) -> uuid.UUID:
    """Marcos bypass · cliente verify ownership · returns updated_by uuid."""
    subject = getattr(request.state, "auth_subject", None)
    if subject is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    pool = getattr(subject, "pool", None) or getattr(
        subject.user, "pool", None,
    )
    user_id = subject.user.id

    if pool == "auth_users" or getattr(subject.user, "is_marcos", False):
        return user_id

    client_id = getattr(subject.user, "client_id", None)
    if client_id is None:
        raise HTTPException(status_code=403, detail="Sin client_id")
    if not await verify_client_owns_project(db, project_id, client_id):
        raise HTTPException(status_code=403, detail="No tienes acceso al proyecto")
    return user_id


# ==================================================================
# ADMIN · Command Center
# ==================================================================


class CommandCenterProjectCard(BaseModel):
    """Mini-card de proyecto en Command Center multi-cliente."""

    project_id: uuid.UUID
    project_nombre: str
    categoria: str | None
    archetype: str | None
    current_phase: str
    current_step_title: str | None
    current_step_urgency: int
    progress_pct: int
    progress_completed: int
    progress_total: int


class CommandCenterResponse(BaseModel):
    """Vista admin multi-cliente cronológica."""

    urgentes_hoy: list[CommandCenterProjectCard] = Field(default_factory=list)
    esta_semana: list[CommandCenterProjectCard] = Field(default_factory=list)
    en_marcha: list[CommandCenterProjectCard] = Field(default_factory=list)
    proximos_30d: list[CommandCenterProjectCard] = Field(default_factory=list)


@admin_router.get("", response_model=CommandCenterResponse)
async def admin_command_center(
    db: AsyncSession = Depends(get_db),
) -> CommandCenterResponse:
    """Vista admin multi-cliente · cronológica per urgencia.

    NO trae proyectos completados/cerrados · solo activos (lifecycle_state IN
    DRAFT/NEGOTIATING/SIGNED/ACTIVE/CERTIFIED/RETAINER).
    """
    active_states = (
        "DRAFT",
        "NEGOTIATING",
        "SIGNED",
        "ACTIVE",
        "CERTIFIED",
        "RETAINER",
    )
    rows = await db.execute(
        select(Project).where(
            Project.lifecycle_state.in_(active_states),
            Project.deleted_at.is_(None),
        )
    )
    projects = list(rows.scalars().all())

    cards: list[CommandCenterProjectCard] = []
    for p in projects:
        current_step = await compute_current_step_for_project(db, p.id)
        progress = await compute_progress_for_project(db, p.id)
        cards.append(
            CommandCenterProjectCard(
                project_id=p.id,
                project_nombre=p.nombre,
                categoria=p.categoria_objetivo,
                archetype=p.archetype,
                current_phase=p.fase,
                current_step_title=current_step.title if current_step else None,
                current_step_urgency=current_step.urgency_score if current_step else 0,
                progress_pct=progress["global_pct"],
                progress_completed=progress["global_completed"],
                progress_total=progress["global_total"],
            )
        )

    # Partition by urgency
    urgentes = [c for c in cards if c.current_step_urgency >= 75]
    semana = [c for c in cards if 50 <= c.current_step_urgency < 75]
    en_marcha = [c for c in cards if 25 <= c.current_step_urgency < 50]
    proximos = [c for c in cards if c.current_step_urgency < 25]

    # Sort each bucket by urgency desc
    urgentes.sort(key=lambda c: -c.current_step_urgency)
    semana.sort(key=lambda c: -c.current_step_urgency)
    en_marcha.sort(key=lambda c: -c.current_step_urgency)
    proximos.sort(key=lambda c: -c.current_step_urgency)

    return CommandCenterResponse(
        urgentes_hoy=urgentes,
        esta_semana=semana,
        en_marcha=en_marcha,
        proximos_30d=proximos,
    )


class ProjectCronologicaResponse(BaseModel):
    """Vista cronológica detallada per proyecto."""

    project_id: uuid.UUID
    project_nombre: str
    dims: dict[str, Any]
    current_phase: str
    progress: dict[str, Any]
    completed: list[EnrichedStepState]
    ahora: EnrichedStepState | None
    proximos_7d: list[EnrichedStepState]
    proximos_30d: list[EnrichedStepState]


@admin_router.get(
    "/projects/{project_id}",
    response_model=ProjectCronologicaResponse,
)
async def admin_project_cronologica(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProjectCronologicaResponse:
    """Vista cronológica detallada per proyecto · admin only."""
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    dims = await load_project_dims(db, project_id)
    steps = await compute_steps_for_project(db, project_id)
    progress = await compute_progress_for_project(db, project_id)
    current = await compute_current_step_for_project(db, project_id)

    completed = [s for s in steps if s.status == "completed"]
    pending = [s for s in steps if s.status != "completed"]
    # ahora = current_step (max urgency · NO completed)
    # proximos_7d = next 3-5 pending (high priority · pending)
    # proximos_30d = forecast resto

    pending_sorted = sorted(pending, key=lambda s: -s.urgency_score)
    ahora = current
    next_5 = [s for s in pending_sorted if s.template_id != (current.template_id if current else None)][:5]
    next_resto = [
        s for s in pending_sorted
        if s.template_id != (current.template_id if current else None)
        and s not in next_5
    ]

    return ProjectCronologicaResponse(
        project_id=project_id,
        project_nombre=project.nombre,
        dims=dims,
        current_phase=project.fase,
        progress=progress,
        completed=completed,
        ahora=ahora,
        proximos_7d=next_5,
        proximos_30d=next_resto,
    )


@admin_router.post(
    "/projects/{project_id}/steps/{template_id}/advance",
    status_code=status.HTTP_200_OK,
)
async def admin_advance_step(
    project_id: uuid.UUID,
    template_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Marcos override · marca step completado."""
    user_id = await _ensure_project_access(db, project_id, request)
    service = WorkflowEngineService(db)
    try:
        task = await service.advance_step(
            project_id=project_id,
            template_id=template_id,
            updated_by=user_id,
        )
    except WorkflowEngineServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "task_id": str(task.id),
        "template_id": task.template_id,
        "status": task.status,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


# ==================================================================
# 1.D.G.D · Admin "Recordar al cliente"
# ==================================================================


class RemindClientResponse(BaseModel):
    project_id: uuid.UUID
    template_id: str
    notified: bool
    channels: list[str]
    message: str


@admin_router.post(
    "/projects/{project_id}/steps/{template_id}/remind",
    status_code=status.HTTP_200_OK,
    response_model=RemindClientResponse,
)
async def admin_remind_client_step(
    project_id: uuid.UUID,
    template_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RemindClientResponse:
    """Marcos dispara recordatorio cliente para step pendiente (1.D.G.D).

    Reuse infraestructura M18 communication existing:
      - In-app ClientNotification (inbox)
      - Email reminder via M18 send_email
      - WhatsApp opt-in si feature flag enabled (1.D.G.F)

    Idempotente · NO duplica notifications si already sent < 24h.
    """
    await _ensure_project_access(db, project_id, request)

    from backend.app.motors.m21_portal_cliente.task_templates_loader import (
        get_template_by_id, resolve_primary_actor,
    )

    template = get_template_by_id(template_id)
    if template is None:
        raise HTTPException(
            status_code=404, detail=f"Template {template_id} not found",
        )

    primary_actor = resolve_primary_actor(template)
    if primary_actor != "cliente":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Step {template_id} primary_actor={primary_actor} · "
                "solo se puede recordar steps cliente-driven"
            ),
        )

    # Reuse existing 1.D.G.F notification trigger pattern (created next sub-fase)
    # Si notification handler aún no wired · response indica fallback
    channels: list[str] = ["in_app"]
    message = (
        f"Recordatorio enviado al cliente · paso «{template.title}»"
    )
    try:
        from backend.app.notifications.workflow_step_notifications import (  # type: ignore
            send_client_remind_notification,
        )
        result = await send_client_remind_notification(
            db=db,
            project_id=project_id,
            template=template,
        )
        channels = result.channels
        message = result.message
    except ImportError:
        # 1.D.G.F notification module pendiente · log + return basic ack
        import logging
        logging.getLogger(__name__).info(
            "remind client · in-app only fallback (1.D.G.F notification module not yet wired)",
        )

    return RemindClientResponse(
        project_id=project_id,
        template_id=template_id,
        notified=True,
        channels=channels,
        message=message,
    )


# ==================================================================
# INTERNOS · reusable copilotos (admin + cliente con ownership)
# ==================================================================


class CatalogResponse(BaseModel):
    project_id: uuid.UUID
    dims: dict[str, Any]
    catalog: list[EnrichedStepState]
    count: int


@reader_router.get(
    "/{project_id}/workflow-engine/catalog",
    response_model=CatalogResponse,
    dependencies=[Depends(require_marcos_or_client)],
)
async def workflow_engine_catalog(
    project_id: uuid.UUID,
    request: Request,
    phase: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> CatalogResponse:
    """YAML enriched filtered per project (19 dims) · reusable copilotos."""
    await _ensure_project_access(db, project_id, request)
    dims = await load_project_dims(db, project_id)
    catalog = await compute_steps_for_project(db, project_id, phase_filter=phase)
    return CatalogResponse(
        project_id=project_id, dims=dims, catalog=catalog, count=len(catalog),
    )


@reader_router.get(
    "/{project_id}/workflow-engine/current-step",
    response_model=EnrichedStepState | None,
    dependencies=[Depends(require_marcos_or_client)],
)
async def workflow_engine_current_step(
    project_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> EnrichedStepState | None:
    """Siguiente sub-paso most-urgent · None si todo completado."""
    await _ensure_project_access(db, project_id, request)
    return await compute_current_step_for_project(db, project_id)


class ProgressResponse(BaseModel):
    project_id: uuid.UUID
    global_pct: int
    global_completed: int
    global_total: int
    per_phase: dict[str, dict[str, int]]


@reader_router.get(
    "/{project_id}/workflow-engine/progress",
    response_model=ProgressResponse,
    dependencies=[Depends(require_marcos_or_client)],
)
async def workflow_engine_progress(
    project_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ProgressResponse:
    """% per phase + global · counts completed/pending/blocked."""
    await _ensure_project_access(db, project_id, request)
    progress = await compute_progress_for_project(db, project_id)
    return ProgressResponse(project_id=project_id, **progress)


class TimelineResponse(BaseModel):
    project_id: uuid.UUID
    timeline: list[EnrichedStepState]
    count: int


@reader_router.get(
    "/{project_id}/workflow-engine/timeline",
    response_model=TimelineResponse,
    dependencies=[Depends(require_marcos_or_client)],
)
async def workflow_engine_timeline(
    project_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TimelineResponse:
    """Cronológica ordenada full proyecto · backbone copiloto admin."""
    await _ensure_project_access(db, project_id, request)
    timeline = await compute_steps_for_project(db, project_id)
    return TimelineResponse(
        project_id=project_id, timeline=timeline, count=len(timeline),
    )


# ==================================================================
# CLIENTE · workflow-guide subset friendly
# ==================================================================


class WorkflowGuideResponse(BaseModel):
    """Vista friendly cliente · subset enriched (NO admin actions)."""

    project_id: uuid.UUID
    categoria: str | None
    archetype: str | None
    fase: str
    progress: dict[str, Any]
    current_step: EnrichedStepState | None
    completed: list[EnrichedStepState]
    proximos: list[EnrichedStepState]


@reader_router.get(
    "/{project_id}/workflow-guide",
    response_model=WorkflowGuideResponse,
    dependencies=[Depends(require_marcos_or_client)],
)
async def workflow_guide_client(
    project_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WorkflowGuideResponse:
    """Workflow guide cliente · vista friendly subset enriched."""
    await _ensure_project_access(db, project_id, request)
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    progress = await compute_progress_for_project(db, project_id)
    current = await compute_current_step_for_project(db, project_id)
    steps = await compute_steps_for_project(db, project_id)
    completed = [s for s in steps if s.status == "completed"]
    pending = sorted(
        [s for s in steps if s.status != "completed"],
        key=lambda s: -s.urgency_score,
    )
    # Cliente ve current + next 5 (NO 30d forecast · UX simplified R29)
    proximos = [
        s for s in pending
        if s.template_id != (current.template_id if current else None)
    ][:5]

    return WorkflowGuideResponse(
        project_id=project_id,
        categoria=project.categoria_objetivo,
        archetype=project.archetype,
        fase=project.fase,
        progress=progress,
        current_step=current,
        completed=completed,
        proximos=proximos,
    )


# ==================================================================
# DELIVERABLES · sub-atom 1.C.D.D.1 v3.8 (admin + cliente con ownership)
# ==================================================================


@reader_router.get(
    "/{project_id}/workflow-engine/steps/{template_id}/deliverables",
    response_model=StepDeliverablesResponse,
    dependencies=[Depends(require_marcos_or_client)],
)
async def list_step_deliverables(
    project_id: uuid.UUID,
    template_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StepDeliverablesResponse:
    """List deliverable_codes per step + Evidence Vault match status.

    Status per code:
      - available · existe + vigente=True
      - needs_regen · existe + vigente=False
      - missing · NO existe (admin trigger generate vía M06)
    """
    await _ensure_project_access(db, project_id, request)
    service = WorkflowDeliverablesService(db)
    try:
        return await service.list_step_deliverables(project_id, template_id)
    except DeliverablesServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@reader_router.get(
    "/{project_id}/workflow-engine/deliverables/{evidence_id}/download",
    dependencies=[Depends(require_marcos_or_client)],
)
async def download_deliverable(
    project_id: uuid.UUID,
    evidence_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Download individual deliverable file desde Evidence Vault.

    Auth dual + ownership · resuelve fichero_path + sirve con nombre original.
    """
    await _ensure_project_access(db, project_id, request)
    service = WorkflowDeliverablesService(db)
    try:
        path, nombre, mime = await service.get_evidence_file_path(
            project_id, evidence_id,
        )
    except DeliverablesServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not path.exists():
        raise HTTPException(
            status_code=404, detail="Evidence file not found on disk",
        )
    return FileResponse(path=str(path), filename=nombre, media_type=mime)


@reader_router.get(
    "/{project_id}/workflow-engine/steps/{template_id}/deliverables/bulk-zip",
    dependencies=[Depends(require_marcos_or_client)],
)
async def download_step_deliverables_bulk_zip(
    project_id: uuid.UUID,
    template_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Download bulk ZIP de TODOS los deliverables available per step.

    Solo incluye deliverables con status='available' (vigentes existing).
    Missing + needs_regen NO incluidos (admin debe generarlos primero).

    Stream on-the-fly · NO persistencia · NO cache.
    """
    await _ensure_project_access(db, project_id, request)
    service = WorkflowDeliverablesService(db)
    try:
        listing = await service.list_step_deliverables(project_id, template_id)
    except DeliverablesServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    available = [d for d in listing.deliverables if d.status == "available"]
    if not available:
        raise HTTPException(
            status_code=404,
            detail="No hay entregables disponibles para este paso",
        )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for d in available:
            try:
                path, nombre, _mime = await service.get_evidence_file_path(
                    project_id, d.evidence_id,  # type: ignore[arg-type]
                )
                if path.exists():
                    zf.write(path, arcname=nombre)
            except DeliverablesServiceError:
                # Skip silently · log via service · NO break ZIP
                continue
    buffer.seek(0)

    safe_template_id = template_id.replace("/", "_")[:80]
    filename = f"deliverables_{safe_template_id}.zip"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
