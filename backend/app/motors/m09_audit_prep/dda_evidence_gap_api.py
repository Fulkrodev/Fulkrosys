"""DdA vs Evidence gap detection API · CLUSTER 3 Phase C3.2.

Two routers (pattern mirror C1/C2):
1. ``router_public`` · auditor portal endpoints (token-gated)
2. ``router_admin`` · admin endpoints (require_owner)

Admin POST /request-more-evidence triggers ClientNotification + emit audit_log
event admin.evidence_request.triggered con metadata={medida_codes_list}.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import status as http_status
from pydantic import BaseModel, Field
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.motors.m09_audit_prep.audit_events import (
    AUDITOR_EVENT_TYPES,
)
from backend.app.motors.m09_audit_prep.dda_evidence_gap_service import (
    GapDetectionOptions,
    compute_dda_evidence_gaps,
    compute_medida_detail,
)
from backend.app.motors.m09_audit_prep.public_api import (
    _validate_token_peek,
    emit_auditor_event,
)


logger = logging.getLogger(__name__)


# Phase C3 canonical events · added to audit_events.py
AUDITOR_VIEW_DDA_EVIDENCE_GAPS = "auditor.view.dda_evidence_gaps"
AUDITOR_VIEW_DDA_EVIDENCE_GAPS_DETAIL = (
    "auditor.view.dda_evidence_gaps_medida_detail"
)
ADMIN_EVIDENCE_REQUEST_TRIGGERED = "admin.evidence_request.triggered"


# ════════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════════


class RequestMoreEvidenceBody(BaseModel):
    medida_codes: list[str] = Field(
        ..., min_length=1, max_length=200,
        description="Códigos de medidas (e.g. ['op.acc.1', 'mp.s.4'])",
    )
    message_to_client: str | None = Field(
        None, max_length=5000,
        description="Mensaje libre para cliente · incluido en ClientNotification body",
    )


class RequestMoreEvidenceResponse(BaseModel):
    notification_id: str | None
    medida_codes: list[str]
    triggered_at: datetime


# ════════════════════════════════════════════════════════════════════════
# Auditor portal router (token-gated)
# ════════════════════════════════════════════════════════════════════════

router_public = APIRouter(
    prefix="/public/auditor-portal",
    tags=["Public Portal · Auditor ENAC DdA-Evidence Gaps (Motor 9 · CLUSTER 3 C3)"],
)


@router_public.get("/{token}/audit/dda-evidence-gaps")
async def get_dda_evidence_gaps_auditor(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Auditor consulta matrix gaps · token bounded project_id."""
    ctx = await _validate_token_peek(token, request, db)
    matrix = await compute_dda_evidence_gaps(db, ctx.project_id)
    await emit_auditor_event(
        db, ctx, AUDITOR_VIEW_DDA_EVIDENCE_GAPS,
        target="dda_evidence_gaps",
        metadata={
            "total_applicable": matrix.total_applicable,
            "total_missing": matrix.total_missing,
            "total_partial": matrix.total_partial,
            "coverage_pct": matrix.coverage_pct,
        },
    )
    await db.commit()
    return matrix.to_dict()


