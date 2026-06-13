"""API REST · m_remediation (ADR-055).

Admin (require_owner · project-scoped):
  GET    /admin/projects/{pid}/remediation/catalog          acciones catalogadas
  GET    /admin/projects/{pid}/remediation/jobs             lista (?status=)
  POST   /admin/projects/{pid}/remediation/jobs             crea job
  GET    /admin/projects/{pid}/remediation/jobs/{jid}       detalle
  POST   /admin/projects/{pid}/remediation/jobs/{jid}/authorize
  POST   /admin/projects/{pid}/remediation/jobs/{jid}/execute

Cliente (require_client_user · ADR-013 · READ + AUTORIZAR · cliente-mínimo):
  GET    /client-portal/remediation/jobs                    lista (R29 friendly)
  POST   /client-portal/remediation/jobs/{jid}/authorize    autoriza GUARDED

Cliente NO crea ni ejecuta: solo VE y AUTORIZA cambios de riesgo en SUS sistemas
(filosofía cliente-mínimo · ADR-014 carve-out controlado).
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_client_user, require_owner
from backend.app.core.audit_writer import emit_audit_log
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m_cloud_connectors.models import CloudConnector
from backend.app.motors.m_remediation.catalog import (
    ACTION_CATALOG,
    actions_for_provider,
    get_action_spec,
)
from backend.app.motors.m_remediation.policy import AutoRemediationPolicy
from backend.app.motors.m_remediation.models import RemediationJob
from backend.app.motors.m_remediation.service import (
    AuthorizationRequiredError,
    InvalidJobTransitionError,
    JobNotFoundError,
    RemediationDisabledError,
    RemediationService,
    RemediationServiceError,
)

admin_router = APIRouter(
    prefix="/admin/projects/{project_id}/remediation",
    tags=["Remediación (ADR-055) · Admin"],
    dependencies=[Depends(require_owner)],
)

client_router = APIRouter(
    prefix="/client-portal/remediation",
    tags=["Remediación (ADR-055) · Cliente"],
    dependencies=[Depends(require_client_user)],
)


# ── request bodies ────────────────────────────────────────────────────────


class CreateJobBody(BaseModel):
    action_type: str = Field(..., min_length=2, max_length=80)
    source_kind: str = Field(default="cloud_gap")
    source_gap_id: uuid.UUID | None = None
    source_finding_id: uuid.UUID | None = None
    connector_id: uuid.UUID | None = None
    target_ref: str | None = Field(default=None, max_length=255)
    params: dict | None = None
    dry_run: bool = False


class ConnectorActivationBody(BaseModel):
    enabled: bool
    policy: str = Field(default="full")  # off | safe_auto_only | full


_VALID_POLICIES = {p.value for p in AutoRemediationPolicy}


# ── helpers ─────────────────────────────────────────────────────────────────


async def _set_project_context(db: AsyncSession, project_id: uuid.UUID) -> None:
    cid = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    if not cid:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    await set_tenant_context(db, project_id=project_id)


async def _resolve_cliente_project(db: AsyncSession, cliente_user) -> uuid.UUID:
    cliente_client_id = getattr(cliente_user, "client_id", None)
    if cliente_client_id is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    row = await db.execute(
        text(
            "SELECT id FROM projects WHERE client_id = :cid AND deleted_at IS NULL "
            "ORDER BY created_at ASC LIMIT 1"
        ),
        {"cid": str(cliente_client_id)},
    )
    pid = row.scalar()
    if pid is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    await set_tenant_context(db, project_id=pid)
    return pid if isinstance(pid, uuid.UUID) else uuid.UUID(str(pid))


def _job_to_dict(job: RemediationJob) -> dict[str, Any]:
    spec = get_action_spec(job.action_type)
    return {
        "id": str(job.id),
        "project_id": str(job.project_id),
        "action_type": job.action_type,
        "title": spec.title_es if spec else job.action_type,
        "tier": job.tier,
        "status": job.status,
        "source_kind": job.source_kind,
        "source_gap_id": str(job.source_gap_id) if job.source_gap_id else None,
        "connector_id": str(job.connector_id) if job.connector_id else None,
        "target_ref": job.target_ref,
        "dry_run": job.dry_run,
        "ens_measures": list(spec.ens_measures) if spec else [],
        "authorized_at": job.authorized_at.isoformat() if job.authorized_at else None,
        "error_message": job.error_message,
        "result": job.result,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


# Etiquetas de estado amistosas R29 (sin jerga admin · cliente-friendly).
_CLIENTE_STATUS_LABEL: dict[str, str] = {
    "queued": "En cola",
    "awaiting_authorization": "Esperando tu autorización",
    "blocked": "Requiere revisión manual",
    "preflight": "Comprobando",
    "snapshotting": "Guardando copia de seguridad",
    "applying": "Aplicando la mejora",
    "verifying": "Verificando",
    "succeeded": "Resuelto · tu sistema está más seguro",
    "skipped_compliant": "Ya estaba correcto",
    "failed": "Lo estamos revisando",
    "rolled_back": "Revertido sin cambios · lo estamos revisando",
}


def _job_to_cliente_dict(job: RemediationJob) -> dict[str, Any]:
    """Vista R29 friendly · sin internals admin · con blurb del catálogo."""
    spec = get_action_spec(job.action_type)
    return {
        "id": str(job.id),
        "title": spec.title_es if spec else "Mejora de seguridad",
        "explicacion": spec.cliente_blurb if spec else None,
        "tier": job.tier,
        "necesita_autorizacion": job.status == "awaiting_authorization",
        "estado": _CLIENTE_STATUS_LABEL.get(job.status, "En proceso"),
        "fecha": job.created_at.isoformat() if job.created_at else None,
    }


# ── admin endpoints ─────────────────────────────────────────────────────────


@admin_router.get("/catalog", status_code=200)
async def admin_catalog(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Catálogo de acciones (R30 tutor · admin elige qué remediar)."""
    return {
        "actions": [
            {
                "action_type": s.action_type,
                "title": s.title_es,
                "tier": s.tier.value,
                "reversible": s.reversible,
                "provider": s.provider,
                "ens_measures": list(s.ens_measures),
                "cliente_blurb": s.cliente_blurb,
                "requires_write_scopes": list(s.requires_write_scopes),
            }
            for s in ACTION_CATALOG.values()
        ],
    }


