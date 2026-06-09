"""Simple REST workflow chains · MB-7 Q7.C hybrid.

5 predefined chains of 2-3 agents · sequential invocation · NO Temporal.
For long-running multi-step orchestration use Temporal workflows in
backend/app/workflows/. This is the lightweight REST option for ad-hoc
chains from the cliente/admin UI.
"""
from __future__ import annotations

import importlib
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.base import AgentBase
from backend.app.agents.registry import get_agent_info
from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/workflows",
    tags=["workflows-simple"],
    dependencies=[Depends(require_owner)],
)


# Workflow registry · 5 predefined chains.
# Each step is the agent id in registry.
_WORKFLOWS: dict[str, dict] = {
    "audit_prep": {
        "description": "A11 auditor virtual → A4 redactor summary → A14 Q&A wrap-up",
        "steps": [11, 4, 14],
    },
    "incident_analysis": {
        "description": "A19 incident → A18 severity → A11 auditor check",
        "steps": [19, 18, 11],
    },
    "evidence_review": {
        "description": "A12 coach → A14 Q&A",
        "steps": [12, 14],
    },
    "retainer_optimal_proposal": {
        "description": "A19 propuestas → A20 negociacion counter",
        "steps": [19, 20],
    },
    "dda_review_inconsistencies": {
        "description": "A11 auditor → A21 discrepancias → A31 enriquecer",
        "steps": [11, 21, 31],
    },
}


# Same _AGENT_CLASSES map as agents/api.py — duplicated to avoid circular
# import. If maintenance burden grows, factor out to agents/registry.py.
_AGENT_CLASSES: dict[int, str] = {
    2: "agent_02_pliegos.AnalizadorPliegosAgent",
    4: "agent_04_redactor.RedactorPoliticasAgent",
    6: "agent_06_contratos.AnalistaContratosAgent",
    11: "agent_11_auditor_virtual.AuditorInternoVirtualAgent",
    12: "agent_12_coach_cliente.CoachClienteAgent",
    14: "agent_14_copiloto.CopilotoAgent",
    17: "agent_17_cualificador.CualificadorComercialAgent",
    18: "agent_18_reunion.AsistenteReunionExploratoriaAgent",
    19: "agent_19_propuestas.RedactorPropuestasAgent",
    20: "agent_20_negociacion.AsistenteNegociacionAgent",
    21: "agent_21_discrepancias.DetectorDiscrepanciasAgent",
    27: "agent_27_clasificador.ClasificadorIDMSAgent",
    31: "agent_31_enriquecedor_dda.Agent31EnriquecedorDdA",
}


def _get_agent_class(agent_id: int) -> type[AgentBase] | None:
    mapping = _AGENT_CLASSES.get(agent_id)
    if not mapping:
        return None
    module_name, class_name = mapping.rsplit(".", 1)
    mod = importlib.import_module(f"backend.app.agents.{module_name}")
    return getattr(mod, class_name, None)


class WorkflowRunBody(BaseModel):
    """Chain input · project_id + user_message + optional initial context."""

    project_id: Optional[uuid.UUID] = None
    user_message: str = Field(..., min_length=1, max_length=4000)
    context: Optional[dict] = None


class WorkflowStepResult(BaseModel):
    agent_id: int
    agent_name: str
    response: str
    tokens_input: int
    tokens_output: int
    latency_ms: int


class WorkflowRunResponse(BaseModel):
    workflow: str
    steps_executed: int
    total_tokens_input: int
    total_tokens_output: int
    total_latency_ms: int
    final_response: str
    step_results: list[WorkflowStepResult]


@router.get("")
async def list_workflows() -> dict[str, dict]:
    """List predefined workflow chains with their step descriptions."""
    return {
        name: {
            "description": cfg["description"],
            "steps": cfg["steps"],
        }
        for name, cfg in _WORKFLOWS.items()
    }


@router.post("/{workflow_name}/run", response_model=WorkflowRunResponse)
async def run_workflow(
    workflow_name: str,
    body: WorkflowRunBody,
    db: AsyncSession = Depends(get_db),
) -> WorkflowRunResponse:
    """Run a predefined chain · sequential invocation through agent steps.

    Each step receives the previous step's response as ``extra_context``.
    Stops at first error · returns 410 Gone if any step is deprecated.
    """
    cfg = _WORKFLOWS.get(workflow_name)
    if not cfg:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_name}' not registered",
        )

    step_results: list[WorkflowStepResult] = []
    accumulated_context = ""
    total_tokens_in = 0
    total_tokens_out = 0
    total_latency = 0

    for agent_id in cfg["steps"]:
        info = get_agent_info(agent_id)
        if not info:
            raise HTTPException(
                status_code=404,
                detail=f"Step agent {agent_id} not in registry",
            )
        if info.get("status") == "deprecated":
            raise HTTPException(
                status_code=410,
                detail=(
                    f"Step agent {agent_id} ({info.get('name', '?')}) "
                    f"deprecated · workflow halted"
                ),
            )
        agent_cls = _get_agent_class(agent_id)
        if not agent_cls:
            raise HTTPException(
                status_code=404,
                detail=f"Step agent {agent_id} has no implementation class",
            )

        agent = agent_cls()
        result = await agent.invoke(
            db=db,
            project_id=body.project_id,
            user_message=body.user_message,
            context=body.context,
            extra_context=accumulated_context,
        )
        step_results.append(WorkflowStepResult(
            agent_id=agent_id,
            agent_name=info.get("name", f"Agent {agent_id}"),
            response=result.get("response", ""),
            tokens_input=int(result.get("tokens_input", 0)),
            tokens_output=int(result.get("tokens_output", 0)),
            latency_ms=int(result.get("latency_ms", 0)),
        ))
        total_tokens_in += int(result.get("tokens_input", 0))
        total_tokens_out += int(result.get("tokens_output", 0))
        total_latency += int(result.get("latency_ms", 0))
        accumulated_context = (
            f"Salida del paso anterior (agente {agent_id} - "
            f"{info.get('name', '?')}):\n{result.get('response', '')}"
        )

    final_response = step_results[-1].response if step_results else ""
    return WorkflowRunResponse(
        workflow=workflow_name,
        steps_executed=len(step_results),
        total_tokens_input=total_tokens_in,
        total_tokens_output=total_tokens_out,
        total_latency_ms=total_latency,
        final_response=final_response,
        step_results=step_results,
    )
