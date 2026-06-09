"""Draft audit report API endpoints · CLUSTER 3 Phase C4.2.

Two router groups:
1. router_public · auditor portal endpoints (token-gated)
2. router_admin · admin endpoints (require_owner)

POST endpoints generate signed PDF stream (binary Content-Type application/pdf).
GET endpoints render HTML preview para inline iframe display (NO signed · NO PDF).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import status as http_status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.motors.m09_audit_prep.draft_report_generator import (
    DraftReportOptions,
    Recommendation,
    build_report_context,
    generate_draft_audit_report,
    render_report_html,
)
from backend.app.motors.m09_audit_prep.public_api import (
    _validate_token_peek,
    emit_auditor_event,
)


logger = logging.getLogger(__name__)


# Phase C4 canonical events
AUDITOR_DRAFT_REPORT_GENERATED = "auditor.draft_report.generated"
AUDITOR_DRAFT_REPORT_PREVIEW = "auditor.draft_report.preview"
ADMIN_DRAFT_REPORT_GENERATED = "admin.draft_report.generated"


# ════════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════════


class GenerateReportBody(BaseModel):
    auditor_opinion_text: str | None = Field(None, max_length=20000)
    recommendation: str | None = Field(
        None, description="APROBAR · APROBAR_CON_CONDICIONES · NO_APROBAR"
    )
    auditor_name: str | None = Field(None, max_length=255)
    audit_period_start: str | None = None
    audit_period_end: str | None = None


def _options_from_body(body: GenerateReportBody | None) -> DraftReportOptions:
    if body is None:
        return DraftReportOptions()
    if body.recommendation and body.recommendation not in Recommendation.VALUES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=(
                f"recommendation inválida · valores válidos: "
                f"{list(Recommendation.VALUES)}"
            ),
        )
    return DraftReportOptions(
        auditor_opinion_text=body.auditor_opinion_text,
        recommendation=body.recommendation,
        auditor_name=body.auditor_name,
        audit_period_start=body.audit_period_start,
        audit_period_end=body.audit_period_end,
    )


# ════════════════════════════════════════════════════════════════════════
# Auditor portal router (token-gated)
# ════════════════════════════════════════════════════════════════════════

router_public = APIRouter(
    prefix="/public/auditor-portal",
    tags=["Public Portal · Auditor ENAC Draft Report (Motor 9 · CLUSTER 3 C4)"],
)


@router_public.post("/{token}/audit/draft-report")
async def generate_draft_report_auditor(
    token: str,
    request: Request,
    body: GenerateReportBody | None = None,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate signed PDF · returns binary application/pdf · audit_log emit."""
    ctx = await _validate_token_peek(token, request, db)
    options = _options_from_body(body)

    result = await generate_draft_audit_report(
        db, ctx.project_id, options=options,
    )

    await emit_auditor_event(
        db, ctx, AUDITOR_DRAFT_REPORT_GENERATED,
        target="draft_report",
        metadata={
            "pdf_sha256": result.pdf_sha256,
            "recommendation": result.recommendation,
            "opinion_text_length": len(options.auditor_opinion_text or ""),
            "size_bytes": len(result.pdf_bytes),
        },
    )
    await db.commit()

    return Response(
        content=result.pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="borrador_auditoria_{ctx.project_id}.pdf"'
            ),
            "X-Pdf-Sha256": result.pdf_sha256,
            "X-Signature-Algorithm": "Ed25519",
            "X-Recommendation": result.recommendation,
        },
    )


@router_public.get(
    "/{token}/audit/draft-report/preview", response_class=HTMLResponse,
)
async def preview_draft_report_auditor(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Render HTML preview · NO signed · for inline iframe display."""
    ctx = await _validate_token_peek(token, request, db)
    context = await build_report_context(db, ctx.project_id)
    html = render_report_html(context)

    await emit_auditor_event(
        db, ctx, AUDITOR_DRAFT_REPORT_PREVIEW,
        target="draft_report_preview",
        metadata={"recommendation": context["recommendation"]},
    )
    await db.commit()
    return HTMLResponse(content=html, status_code=200)


# ════════════════════════════════════════════════════════════════════════
# Admin router (require_owner)
# ════════════════════════════════════════════════════════════════════════

router_admin = APIRouter(
    prefix="/admin/projects",
    tags=["Admin · Draft Audit Report (Motor 9 · CLUSTER 3 C4)"],
    dependencies=[Depends(require_owner)],
)


@router_admin.post("/{project_id}/audit/draft-report")
async def generate_draft_report_admin(
    project_id: uuid.UUID,
    body: GenerateReportBody | None = None,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_owner),
) -> Response:
    """Admin trigger · generates signed PDF · audit_log direct emit."""
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    options = _options_from_body(body)

    result = await generate_draft_audit_report(
        db, project_id, options=options,
    )

    # Audit log direct emit (NO via emit_auditor_event · NO auditor token)
    client_id_row = (await db.execute(sa_text(
        "SELECT client_id FROM projects WHERE id = :pid"
    ), {"pid": str(project_id)})).first()
    client_id_val = str(client_id_row[0]) if client_id_row else None
    admin_email = getattr(user, "email", None) or "marcosmata@fulkro.es"

    import json
    await db.execute(sa_text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, client_id, payload_new, timestamp) "
        "VALUES (gen_random_uuid(), 'projects', :rid, :accion, :user, "
        ":pid, :cid, :payload, now())"
    ), {
        "rid": str(project_id),
        "accion": ADMIN_DRAFT_REPORT_GENERATED,
        "user": admin_email[:255],
        "pid": str(project_id),
        "cid": client_id_val,
        "payload": json.dumps({
            "pdf_sha256": result.pdf_sha256,
            "recommendation": result.recommendation,
            "size_bytes": len(result.pdf_bytes),
        }),
    })
    await db.flush()
    await db.commit()

    return Response(
        content=result.pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="borrador_auditoria_{project_id}.pdf"'
            ),
            "X-Pdf-Sha256": result.pdf_sha256,
            "X-Signature-Algorithm": "Ed25519",
            "X-Recommendation": result.recommendation,
        },
    )


@router_admin.get(
    "/{project_id}/audit/draft-report/preview", response_class=HTMLResponse,
)
async def preview_draft_report_admin(
    project_id: uuid.UUID, db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Admin HTML preview render."""
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    context = await build_report_context(db, project_id)
    html = render_report_html(context)
    return HTMLResponse(content=html, status_code=200)