@admin_router.get("/jobs", status_code=200)
async def admin_list_jobs(
    project_id: uuid.UUID,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_context(db, project_id)
    svc = RemediationService(db)
    jobs = await svc.list_jobs(project_id, status=status)
    return {"jobs": [_job_to_dict(j) for j in jobs]}


@admin_router.post("/jobs", status_code=201)
async def admin_create_job(
    project_id: uuid.UUID,
    body: CreateJobBody,
    user=Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_context(db, project_id)
    svc = RemediationService(db)
    try:
        job = await svc.create_job(
            project_id=project_id,
            action_type=body.action_type,
            source_kind=body.source_kind,
            source_gap_id=body.source_gap_id,
            source_finding_id=body.source_finding_id,
            connector_id=body.connector_id,
            target_ref=body.target_ref,
            params=body.params,
            dry_run=body.dry_run,
            created_by_user_id=getattr(user, "id", None),
        )
    except RemediationServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _job_to_dict(job)


@admin_router.get("/jobs/{job_id}", status_code=200)
async def admin_get_job(
    project_id: uuid.UUID,
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_context(db, project_id)
    svc = RemediationService(db)
    try:
        job = await svc.get_job(job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return _job_to_dict(job)


@admin_router.post("/jobs/{job_id}/authorize", status_code=200)
async def admin_authorize_job(
    project_id: uuid.UUID,
    job_id: uuid.UUID,
    user=Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_context(db, project_id)
    svc = RemediationService(db)
    try:
        job = await svc.authorize_job(job_id, user_id=getattr(user, "id", None))
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    except InvalidJobTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return _job_to_dict(job)


@admin_router.post("/jobs/{job_id}/execute", status_code=200)
async def admin_execute_job(
    project_id: uuid.UUID,
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Dispara el ciclo seguro (usa el writer registrado opt-in del proveedor).

    Sin writer registrado → el job termina FAILED explícito (default seguro · la
    escritura es opt-in y requiere scopes concedidos por el cliente).
    """
    await _set_project_context(db, project_id)
    svc = RemediationService(db)
    try:
        job = await svc.execute_job(job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    except AuthorizationRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except RemediationDisabledError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return _job_to_dict(job)


# ── admin · activación por conector (botones) ────────────────────────────────


def _connector_to_dict(c: CloudConnector) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "provider": c.provider,
        "status": c.status,
        "remediation_enabled": bool(c.remediation_enabled),
        "auto_remediation_policy": c.auto_remediation_policy,
        "granted_write_scopes": c.granted_write_scopes,
    }


@admin_router.get("/connectors", status_code=200)
async def admin_list_connectors(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Conectores del proyecto + su estado de remediación (para los toggles)."""
    await _set_project_context(db, project_id)
    from sqlalchemy import select

    res = await db.execute(
        select(CloudConnector).where(
            CloudConnector.project_id == project_id,
            CloudConnector.deleted_at.is_(None),
        )
    )
    return {"connectors": [_connector_to_dict(c) for c in res.scalars().all()]}


@admin_router.patch("/connectors/{connector_id}/activation", status_code=200)
async def admin_set_connector_activation(
    project_id: uuid.UUID,
    connector_id: uuid.UUID,
    body: ConnectorActivationBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Activa/desactiva la remediación de un conector + fija la política (botón)."""
    await _set_project_context(db, project_id)
    if body.policy not in _VALID_POLICIES:
        raise HTTPException(status_code=400, detail=f"Política inválida: {body.policy}")
    connector = await db.get(CloudConnector, connector_id)
    if connector is None or connector.project_id != project_id:
        raise HTTPException(status_code=404, detail="Conector no encontrado")
    connector.remediation_enabled = body.enabled
    connector.auto_remediation_policy = body.policy
    await emit_audit_log(
        db, tabla="cloud_connectors", registro_id=connector.id,
        accion="remediation.connector.activation", project_id=project_id,
        payload_new={"enabled": body.enabled, "policy": body.policy},
    )
    await db.commit()
    return _connector_to_dict(connector)


@admin_router.post("/connectors/{connector_id}/grant-write", status_code=200)
async def admin_grant_write(
    project_id: uuid.UUID,
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Registra el consentimiento de escritura del cliente + activa el conector.

    Devuelve los scopes requeridos + las instrucciones de consentimiento del
    proveedor. El admin del cliente debe conceder esos permisos en SU plataforma
    (pantalla de consentimiento Microsoft/Google o policy IAM en AWS · OAuth lo
    exige · no se puede auto-aprobar por nosotros).
    """
    await _set_project_context(db, project_id)
    connector = await db.get(CloudConnector, connector_id)
    if connector is None or connector.project_id != project_id:
        raise HTTPException(status_code=404, detail="Conector no encontrado")

    scopes = sorted({
        s for action in actions_for_provider(connector.provider)
        for s in action.requires_write_scopes
    })
    instructions = _CONSENT_INSTRUCTIONS.get(
        connector.provider, "Conceda permisos de escritura acotados al proveedor.",
    )
    connector.granted_write_scopes = {"scopes": scopes, "granted": True}
    connector.remediation_enabled = True
    if connector.auto_remediation_policy in (None, "off"):
        connector.auto_remediation_policy = AutoRemediationPolicy.FULL.value
    await emit_audit_log(
        db, tabla="cloud_connectors", registro_id=connector.id,
        accion="remediation.connector.grant_write", project_id=project_id,
        payload_new={"scopes": scopes, "provider": connector.provider},
    )
    await db.commit()
    return {
        "connector": _connector_to_dict(connector),
        "required_scopes": scopes,
        "instructions": instructions,
    }


_CONSENT_INSTRUCTIONS: dict[str, str] = {
    "aws": (
        "En la consola IAM del cliente, adjunta al rol que asume FULKRO una "
        "policy con los permisos de escritura listados (S3/IAM/CloudTrail)."
    ),
    "microsoft_365": (
        "El Global Admin del cliente debe conceder consentimiento de "
        "administrador a la app de FULKRO para los permisos Graph listados "
        "(Policy.ReadWrite.ConditionalAccess) en la pantalla oficial de Microsoft."
    ),
    "azure": (
        "Asigna al Service Principal de FULKRO el rol con permisos de escritura "
        "sobre los recursos (p.ej. Storage Account Contributor) en el portal Azure."
    ),
    "google_workspace": (
        "En la consola de administración de Google, añade a la cuenta de servicio "
        "de FULKRO la delegación de dominio para el scope de Drive listado."
    ),
}


# ── cliente endpoints (READ + AUTORIZAR) ────────────────────────────────────


@client_router.get("/jobs", status_code=200)
async def cliente_list_jobs(
    cliente_user=Depends(require_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project_id = await _resolve_cliente_project(db, cliente_user)
    svc = RemediationService(db)
    jobs = await svc.list_jobs(project_id)
    # Cliente solo ve acciones que le conciernen (no internals técnicos).
    return {"jobs": [_job_to_cliente_dict(j) for j in jobs]}


@client_router.post("/jobs/{job_id}/authorize", status_code=200)
async def cliente_authorize_job(
    job_id: uuid.UUID,
    cliente_user=Depends(require_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """El cliente AUTORIZA un cambio de riesgo en SU sistema (tier GUARDED).

    RLS aísla por proyecto del cliente: un job de otro proyecto no es visible (404).
    """
    await _resolve_cliente_project(db, cliente_user)
    svc = RemediationService(db)
    try:
        job = await svc.authorize_job(
            job_id, user_id=getattr(cliente_user, "id", None),
        )
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="No encontrado")
    except InvalidJobTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return _job_to_cliente_dict(job)
