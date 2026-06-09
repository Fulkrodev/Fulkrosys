"""Motor 27 · DPC anual portal cliente API · SAN-E v3.MB-6 atom 2.

CCN-STIC 806 · art.25 RD 311/2022 · cliente revisa contexto + firma anual.

Endpoints (cliente-facing · auth ClientUser cookie + CSRF):

- GET   /portal/dpc-anual/projects/{project_id}                · list current + history
- GET   /portal/dpc-anual/declarations/{id}                    · detail single declaration
- POST  /portal/dpc-anual/declarations/{id}/review             · review action cliente
- GET   /portal/dpc-anual/declarations/{id}/document-hash      · SHA256 pre-firma
- POST  /portal/dpc-anual/declarations/{id}/finalize-signoff   · link signing_intent

Pattern atom 1 (policies) consolidated 9ª aplicación drop-in.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m05_signing.models import SigningIntent
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m27_conformity.dpc_anual_service import (
    ConformidadNotSignedError,
    DpcAlreadySignedError,
    DpcAnualService,
    DpcDeclarationNotFoundError,
    InvalidReviewActionError,
)


router = APIRouter(
    prefix="/portal/dpc-anual",
    tags=["Motor 27 - DPC anual (cliente)"],
)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class DpcDeclarationOut(BaseModel):
    """Vista cliente single DPC anual declaration."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    anniversary_year: int
    status: str
    client_concerns_note: str | None
    client_reviewed_at: datetime | None
    client_signing_intent_id: uuid.UUID | None
    signed_at: datetime | None
    conformidad_signature_id: str | None
    anniversary_date: date
    days_until_anniversary: int | None
    created_at: datetime


class DpcContextOut(BaseModel):
    """Detail con readiness_snapshot 4 secciones (Q3.A)."""

    declaration: DpcDeclarationOut
    sla_section: dict
    recovery_section: dict
    incidents_section: dict
    roadmap_section: dict


class DpcReviewRequest(BaseModel):
    action: str = Field(..., description="revisada_ok / con_pregunta / suggest_change")
    note: str | None = Field(None, max_length=4000)


class DpcDocumentHashOut(BaseModel):
    declaration_id: uuid.UUID
    anniversary_year: int
    canonical_length: int
    document_hash_sha256: str
    ready_for_signing: bool


class DpcFinalizeSignoffRequest(BaseModel):
    signing_intent_id: uuid.UUID


class DpcFinalizeSignoffOut(BaseModel):
    declaration_id: uuid.UUID
    signing_intent_id: uuid.UUID
    signed_at: datetime
    signed_hash: str


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _service(db: AsyncSession) -> DpcAnualService:
    return DpcAnualService(db)


