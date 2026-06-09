"""Sub-atom 1.D.E.A v3.11 · MCP execution endpoints project-scoped.

5 endpoints REST + SSE stream:
  POST /api/v1/projects/{id}/mcps/{mcp}/tools/{tool}/execute → trigger
  GET  /api/v1/projects/{id}/mcps/executions/{exec_id} → status + result
  GET  /api/v1/projects/{id}/mcps/executions/{exec_id}/stream → SSE events
  GET  /api/v1/projects/{id}/mcps/executions/{exec_id}/report → JSON download
  GET  /api/v1/projects/{id}/mcps/executions → history per project
  GET  /api/v1/mcps/tools → catalog 13 tools per family

R23 sostener firmísimo · todo project-scoped · require_owner admin-only.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m08_verification.mcp_executor_service import (
    MCP_TOOLS_CATALOG,
    MCPExecutorError,
    get_mcp_executor,
    get_tool_descriptor,
    list_all_tools,
)


router = APIRouter(
    prefix="/api/v1",
    tags=["MCPs - Execution project-scoped (1.D.E)"],
    dependencies=[Depends(require_owner)],
)


_HEARTBEAT_INTERVAL_SECONDS = 30


async def _set_project_rls(
    project_id: uuid.UUID, db: AsyncSession,
) -> None:
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class ExecuteMCPBody(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)


class MCPExecutionOut(BaseModel):
    execution_id: str
    project_id: str
    mcp_name: str
    tool_name: str
    params: dict[str, Any]
    triggered_by: str
    status: str
    progress: int
    started_at: str | None
    completed_at: str | None
    result: dict[str, Any] | None
    error: str | None
    evidence_document_id: str | None


class MCPToolParamOut(BaseModel):
    name: str
    type: str
    description: str
    required: bool
    default: Any | None = None
    enum: list[str] | None = None
    placeholder: str | None = None


class MCPToolOut(BaseModel):
    mcp_name: str
    tool_name: str
    label: str
    description: str
    risk_level: str
    estimated_duration_s: int
    params: list[MCPToolParamOut]


class MCPCatalogOut(BaseModel):
    families: dict[str, list[MCPToolOut]]
    total: int


# ════════════════════════════════════════════════════════════════════
# Catalog endpoint (NO project-scoped · catálogo es global · pero R23
# sostener: este endpoint sólo lo consume la página project-scoped)
# ════════════════════════════════════════════════════════════════════


@router.get("/mcps/tools", response_model=MCPCatalogOut)
async def list_tools_catalog() -> MCPCatalogOut:
    """Catálogo 13 tools agrupadas por familia (vulnscan · cloud · config
    · phishing). Consumido por el formulario UI project-scoped (frontend
    `/admin/projects/{id}/mcps/`).
    """
    families: dict[str, list[MCPToolOut]] = {}
    total = 0
    for family, tools in MCP_TOOLS_CATALOG.items():
        items: list[MCPToolOut] = []
        for t in tools.values():
            items.append(
                MCPToolOut(
                    mcp_name=t.mcp_name,
                    tool_name=t.tool_name,
                    label=t.label,
                    description=t.description,
                    risk_level=t.risk_level,
                    estimated_duration_s=t.estimated_duration_s,
                    params=[
                        MCPToolParamOut(
                            name=p.name, type=p.type,
                            description=p.description,
                            required=p.required, default=p.default,
                            enum=list(p.enum) if p.enum else None,
                            placeholder=p.placeholder,
                        )
                        for p in t.params
                    ],
                ),
            )
            total += 1
        families[family] = items
    return MCPCatalogOut(families=families, total=total)


# ════════════════════════════════════════════════════════════════════
# Execute + status + history
# ════════════════════════════════════════════════════════════════════


def _serialize_execution(e) -> MCPExecutionOut:
    return MCPExecutionOut(
        execution_id=str(e.execution_id),
        project_id=str(e.project_id),
        mcp_name=e.mcp_name,
        tool_name=e.tool_name,
        params=e.params,
        triggered_by=e.triggered_by,
        status=e.status,
        progress=e.progress,
        started_at=e.started_at.isoformat() if e.started_at else None,
        completed_at=e.completed_at.isoformat() if e.completed_at else None,
        result=e.result,
        error=e.error,
        evidence_document_id=(
            str(e.evidence_document_id) if e.evidence_document_id else None
        ),
    )


@router.post(
    "/projects/{project_id}/mcps/{mcp_name}/tools/{tool_name}/execute",
    status_code=status.HTTP_201_CREATED,
    response_model=MCPExecutionOut,
)
async def execute_mcp_tool(
    project_id: uuid.UUID,
    mcp_name: str,
    tool_name: str,
    body: ExecuteMCPBody,
    db: AsyncSession = Depends(get_db),
) -> MCPExecutionOut:
    """Dispara la ejecución de un MCP tool (background task · async).

    Devuelve inmediatamente el ``execution_id`` con status=pending. El
    cliente debe poll ``GET /executions/{exec_id}`` o conectar al SSE
    stream ``/executions/{exec_id}/stream`` para progreso real-time.
    """
    await _set_project_rls(project_id, db)
    if not get_tool_descriptor(mcp_name, tool_name):
        raise HTTPException(
            status_code=404,
            detail=(
                f"Tool {mcp_name}/{tool_name} no existe en el catálogo. "
                f"Ver GET /api/v1/mcps/tools"
            ),
        )
    try:
        execution = await get_mcp_executor().execute_tool(
            db=db,
            project_id=project_id,
            mcp_name=mcp_name,
            tool_name=tool_name,
            params=body.params,
        )
    except MCPExecutorError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _serialize_execution(execution)


@router.get(
    "/projects/{project_id}/mcps/executions/{execution_id}",
    response_model=MCPExecutionOut,
)
async def get_execution_status(
    project_id: uuid.UUID,
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MCPExecutionOut:
    await _set_project_rls(project_id, db)
    execution = get_mcp_executor().get_execution(execution_id)
    if not execution or execution.project_id != project_id:
        raise HTTPException(status_code=404, detail="Execution not found")
    return _serialize_execution(execution)


@router.get("/projects/{project_id}/mcps/executions")
async def list_executions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    executions = get_mcp_executor().list_executions_by_project(project_id)
    executions.sort(
        key=lambda e: e.started_at or e.completed_at or e.event_queue.qsize(),
        reverse=True,
    )
    return {
        "project_id": str(project_id),
        "total": len(executions),
        "executions": [_serialize_execution(e).model_dump() for e in executions],
    }


@router.get(
    "/projects/{project_id}/mcps/executions/{execution_id}/report",
)
async def download_execution_report(
    project_id: uuid.UUID,
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Descarga el reporte JSON del execution. El reporte completo
    también se persiste en m24_idms como Evidence (folder 13_Informes_
    Tecnicos · clasificacion=informe).
    """
    await _set_project_rls(project_id, db)
    execution = get_mcp_executor().get_execution(execution_id)
    if not execution or execution.project_id != project_id:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.status not in ("completed", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Execution todavía en estado {execution.status}",
        )

    payload = {
        "execution_id": str(execution.execution_id),
        "project_id": str(execution.project_id),
        "mcp_name": execution.mcp_name,
        "tool_name": execution.tool_name,
        "params": execution.params,
        "triggered_by": execution.triggered_by,
        "status": execution.status,
        "started_at": (
            execution.started_at.isoformat() if execution.started_at else None
        ),
        "completed_at": (
            execution.completed_at.isoformat()
            if execution.completed_at else None
        ),
        "result": execution.result,
        "error": execution.error,
        "evidence_document_id": (
            str(execution.evidence_document_id)
            if execution.evidence_document_id else None
        ),
    }
    content = json.dumps(payload, indent=2, default=str).encode("utf-8")
    filename = (
        f"mcp_{execution.mcp_name}_{execution.tool_name}_"
        f"{execution.execution_id.hex[:8]}.json"
    )
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ════════════════════════════════════════════════════════════════════
# SSE stream
# ════════════════════════════════════════════════════════════════════