@router_public.get("/{token}/audit/dda-evidence-gaps/medida/{medida_code}")
async def get_medida_detail_auditor(
    token: str,
    medida_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Drill-down auditor per medida code."""
    ctx = await _validate_token_peek(token, request, db)
    detail = await compute_medida_detail(db, ctx.project_id, medida_code)
    if detail is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Medida {medida_code} no encontrada en catálogo",
        )
    await emit_auditor_event(
        db, ctx, AUDITOR_VIEW_DDA_EVIDENCE_GAPS_DETAIL,
        target=medida_code,
        metadata={
            "medida_code": medida_code,
            "status": detail.status,
            "severity": detail.severity,
            "evidence_count": detail.evidence_count,
        },
    )
    await db.commit()
    return detail.to_dict()


# ════════════════════════════════════════════════════════════════════════
# Admin router (require_owner)
# ════════════════════════════════════════════════════════════════════════

router_admin = APIRouter(
    prefix="/admin/projects",
    tags=["Admin · DdA-Evidence Gaps (Motor 9 · CLUSTER 3 C3)"],
    dependencies=[Depends(require_owner)],
)


@router_admin.get("/{project_id}/audit/dda-evidence-gaps")
async def get_dda_evidence_gaps_admin(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Admin matrix gaps · cross-project legítimo (require_owner)."""
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    matrix = await compute_dda_evidence_gaps(db, project_id)
    await db.commit()
    return matrix.to_dict()


@router_admin.post(
    "/{project_id}/audit/request-more-evidence",
    response_model=RequestMoreEvidenceResponse,
)
async def request_more_evidence_admin(
    project_id: uuid.UUID,
    body: RequestMoreEvidenceBody,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_owner),
) -> RequestMoreEvidenceResponse:
    """Admin solicita más evidencias al cliente · 1 ClientNotification + audit_log.

    Triggers:
    1. ClientNotification (type='evidence_request' · target_url evidence portal)
       · soporta 1+ medidas en un único notification (NO 1 per medida · spam)
    2. audit_log row admin.evidence_request.triggered metadata={medida_codes_list}
    """
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))

    # Validate project + resolve client_user (primary cliente piloto)
    project_row = (await db.execute(sa_text(
        "SELECT client_id, nombre FROM projects WHERE id = :pid"
    ), {"pid": str(project_id)})).first()
    if project_row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    client_id, project_name = project_row[0], project_row[1]

    client_user_row = (await db.execute(sa_text(
        "SELECT id FROM client_users WHERE client_id = :cid "
        "AND deleted_at IS NULL ORDER BY created_at LIMIT 1"
    ), {"cid": str(client_id)})).first()

    notification_id_str: str | None = None
    if client_user_row is not None:
        # Compose ClientNotification body
        medida_list_str = ", ".join(body.medida_codes[:10])
        if len(body.medida_codes) > 10:
            medida_list_str += f" (+ {len(body.medida_codes) - 10} más)"

        body_text = (
            f"Necesitamos evidencias adicionales para las siguientes medidas: "
            f"{medida_list_str}"
        )
        if body.message_to_client:
            body_text += f"\n\n{body.message_to_client}"

        from backend.app.motors.m21_portal_cliente.notification_service import (
            emit_client_notification,
        )
        notif = await emit_client_notification(
            db=db,
            project_id=project_id,
            client_user_id=client_user_row[0],
            type="evidence_request",
            title=f"Aportar evidencias adicionales · {len(body.medida_codes)} medidas",
            body=body_text,
            target_url="/client-portal/evidencias",
            priority="high",
            emitted_by_motor="m09",
            payload={
                "medida_codes": body.medida_codes,
                "triggered_by": "audit_evidence_gap_detection",
                "project_name": project_name,
            },
        )
        notification_id_str = str(notif.id)

    # Audit log emit direct (admin scope · NO via emit_auditor_event)
    admin_email = getattr(user, "email", None) or "marcosmata@fulkro.es"
    import json
    await db.execute(sa_text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, client_id, payload_new, timestamp) "
        "VALUES (gen_random_uuid(), 'projects', :rid, :accion, "
        ":user, :pid, :cid, :payload, now())"
    ), {
        "rid": str(project_id),
        "accion": ADMIN_EVIDENCE_REQUEST_TRIGGERED,
        "user": admin_email[:255],
        "pid": str(project_id),
        "cid": str(client_id),
        "payload": json.dumps({
            "medida_codes": body.medida_codes,
            "notification_id": notification_id_str,
            "medida_count": len(body.medida_codes),
            "has_custom_message": bool(body.message_to_client),
        }),
    })
    await db.flush()
    await db.commit()

    return RequestMoreEvidenceResponse(
        notification_id=notification_id_str,
        medida_codes=body.medida_codes,
        triggered_at=datetime.now(timezone.utc),
    )