async def _ensure_project_belongs_to_client(
    db: AsyncSession, project_id: uuid.UUID, user: ClientUser,
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


async def _get_declaration_project(
    db: AsyncSession, declaration_id: uuid.UUID,
) -> uuid.UUID:
    from sqlalchemy import text as sa_text
    row = await db.execute(
        sa_text(
            "SELECT project_id FROM basic_declarations "
            "WHERE id = :did AND declaration_type = 'dpc_anual'"
        ),
        {"did": str(declaration_id)},
    )
    hit = row.first()
    if hit is None:
        raise HTTPException(status_code=404, detail="DPC declaration no existe")
    return hit[0]


def _handle_service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ConformidadNotSignedError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, DpcDeclarationNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, InvalidReviewActionError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, DpcAlreadySignedError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


def _view_to_out(view) -> DpcDeclarationOut:
    return DpcDeclarationOut(
        id=view.id,
        project_id=view.project_id,
        anniversary_year=view.anniversary_year,
        status=view.status,
        client_concerns_note=view.client_concerns_note,
        client_reviewed_at=view.client_reviewed_at,
        client_signing_intent_id=view.client_signing_intent_id,
        signed_at=view.signed_at,
        conformidad_signature_id=view.conformidad_signature_id,
        anniversary_date=view.anniversary_date,
        days_until_anniversary=view.days_until_anniversary,
        created_at=view.created_at,
    )


# ════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════


@router.get(
    "/projects/{project_id}",
    response_model=list[DpcDeclarationOut],
)
async def list_dpc_declarations(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> list[DpcDeclarationOut]:
    """Lista DPC anual declarations project · current + history."""
    await _ensure_project_belongs_to_client(db, project_id, user)
    views = await _service(db).list_declarations_for_project(project_id)
    return [_view_to_out(v) for v in views]


@router.get(
    "/declarations/{declaration_id}",
    response_model=DpcContextOut,
)
async def get_dpc_declaration_detail(
    declaration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> DpcContextOut:
    """Detail single DPC declaration · 4 secciones readiness snapshot."""
    project_id = await _get_declaration_project(db, declaration_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    views = await _service(db).list_declarations_for_project(project_id)
    view = next((v for v in views if v.id == declaration_id), None)
    if view is None:
        raise HTTPException(status_code=404, detail="DPC declaration no existe")

    from backend.app.models.conformity_lifecycle import BasicDeclarationRow
    decl = await db.get(BasicDeclarationRow, declaration_id)
    if decl is None:
        raise HTTPException(status_code=404, detail="DPC declaration no existe")
    readiness = decl.readiness_snapshot_jsonb or {}

    return DpcContextOut(
        declaration=_view_to_out(view),
        sla_section=readiness.get("sla_section", {}),
        recovery_section=readiness.get("recovery_section", {}),
        incidents_section=readiness.get("incidents_section", {}),
        roadmap_section=readiness.get("roadmap_section", {}),
    )


@router.post(
    "/declarations/{declaration_id}/review",
    response_model=DpcDeclarationOut,
)
async def review_dpc_declaration(
    declaration_id: uuid.UUID,
    body: DpcReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> DpcDeclarationOut:
    """Cliente review action DPC anual."""
    project_id = await _get_declaration_project(db, declaration_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    try:
        decl = await _service(db).mark_dpc_reviewed(
            declaration_id=declaration_id,
            action=body.action,
            note=body.note,
            user_id=user.id,
        )
    except (InvalidReviewActionError, DpcDeclarationNotFoundError) as exc:
        raise _handle_service_error(exc) from exc

    await db.commit()

    views = await _service(db).list_declarations_for_project(project_id)
    view = next((v for v in views if v.id == decl.id), None)
    if view is None:
        raise HTTPException(status_code=500, detail="View regeneration failed")
    return _view_to_out(view)


@router.get(
    "/declarations/{declaration_id}/document-hash",
    response_model=DpcDocumentHashOut,
)
async def get_dpc_document_hash(
    declaration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> DpcDocumentHashOut:
    """SHA256 deterministic DPC declaration state · input firma M05."""
    project_id = await _get_declaration_project(db, declaration_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    try:
        doc_hash, canonical_length = await _service(db).compute_dpc_document_hash(
            declaration_id,
        )
    except DpcDeclarationNotFoundError as exc:
        raise _handle_service_error(exc) from exc

    from backend.app.models.conformity_lifecycle import BasicDeclarationRow
    decl = await db.get(BasicDeclarationRow, declaration_id)
    assert decl is not None
    ready = decl.client_reviewed_at is not None and decl.signed_at is None

    return DpcDocumentHashOut(
        declaration_id=declaration_id,
        anniversary_year=decl.anniversary_year or 0,
        canonical_length=canonical_length,
        document_hash_sha256=doc_hash,
        ready_for_signing=ready,
    )


@router.post(
    "/declarations/{declaration_id}/finalize-signoff",
    response_model=DpcFinalizeSignoffOut,
)
async def finalize_dpc_signoff(
    declaration_id: uuid.UUID,
    body: DpcFinalizeSignoffRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> DpcFinalizeSignoffOut:
    """Post-firma DPC · link signing_intent_id + signed_at + signed_hash."""
    project_id = await _get_declaration_project(db, declaration_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    intent = await db.get(SigningIntent, body.signing_intent_id)
    if intent is None:
        raise HTTPException(status_code=404, detail="SigningIntent no existe")
    if intent.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="SigningIntent no pertenece al project",
        )
    if intent.signable_type != "dpc_anual":
        raise HTTPException(
            status_code=400,
            detail=(
                f"SigningIntent.signable_type='{intent.signable_type}' "
                f"esperado 'dpc_anual'"
            ),
        )
    if intent.status != "signed":
        raise HTTPException(
            status_code=409,
            detail=f"SigningIntent status='{intent.status}' · esperado 'signed'",
        )

    try:
        decl = await _service(db).process_dpc_signoff(
            declaration_id=declaration_id,
            signing_intent_id=body.signing_intent_id,
        )
    except (DpcDeclarationNotFoundError, DpcAlreadySignedError) as exc:
        raise _handle_service_error(exc) from exc

    await db.commit()

    return DpcFinalizeSignoffOut(
        declaration_id=decl.id,
        signing_intent_id=body.signing_intent_id,
        signed_at=decl.signed_at,
        signed_hash=decl.signed_hash or "",
    )
