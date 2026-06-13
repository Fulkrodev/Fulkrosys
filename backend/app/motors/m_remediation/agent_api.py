"""API del agente on-prem · m_remediation (ADR-055 Fase 3).

Admin (require_owner · project-scoped):
  POST   /admin/projects/{pid}/remediation/agents              emite enrollment
  GET    /admin/projects/{pid}/remediation/agents              lista agentes
  POST   /admin/projects/{pid}/remediation/agents/{aid}/revoke kill-switch
  POST   /admin/projects/{pid}/remediation/agents/{aid}/commands  encola (body job_id)

Agente (auth por token · SIN require_owner · el token ES la auth):
  POST   /agent/remediation/enroll                  canjea token de un solo uso
  GET    /agent/remediation/commands                pull comandos firmados (Bearer)
  POST   /agent/remediation/commands/{cid}/report   reporta resultado firmado (Bearer)
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m_remediation.agent_service import (
    AgentAuthError,
    AgentServiceError,
    EnrollmentError,
    RemediationAgentService,
)
from backend.app.motors.m_remediation.service import (
    AuthorizationRequiredError,
    JobNotFoundError,
    RemediationDisabledError,
    RemediationService,
)

admin_router = APIRouter(
    prefix="/admin/projects/{project_id}/remediation/agents",
    tags=["Remediación Agente (ADR-055) · Admin"],
    dependencies=[Depends(require_owner)],
)

agent_router = APIRouter(
    prefix="/agent/remediation",
    tags=["Remediación Agente (ADR-055) · Agente"],
)


# ── bodies ──────────────────────────────────────────────────────────────────


class IssueEnrollmentBody(BaseModel):
    hostname: str = Field(..., min_length=1, max_length=255)
    ttl_minutes: int = Field(default=60, ge=5, le=1440)


class EnqueueCommandBody(BaseModel):
    job_id: uuid.UUID


class EnrollBody(BaseModel):
    token: str = Field(..., min_length=10, max_length=200)
    agent_pubkey_hex: str = Field(..., min_length=64, max_length=64)
    agent_version: str | None = Field(default=None, max_length=40)


class ReportBody(BaseModel):
    result: dict[str, Any]
    report_signature: str = Field(..., min_length=16, max_length=256)


# ── helpers ──────────────────────────────────────────────────────────────────


async def _set_project_context(db: AsyncSession, project_id: uuid.UUID) -> None:
    cid = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    if not cid:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    await set_tenant_context(db, project_id=project_id)


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Falta token de agente")
    return authorization.split(" ", 1)[1].strip()


def _agent_to_dict(agent) -> dict[str, Any]:
    return {
        "id": str(agent.id),
        "hostname": agent.hostname,
        "status": agent.status,
        "agent_version": agent.agent_version,
        "capabilities": agent.capabilities,
        "enrolled_at": agent.enrolled_at.isoformat() if agent.enrolled_at else None,
        "last_heartbeat_at": (
            agent.last_heartbeat_at.isoformat() if agent.last_heartbeat_at else None
        ),
        "revoked_at": agent.revoked_at.isoformat() if agent.revoked_at else None,
    }


# ── admin ────────────────────────────────────────────────────────────────────


@admin_router.post("", status_code=201)
async def admin_issue_enrollment(
    project_id: uuid.UUID,
    body: IssueEnrollmentBody,
    user=Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_context(db, project_id)
    svc = RemediationAgentService(db)
    agent, token = await svc.issue_enrollment(
        project_id=project_id,
        hostname=body.hostname,
        created_by_user_id=getattr(user, "id", None),
        ttl_minutes=body.ttl_minutes,
    )
    await db.commit()
    # El token solo se muestra UNA vez (no se vuelve a poder leer).
    return {
        "agent_id": str(agent.id),
        "enrollment_token": token,
        "expires_at": (
            agent.enrollment_expires_at.isoformat()
            if agent.enrollment_expires_at else None
        ),
        "hostname": agent.hostname,
    }


@admin_router.get("", status_code=200)
async def admin_list_agents(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_context(db, project_id)
    svc = RemediationAgentService(db)
    agents = await svc.list_agents(project_id)
    return {"agents": [_agent_to_dict(a) for a in agents]}


@admin_router.post("/{agent_id}/revoke", status_code=200)
async def admin_revoke_agent(
    project_id: uuid.UUID,
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_context(db, project_id)
    svc = RemediationAgentService(db)
    try:
        agent = await svc.revoke_agent(agent_id)
    except AgentServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return _agent_to_dict(agent)


@admin_router.post("/{agent_id}/commands", status_code=201)
async def admin_enqueue_command(
    project_id: uuid.UUID,
    agent_id: uuid.UUID,
    body: EnqueueCommandBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_context(db, project_id)
    agent_svc = RemediationAgentService(db)
    rem_svc = RemediationService(db)
    agents = await agent_svc.list_agents(project_id)
    agent = next((a for a in agents if a.id == agent_id), None)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    try:
        job = await rem_svc.get_job(body.job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    try:
        cmd = await agent_svc.enqueue_command(agent=agent, job=job)
    except (RemediationDisabledError, AuthorizationRequiredError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except AgentServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return {"command_id": str(cmd.id), "status": cmd.status}


# ── agente (auth por token) ───────────────────────────────────────────────────


@agent_router.post("/enroll", status_code=200)
async def agent_enroll(
    body: EnrollBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    svc = RemediationAgentService(db)
    try:
        agent, agent_token, server_pubkey = await svc.redeem_enrollment(
            token=body.token,
            agent_pubkey_hex=body.agent_pubkey_hex,
            agent_version=body.agent_version,
        )
    except EnrollmentError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    await db.commit()
    return {
        "agent_id": str(agent.id),
        "agent_token": agent_token,
        "server_pubkey_hex": server_pubkey,
        "capabilities": agent.capabilities,
    }


@agent_router.get("/commands", status_code=200)
async def agent_poll_commands(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    svc = RemediationAgentService(db)
    try:
        agent = await svc.authenticate_agent(_bearer(authorization))
        commands = await svc.poll_commands(agent)
    except AgentAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    await db.commit()
    return {"commands": commands}


@agent_router.post("/commands/{command_id}/report", status_code=200)
async def agent_report_command(
    command_id: uuid.UUID,
    body: ReportBody,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    svc = RemediationAgentService(db)
    try:
        agent = await svc.authenticate_agent(_bearer(authorization))
        cmd = await svc.report_command(
            agent=agent,
            command_id=command_id,
            result=body.result,
            report_signature=body.report_signature,
        )
    except AgentAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except AgentServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return {"command_id": str(cmd.id), "status": cmd.status}
