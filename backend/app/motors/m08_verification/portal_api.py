"""Motor 8 — Verification · cliente in-portal pentest authorization API · SAN-E v3.MB-5.5.

ADR-020 v6 Q5.3: cliente revisa scope + ventana + plan + IR + compromisos in-portal,
luego firma autorizacion ventana pentest (OTP step-up).

Pattern atom 5.3.A / 5.4.A sostenido: extender tabla existing (VerificationRun)
y exponer portal_api. Audit-driven adaptation L99: motor real es m08_verification,
plan original asumia m08_pentest inexistente. VerificationRun semantic =
pentest authorization.

URL publico mantiene /portal/pentest/... (cliente NO conoce motor verification
internamente · decoupling correcto).

Sub-atom 5.5.B endpoints:
- GET  /portal/pentest/projects/{project_id}/authorization (cliente VE richer)
- POST /portal/pentest/projects/{project_id}/authorization/mark-reviewed
- GET  /portal/pentest/projects/{project_id}/authorization/document-hash

Auth: ClientUser via cookie + CSRF triple binding (alineado m03/m02 portales).
RLS: verification_runs enforce project_id · _ensure_project_belongs_to_client.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m08_verification.models import VerificationRun
from backend.app.motors.m21_portal_cliente.api import get_current_client_user


router = APIRouter(
    prefix="/portal/pentest",
    tags=["Motor 08 - Pentest cliente in-portal"],
)


# ====================================================================
# Schemas
# ====================================================================


class ScopeTarget(BaseModel):
    """Target individual dentro del scope pentest (extraido de scope_jsonb)."""

    target_url: str
    target_type: str  # 'web_app' | 'api' | 'mobile' | 'network'
    notes: str | None = None


class PentestAuthorizationClientView(BaseModel):
    """Cliente view de autorizacion pentest (VerificationRun semantic).

    Mapea desde VerificationRun (single source of truth):
    - scope_jsonb (existing) → scope_* fields
    - scheduled_start (existing) → ventana_inicio (reuse · NO duplicar)
    - tools_config (existing) → plan_tools subset
    - authorization_signed_at (existing) → admin_authorized_at
    - cliente review fields NEW migration fc8ad935f6f6
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    verification_run_id: uuid.UUID

    # Scope (desde scope_jsonb · admin pre-set · cliente VE)
    scope_summary: str
    scope_targets: list[ScopeTarget]
    scope_exclusions: list[str]
    scope_credentials_provided: bool
    scope_data_classification: str

    # Ventana (inicio = scheduled_start existing · fin/tz/bh NEW)
    ventana_inicio: datetime | None
    ventana_fin: datetime | None
    ventana_timezone: str
    ventana_business_hours_only: bool

    # Plan tests
    plan_test_categorias: list[str]
    plan_test_intensity: str
    plan_test_estimated_hours: int
    plan_tools: list[str]

    # Contacto IR (admin pre-set)
    contacto_ir_nombre: str
    contacto_ir_email: str
    contacto_ir_telefono: str
    contacto_ir_horario: str

    # Compromiso FULKRO (admin pre-set)
    rules_of_engagement: str
    responsibility_disclosure: str
    data_handling_policy: str

    # Admin authorization (existing fields)
    admin_authorized_at: datetime | None
    admin_authorized_by: str | None

    # Cliente review/sign state (NEW)
    client_reviewed_at: datetime | None
    client_reviewed_by_user_id: uuid.UUID | None
    client_concerns_note: str | None
    client_signing_intent_id: uuid.UUID | None

    # Computed from signing_events (pattern MAGERIT)
    last_signed_at: datetime | None

    last_modified_at: datetime | None


class MarkReviewedRequest(BaseModel):
    """Cliente confirma review · optional concerns note (NO bloquea authorize)."""

    concerns_note: str | None = Field(None, max_length=4000)


class PentestDocumentHashResponse(BaseModel):
    """SHA256 deterministic state autorizacion · pre-firma."""

    document_hash_sha256: str
    canonical_length: int
    verification_run_id: uuid.UUID
    last_modified_at: datetime | None
    ready_for_authorization: bool


# ====================================================================
# Helpers
# ====================================================================