@router.get(
    "/projects/{project_id}/mcps/executions/{execution_id}/stream",
    summary="SSE stream progress events para una ejecución MCP",
)
async def stream_execution_events(
    project_id: uuid.UUID,
    execution_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Stream SSE de eventos de la ejecución:
      - ``started`` cuando arranca
      - ``progress`` con {progress, message}
      - ``completed`` con {evidence_document_id, summary}
      - ``failed`` con {error}
      - ``heartbeat`` cada 30s para mantener conexión viva

    Cliente: ``new EventSource('/api/v1/projects/X/mcps/executions/Y/stream')``.
    """
    await _set_project_rls(project_id, db)
    execution = get_mcp_executor().get_execution(execution_id)
    if not execution or execution.project_id != project_id:
        raise HTTPException(status_code=404, detail="Execution not found")

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(
                        execution.event_queue.get(),
                        timeout=_HEARTBEAT_INTERVAL_SECONDS,
                    )
                except asyncio.TimeoutError:
                    yield {"event": "heartbeat", "data": "ping"}
                    continue
                if event is None:
                    # Sentinel · ejecución terminó
                    break
                yield {
                    "event": event["type"],
                    "data": json.dumps(event["data"], default=str),
                }
        except asyncio.CancelledError:
            pass

    return EventSourceResponse(event_generator())
