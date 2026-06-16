"""Motor 6 · cliente policies portal · SAN-E v3.MB-6 atom 1.

ADR-020 v6 · Q1.C híbrida: cliente review individual + firma bulk única CCN-STIC 805.

Endpoints (cliente-facing · auth ClientUser cookie + CSRF triple binding):

- GET   /portal/policies/projects/{project_id}                   · summary tier
- GET   /portal/policies/projects/{project_id}/list              · 25 policy cards
- POST  /portal/policies/documents/{document_id}/review          · cliente review action
- GET   /portal/policies/projects/{project_id}/document-hash     · SHA256 bulk pre-firma
- POST  /portal/policies/projects/{project_id}/finalize-signoff  · post-firma link signing_intent

Pattern atom 5.3.A · 5.4.A · 5.5.A consolidated 6ª aplicación.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m05_signing.models import SigningIntent
from backend.app.motors.m06_document_factory.policy_signoff_service import (
    InvalidReviewActionError,
    InvalidTierError,
    PolicyDocumentNotFoundError,
    PolicySignoffService,
    ProjectNotFoundError,
)
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m21_portal_cliente.ownership import ensure_owned_via_project


router = APIRouter(
    prefix="/portal/policies",
    tags=["Motor 06 - Policies signoff (cliente)"],
)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class PolicyClientViewOut(BaseModel):
    """Vista cliente single policy document."""

    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID | None
    template_codigo: str
    nombre: str | None
    level: int
    family: str
    docx_path: str | None
    estado: str | None
    client_review_status: str | None
    client_review_note: str | None
    client_reviewed_at: datetime | None
    client_signing_intent_id: uuid.UUID | None


class PolicySummaryOut(BaseModel):
    """Resumen tier + counters portal cliente header."""

    project_id: uuid.UUID
    tier: str
    expected_count: int
    generated_count: int
    pending_review_count: int
    revisada_ok_count: int
    with_questions_count: int
    suggest_change_count: int
    ready_for_bulk_sign: bool
    bulk_signing_intent_id: uuid.UUID | None
    bulk_signed: bool


class PolicyReviewRequest(BaseModel):
    action: str = Field(..., description="revisada_ok / con_pregunta / suggest_change")
    note: str | None = Field(None, max_length=4000)


class PolicyBulkHashOut(BaseModel):
    project_id: uuid.UUID
    tier: str
    expected_count: int
    canonical_length: int
    document_hash_sha256: str
    ready_for_signing: bool


class PolicyFinalizeSignoffRequest(BaseModel):
    signing_intent_id: uuid.UUID


class PolicyFinalizeSignoffOut(BaseModel):
    project_id: uuid.UUID
    signing_intent_id: uuid.UUID
    documents_linked: int


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _service(db: AsyncSession) -> PolicySignoffService:
    return PolicySignoffService(db)


async def _ensure_project_belongs_to_client(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: ClientUser,
) -> None:
    from sqlalchemy import text as sa_text
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
    await set_tenant_context(db, client_id=user.client_id, project_id=project_id)


def _handle_service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, InvalidTierError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, InvalidReviewActionError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, PolicyDocumentNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


# ════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════


@router.get("/projects/{project_id}", response_model=PolicySummaryOut)
async def get_policies_summary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> PolicySummaryOut:
    """Summary tier policies project · counters + readiness gate."""
    await _ensure_project_belongs_to_client(db, project_id, user)
    try:
        summary = await _service(db).get_summary(project_id)
    except (ProjectNotFoundError, InvalidTierError) as exc:
        raise _handle_service_error(exc) from exc
    return PolicySummaryOut(
        project_id=summary.project_id,
        tier=summary.tier,
        expected_count=summary.expected_count,
        generated_count=summary.generated_count,
        pending_review_count=summary.pending_review_count,
        revisada_ok_count=summary.revisada_ok_count,
        with_questions_count=summary.with_questions_count,
        suggest_change_count=summary.suggest_change_count,
        ready_for_bulk_sign=summary.ready_for_bulk_sign,
        bulk_signing_intent_id=summary.bulk_signing_intent_id,
        bulk_signed=summary.bulk_signed,
    )


@router.get(
    "/projects/{project_id}/list",
    response_model=list[PolicyClientViewOut],
)
async def list_policies(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> list[PolicyClientViewOut]:
    """Lista 25 policies project (tier-aware) · review state."""
    await _ensure_project_belongs_to_client(db, project_id, user)
    try:
        items = await _service(db).list_policies_for_client(project_id)
    except (ProjectNotFoundError, InvalidTierError) as exc:
        raise _handle_service_error(exc) from exc
    return [
        PolicyClientViewOut(
            document_id=i.document_id,
            template_codigo=i.template_codigo,
            nombre=i.nombre,
            level=i.level,
            family=i.family,
            docx_path=i.docx_path,
            estado=i.estado,
            client_review_status=i.client_review_status,
            client_review_note=i.client_review_note,
            client_reviewed_at=i.client_reviewed_at,
            client_signing_intent_id=i.client_signing_intent_id,
        )
        for i in items
    ]


@router.post(
    "/documents/{document_id}/review",
    response_model=PolicyClientViewOut,
)
async def review_policy(
    document_id: uuid.UUID,
    body: PolicyReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> PolicyClientViewOut:
    """Cliente review individual policy · revisada_ok/con_pregunta/suggest_change."""
    from sqlalchemy import text as sa_text
    row = await db.execute(
        sa_text("SELECT project_id FROM documents WHERE id = :did"),
        {"did": str(document_id)},
    )
    hit = row.first()
    if hit is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    project_id = hit[0]
    await ensure_owned_via_project(db, project_id, user)

    try:
        doc = await _service(db).review_policy(
            document_id=document_id,
            action=body.action,
            note=body.note,
            user_id=user.id,
        )
    except (PolicyDocumentNotFoundError, InvalidReviewActionError) as exc:
        raise _handle_service_error(exc) from exc

    await db.commit()

    from backend.app.motors.m06_document_factory.policy_signoff_service import (
        _POLICY_FAMILY,
    )
    family = _POLICY_FAMILY.get(doc.template_codigo or "", "otros")
    level = 1 if doc.template_codigo == "E-100" else 2

    return PolicyClientViewOut(
        document_id=doc.id,
        template_codigo=doc.template_codigo or "",
        nombre=doc.nombre,
        level=level,
        family=family,
        docx_path=doc.docx_path,
        estado=doc.estado,
        client_review_status=doc.client_review_status,
        client_review_note=doc.client_review_note,
        client_reviewed_at=doc.client_reviewed_at,
        client_signing_intent_id=doc.client_signing_intent_id,
    )


@router.get(
    "/projects/{project_id}/document-hash",
    response_model=PolicyBulkHashOut,
)
async def get_bulk_document_hash(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> PolicyBulkHashOut:
    """SHA256 deterministic bulk policies state · input crear SigningIntent."""
    await _ensure_project_belongs_to_client(db, project_id, user)
    try:
        doc_hash, canonical_length = await _service(db).compute_bulk_document_hash(
            project_id,
        )
        summary = await _service(db).get_summary(project_id)
    except (ProjectNotFoundError, InvalidTierError) as exc:
        raise _handle_service_error(exc) from exc

    return PolicyBulkHashOut(
        project_id=project_id,
        tier=summary.tier,
        expected_count=summary.expected_count,
        canonical_length=canonical_length,
        document_hash_sha256=doc_hash,
        ready_for_signing=summary.ready_for_bulk_sign,
    )


@router.post(
    "/projects/{project_id}/finalize-signoff",
    response_model=PolicyFinalizeSignoffOut,
)
async def finalize_bulk_signoff(
    project_id: uuid.UUID,
    body: PolicyFinalizeSignoffRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> PolicyFinalizeSignoffOut:
    """Post-firma bulk · linkea TODOS documents al signing_intent · audit ENAC."""
    await _ensure_project_belongs_to_client(db, project_id, user)

    intent = await db.get(SigningIntent, body.signing_intent_id)
    if intent is None:
        raise HTTPException(status_code=404, detail="SigningIntent no existe")
    if intent.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="SigningIntent no pertenece al project",
        )
    if intent.signable_type != "policy_approval":
        raise HTTPException(
            status_code=400,
            detail=(
                f"SigningIntent.signable_type='{intent.signable_type}' "
                f"esperado 'policy_approval'"
            ),
        )
    if intent.status != "signed":
        raise HTTPException(
            status_code=409,
            detail=f"SigningIntent status='{intent.status}' · esperado 'signed'",
        )

    try:
        count = await _service(db).mark_bulk_signed(
            project_id=project_id,
            signing_intent_id=body.signing_intent_id,
        )
    except (ProjectNotFoundError, InvalidTierError) as exc:
        raise _handle_service_error(exc) from exc

    await db.commit()

    return PolicyFinalizeSignoffOut(
        project_id=project_id,
        signing_intent_id=body.signing_intent_id,
        documents_linked=count,
    )