async def _ensure_project_belongs_to_client(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: ClientUser,
) -> None:
    """Verify project ownership + sets tenant context for RLS."""
    row = await db.execute(
        sa_text("SELECT client_id FROM projects WHERE id = :pid"),
        {"pid": str(project_id)},
    )
    hit = row.first()
    if hit is None:
        raise HTTPException(status_code=404, detail="Project no existe")
    if hit[0] != user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project no pertenece al cliente del usuario",
        )
    await set_tenant_context(
        db, client_id=user.client_id, project_id=project_id,
    )


async def _get_active_verification_run(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> VerificationRun | None:
    """Latest VerificationRun for project (pentest authorization pending cliente)."""
    row = await db.execute(
        select(VerificationRun)
        .where(VerificationRun.project_id == project_id)
        .where(VerificationRun.deleted_at.is_(None))
        .order_by(VerificationRun.created_at.desc())
        .limit(1)
    )
    return row.scalar_one_or_none()


def _to_client_authorization_view(
    run: VerificationRun,
    last_signed_at: datetime | None = None,
) -> PentestAuthorizationClientView:
    """DRY: VerificationRun ORM → cliente view richer.

    Pattern atom 5.3.E sostenido · richer detail in single object.
    """
    scope = run.scope_jsonb or {}
    tools_cfg = run.tools_config or {}

    targets_raw = scope.get("targets") or []
    targets: list[ScopeTarget] = []
    for t in targets_raw:
        if isinstance(t, dict):
            targets.append(
                ScopeTarget(
                    target_url=str(t.get("target_url", "")),
                    target_type=str(t.get("target_type", "web_app")),
                    notes=t.get("notes"),
                )
            )

    return PentestAuthorizationClientView(
        id=run.id,
        project_id=run.project_id,
        verification_run_id=run.id,

        scope_summary=str(scope.get("summary", "")),
        scope_targets=targets,
        scope_exclusions=list(scope.get("exclusions") or []),
        scope_credentials_provided=bool(scope.get("credentials_provided", False)),
        scope_data_classification=str(scope.get("data_classification", "staging")),

        ventana_inicio=run.scheduled_start,
        ventana_fin=run.ventana_fin,
        ventana_timezone=run.ventana_timezone or "Europe/Madrid",
        ventana_business_hours_only=bool(run.ventana_business_hours_only),

        plan_test_categorias=list(run.plan_test_categorias or []),
        plan_test_intensity=run.plan_test_intensity or "medium",
        plan_test_estimated_hours=int(run.plan_test_estimated_hours or 0),
        plan_tools=list(tools_cfg.get("tools") or []),

        contacto_ir_nombre=run.contacto_ir_nombre or "",
        contacto_ir_email=run.contacto_ir_email or "",
        contacto_ir_telefono=run.contacto_ir_telefono or "",
        contacto_ir_horario=run.contacto_ir_horario or "",

        rules_of_engagement=run.rules_of_engagement or "",
        responsibility_disclosure=run.responsibility_disclosure or "",
        data_handling_policy=run.data_handling_policy or "",

        admin_authorized_at=run.authorization_signed_at,
        admin_authorized_by=run.authorized_by,

        client_reviewed_at=run.client_reviewed_at,
        client_reviewed_by_user_id=run.client_reviewed_by_user_id,
        client_concerns_note=run.client_concerns_note,
        client_signing_intent_id=run.client_signing_intent_id,

        last_signed_at=last_signed_at,

        last_modified_at=run.updated_at,
    )


async def _get_last_pentest_signed_at(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> datetime | None:
    """Compute MAX signing_events.created_at for pentest_authorization
    signature_generated · pattern MAGERIT summary.
    """
    row = await db.execute(
        sa_text(
            "SELECT MAX(se.created_at) FROM signing_events se "
            "JOIN signing_intents si ON si.id = se.signing_intent_id "
            "WHERE si.project_id = :pid AND si.signable_type = "
            "'pentest_authorization' AND se.event_type = 'signature_generated'"
        ),
        {"pid": str(project_id)},
    )
    return row.scalar_one_or_none()


# ====================================================================
# Endpoints
# ====================================================================


@router.get(
    "/projects/{project_id}/authorization",
    response_model=PentestAuthorizationClientView,
)
async def get_pentest_authorization(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> PentestAuthorizationClientView:
    """Cliente VE autorizacion pentest pendiente firma."""
    await _ensure_project_belongs_to_client(db, project_id, user)
    run = await _get_active_verification_run(db, project_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No hay autorizacion pentest pendiente. "
                "Marcos debe configurar verification_run primero."
            ),
        )
    if run.authorization_signed_at is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Autorizacion pendiente firma admin. "
                "Marcos debe completar autorizacion interna primero."
            ),
        )
    last_signed_at = await _get_last_pentest_signed_at(db, project_id)
    return _to_client_authorization_view(run, last_signed_at=last_signed_at)


