"""API endpoints retainer state + churn (MB-18.4 ADR-040).

Routers (admin · ``require_owner``):
- GET  ``/api/v1/admin/retainers/churn-risk``
- POST ``/api/v1/admin/retainers/{id}/transition``
- POST ``/api/v1/admin/retainers/scan-churn``
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.billing_milestones import (
    VALID_RISK_LEVELS,
)
from backend.app.retainer.state_machine import (
    RetainerStateMachine,
    RetainerStateMachineError,
    VALID_RETAINER_STATES,
)
from backend.app.retainer.tasks import scan_churn_risk_with_session

logger = logging.getLogger(__name__)


admin_retainer_router = APIRouter(
    prefix="/admin/retainers",
    tags=["Admin - Retainer Health (MB-18)"],
)


class ChurnRiskRow(BaseModel):
    signal_id: uuid.UUID
    retainer_id: uuid.UUID
    project_id: uuid.UUID
    computed_at: datetime
    churn_risk_score: str
    risk_level: str
    days_since_portal_login: int | None
    days_since_chat_msg_client: int | None
    tasks_overdue_count: int
    invoices_overdue_count: int
    primary_risk_factors: list[str]
    recommended_action: str | None


class TransitionRequest(BaseModel):
    target_state: str
    reason: str | None = None

    @field_validator("target_state")
    @classmethod
    def _validate_state(cls, v: str) -> str:
        if v not in VALID_RETAINER_STATES:
            raise ValueError(
                f"target_state debe estar en {VALID_RETAINER_STATES}"
            )
        return v


class TransitionResponse(BaseModel):
    retainer_id: uuid.UUID
    previous_state: str
    new_state: str
    reason: str | None


class ScanChurnResponse(BaseModel):
    total_scanned: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    alerts_created: int


async def _set_admin_rls_context(db: AsyncSession) -> None:
    await db.execute(
        text(
            "SELECT set_config('app.current_role_pool', 'marcos', true)"
        )
    )
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))


@admin_retainer_router.get(
    "/churn-risk",
    response_model=list[ChurnRiskRow],
)
async def list_churn_risk(
    db: Annotated[AsyncSession, Depends(get_db)],
    _owner: Annotated[User, Depends(require_owner)],
    risk_level: str | None = None,
    limit: int = 50,
):
    """Listado top retainers con churn signal reciente · default high+critical."""
    await _set_admin_rls_context(db)

    if risk_level and risk_level not in VALID_RISK_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"risk_level inválido · valores: {VALID_RISK_LEVELS}",
        )

    levels_filter: tuple[str, ...]
    if risk_level:
        levels_filter = (risk_level,)
    else:
        levels_filter = ("high", "critical")

    placeholders = ", ".join(f":lvl{i}" for i in range(len(levels_filter)))
    params: dict[str, str | int] = {
        f"lvl{i}": lvl for i, lvl in enumerate(levels_filter)
    }
    params["lim"] = limit

    rows = (await db.execute(
        text(
            "SELECT DISTINCT ON (retainer_id) "
            "id, retainer_id, project_id, computed_at, "
            "churn_risk_score, risk_level, "
            "days_since_portal_login, days_since_chat_msg_client, "
            "tasks_overdue_count, invoices_overdue_count, "
            "primary_risk_factors, recommended_action "
            "FROM retainer_health_signals "
            f"WHERE risk_level IN ({placeholders}) "
            "AND deleted_at IS NULL "
            "ORDER BY retainer_id, computed_at DESC "
            "LIMIT :lim"
        ),
        params,
    )).all()

    return [
        ChurnRiskRow(
            signal_id=r[0],
            retainer_id=r[1],
            project_id=r[2],
            computed_at=r[3],
            churn_risk_score=f"{Decimal(r[4]):.2f}",
            risk_level=r[5],
            days_since_portal_login=r[6],
            days_since_chat_msg_client=r[7],
            tasks_overdue_count=int(r[8] or 0),
            invoices_overdue_count=int(r[9] or 0),
            primary_risk_factors=list(r[10] or []),
            recommended_action=r[11],
        )
        for r in rows
    ]


@admin_retainer_router.post(
    "/{retainer_id}/transition",
    response_model=TransitionResponse,
)
async def transition_retainer(
    retainer_id: uuid.UUID,
    payload: TransitionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_owner)],
):
    await _set_admin_rls_context(db)
    sm = RetainerStateMachine(db)
    try:
        outcome = await sm.transition(
            retainer_id=retainer_id,
            target_state=payload.target_state,
            reason=payload.reason,
            by_user_id=owner.id,
        )
    except RetainerStateMachineError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return TransitionResponse(
        retainer_id=outcome.retainer_id,
        previous_state=outcome.previous_state,
        new_state=outcome.new_state,
        reason=outcome.reason,
    )


@admin_retainer_router.post(
    "/scan-churn",
    response_model=ScanChurnResponse,
)
async def trigger_scan_churn(
    db: Annotated[AsyncSession, Depends(get_db)],
    _owner: Annotated[User, Depends(require_owner)],
):
    """Trigger manual scan churn (debug Celery beat)."""
    await _set_admin_rls_context(db)
    stats = await scan_churn_risk_with_session(db)
    return ScanChurnResponse(
        total_scanned=stats["total_scanned"],
        critical_count=stats["critical_count"],
        high_count=stats["high_count"],
        medium_count=stats["medium_count"],
        low_count=stats["low_count"],
        alerts_created=stats["alerts_created"],
    )


__all__ = ["admin_retainer_router"]