@router.post(
    "/projects/{project_id}/authorization/mark-reviewed",
    response_model=PentestAuthorizationClientView,
)
async def mark_pentest_authorization_reviewed(
    project_id: uuid.UUID,
    body: MarkReviewedRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> PentestAuthorizationClientView:
    """Cliente confirma review scope + ventana + plan + IR.

    Persiste client_reviewed_at + reviewed_by + concerns_note.
    NO firma aun · firma viene via signing_intent (sub-atom 5.5.D).
    """
    await _ensure_project_belongs_to_client(db, project_id, user)
    run = await _get_active_verification_run(db, project_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail="No hay autorizacion pentest pendiente",
        )
    if run.authorization_signed_at is None:
        raise HTTPException(
            status_code=409,
            detail="Autorizacion pendiente firma admin",
        )

    run.client_reviewed_at = datetime.now(UTC)
    run.client_reviewed_by_user_id = user.id
    if body.concerns_note is not None:
        run.client_concerns_note = body.concerns_note
    await db.flush()
    # Construir la vista ANTES del commit (bug commit-RLS · auditoría 2026-06-07):
    # db.commit() resetea el GUC is_local del RLS cliente → un db.refresh/query
    # posterior consultaría SIN contexto de tenant y fallaría 500 ("Could not
    # refresh instance"). El run ya tiene los campos en memoria tras el flush.
    last_signed_at = await _get_last_pentest_signed_at(db, project_id)
    view = _to_client_authorization_view(run, last_signed_at=last_signed_at)
    await db.commit()
    return view


@router.get(
    "/projects/{project_id}/authorization/document-hash",
    response_model=PentestDocumentHashResponse,
)
async def get_pentest_document_hash(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> PentestDocumentHashResponse:
    """SHA256 determinista state autorizacion pre-firma.

    Hash incluye scope + ventana + plan + IR + cliente review state.
    ready_for_authorization gate · cliente MUST mark-reviewed primero.
    """
    await _ensure_project_belongs_to_client(db, project_id, user)
    run = await _get_active_verification_run(db, project_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail="No hay autorizacion pentest pendiente",
        )
    if run.authorization_signed_at is None:
        raise HTTPException(
            status_code=409,
            detail="Autorizacion pendiente firma admin",
        )

    scope = run.scope_jsonb or {}
    canonical_parts: list[str] = [
        f"project_id:{project_id}",
        f"verification_run_id:{run.id}",
        f"scope_summary:{scope.get('summary', '')}",
        f"scope_targets:{json.dumps(scope.get('targets') or [], sort_keys=True)}",
        f"scope_exclusions:{json.dumps(scope.get('exclusions') or [], sort_keys=True)}",
        f"data_classification:{scope.get('data_classification', 'staging')}",
        f"ventana_inicio:{run.scheduled_start.isoformat() if run.scheduled_start else 'tbd'}",
        f"ventana_fin:{run.ventana_fin.isoformat() if run.ventana_fin else 'tbd'}",
        f"ventana_tz:{run.ventana_timezone or 'Europe/Madrid'}",
        f"plan_categorias:{json.dumps(list(run.plan_test_categorias or []), sort_keys=True)}",
        f"plan_intensity:{run.plan_test_intensity or 'medium'}",
        f"plan_estimated_hours:{int(run.plan_test_estimated_hours or 0)}",
        f"contacto_ir_email:{run.contacto_ir_email or ''}",
        f"admin_signed:{run.authorization_signed_at.isoformat() if run.authorization_signed_at else 'pending'}",
        f"client_reviewed:{run.client_reviewed_at.isoformat() if run.client_reviewed_at else 'pending'}",
    ]
    canonical = "\n".join(canonical_parts)
    document_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return PentestDocumentHashResponse(
        document_hash_sha256=document_hash,
        canonical_length=len(canonical),
        verification_run_id=run.id,
        last_modified_at=run.updated_at,
        ready_for_authorization=run.client_reviewed_at is not None,
    )
