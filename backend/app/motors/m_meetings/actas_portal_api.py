"""M_meetings · Actas portal cliente · SAN-E v3.MB-6 atom 5.

5 endpoints cliente cliente-facing (admin curate diferido atom 5.bis):
- GET   /portal/actas/projects/{id}                · list visible + optional subtype filter
- GET   /portal/actas/{id}                         · detail
- POST  /portal/actas/{id}/review                  · cliente review MixinA
- GET   /portal/actas/{id}/document-hash           · SHA256 pre-firma
- POST  /portal/actas/{id}/finalize-signoff        · link signing_intent

Auth ClientUser (cookie session + CSRF triple binding pattern existing M21).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.models.governance import CommitteeMeeting, ACTA_SUBTYPE_LABELS
from backend.app.motors.m05_signing.models import SigningIntent
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m_meetings.actas_service import (
    ACTA_SUBTYPES,
    ActaAlreadySignedError,
    ActaNotFoundError,
    ActasError,
    ActasService,
    InvalidActaSubtypeError,
    InvalidReviewActionError,
)


router = APIRouter(
    prefix="/portal/actas",
    tags=["Motor meetings - Actas (cliente)"],
)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class ActaClientOut(BaseModel):
    """Vista cliente acta · admin_curation_status='sent_to_client'."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    codigo: str | None
    acta_subtype: str | None
    acta_subtype_label: str
    titulo: str | None
    fecha: datetime | None
    lugar: str | None
    presidente: str | None
    secretario: str | None
    asistentes: list | None
    orden_del_dia: list | None
    acuerdos_jsonb: list | None
    proximos_pasos: list | None
    notas_libres: str | None
    estado: str | None
    admin_curation_status: str
    hash_sha256: str | None
    signature_ed25519: str | None
    firmas: list | None
    fully_signed_at: datetime | None
    client_review_status: str | None
    client_review_note: str | None
    client_reviewed_at: datetime | None
    client_signing_intent_id: uuid.UUID | None
    pdf_path: str | None
    created_at: datetime


class ActaReviewRequest(BaseModel):
    action: str = Field(..., description="revisada_ok / con_pregunta / suggest_change")
    note: str | None = Field(None, max_length=4000)


class ActaDocumentHashOut(BaseModel):
    meeting_id: uuid.UUID
    acta_subtype: str | None
    canonical_length: int
    document_hash_sha256: str
    ready_for_signing: bool


class ActaFinalizeSignoffRequest(BaseModel):
    signing_intent_id: uuid.UUID


class ActaFinalizeSignoffOut(BaseModel):
    meeting_id: uuid.UUID
    signing_intent_id: uuid.UUID


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _service(db: AsyncSession) -> ActasService:
    return ActasService(db)


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


async def _get_acta_project(
    db: AsyncSession, meeting_id: uuid.UUID,
) -> uuid.UUID:
    from sqlalchemy import text as sa_text
    row = await db.execute(
        sa_text(
            "SELECT project_id FROM committee_meetings WHERE id = :mid"
        ),
        {"mid": str(meeting_id)},
    )
    hit = row.first()
    if hit is None:
        raise HTTPException(status_code=404, detail="Acta no existe")
    return hit[0]


def _handle_service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ActaNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, InvalidActaSubtypeError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, InvalidReviewActionError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, ActaAlreadySignedError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ActasError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


def _to_out(meeting: CommitteeMeeting) -> ActaClientOut:
    label = ""
    if meeting.acta_subtype:
        label = ACTA_SUBTYPE_LABELS.get(meeting.acta_subtype, meeting.acta_subtype)
    return ActaClientOut(
        id=meeting.id,
        project_id=meeting.project_id,
        codigo=meeting.codigo,
        acta_subtype=meeting.acta_subtype,
        acta_subtype_label=label,
        titulo=meeting.titulo,
        fecha=meeting.fecha,
        lugar=meeting.lugar,
        presidente=meeting.presidente,
        secretario=meeting.secretario,
        asistentes=meeting.asistentes,
        orden_del_dia=meeting.orden_del_dia,
        acuerdos_jsonb=meeting.acuerdos_jsonb,
        proximos_pasos=meeting.proximos_pasos,
        notas_libres=meeting.notas_libres,
        estado=meeting.estado,
        admin_curation_status=meeting.admin_curation_status,
        hash_sha256=meeting.hash_sha256,
        signature_ed25519=meeting.signature_ed25519,
        firmas=meeting.firmas,
        fully_signed_at=meeting.fully_signed_at,
        client_review_status=meeting.client_review_status,
        client_review_note=meeting.client_review_note,
        client_reviewed_at=meeting.client_reviewed_at,
        client_signing_intent_id=meeting.client_signing_intent_id,
        pdf_path=meeting.pdf_path,
        created_at=meeting.created_at,
    )


# ════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════


@router.get(
    "/projects/{project_id}",
    response_model=list[ActaClientOut],
)
async def list_client_actas(
    project_id: uuid.UUID,
    subtype: str | None = Query(
        None,
        description="Optional filter · uno de kickoff / checkpoint / audit / cierre / other",
    ),
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> list[ActaClientOut]:
    """Lista actas visible · admin_curation_status='sent_to_client' + optional subtype filter."""
    await _ensure_project_belongs_to_client(db, project_id, user)
    if subtype is not None and subtype not in ACTA_SUBTYPES:
        raise HTTPException(
            status_code=400,
            detail=f"subtype '{subtype}' invalido · esperado {list(ACTA_SUBTYPES)}",
        )
    try:
        meetings = await _service(db).list_actas_for_client(
            project_id=project_id, subtype_filter=subtype,
        )
    except InvalidActaSubtypeError as exc:
        raise _handle_service_error(exc) from exc
    return [_to_out(m) for m in meetings]


@router.get(
    "/{meeting_id}",
    response_model=ActaClientOut,
)
async def get_client_acta_detail(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> ActaClientOut:
    """Detail single · enforce sent_to_client visibility."""
    project_id = await _get_acta_project(db, meeting_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    meeting = await db.get(CommitteeMeeting, meeting_id)
    if (
        meeting is None
        or meeting.deleted_at is not None
        or meeting.admin_curation_status != "sent_to_client"
    ):
        raise HTTPException(status_code=404, detail="Acta no visible")
    return _to_out(meeting)


@router.post(
    "/{meeting_id}/review",
    response_model=ActaClientOut,
)
async def review_acta(
    meeting_id: uuid.UUID,
    body: ActaReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> ActaClientOut:
    """Cliente review action MixinA pattern."""
    project_id = await _get_acta_project(db, meeting_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    try:
        meeting = await _service(db).mark_client_review(
            meeting_id=meeting_id,
            action=body.action,
            note=body.note,
            user_id=user.id,
        )
    except (
        InvalidReviewActionError,
        ActaNotFoundError,
        ActasError,
    ) as exc:
        raise _handle_service_error(exc) from exc

    await db.commit()
    return _to_out(meeting)


@router.get(
    "/{meeting_id}/document-hash",
    response_model=ActaDocumentHashOut,
)
async def get_acta_hash(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> ActaDocumentHashOut:
    """SHA256 canonical · pre-firma input M05."""
    project_id = await _get_acta_project(db, meeting_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    try:
        doc_hash, canonical_length = await _service(db).compute_acta_hash(
            meeting_id,
        )
    except ActaNotFoundError as exc:
        raise _handle_service_error(exc) from exc

    meeting = await db.get(CommitteeMeeting, meeting_id)
    assert meeting is not None
    ready = (
        meeting.admin_curation_status == "sent_to_client"
        and meeting.client_reviewed_at is not None
        and meeting.client_signing_intent_id is None
    )

    return ActaDocumentHashOut(
        meeting_id=meeting_id,
        acta_subtype=meeting.acta_subtype,
        canonical_length=canonical_length,
        document_hash_sha256=doc_hash,
        ready_for_signing=ready,
    )


@router.post(
    "/{meeting_id}/finalize-signoff",
    response_model=ActaFinalizeSignoffOut,
)
async def finalize_acta_signoff(
    meeting_id: uuid.UUID,
    body: ActaFinalizeSignoffRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> ActaFinalizeSignoffOut:
    """Post-firma cliente · link signing_intent + firmas jsonb multi-sig append."""
    project_id = await _get_acta_project(db, meeting_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    intent = await db.get(SigningIntent, body.signing_intent_id)
    if intent is None:
        raise HTTPException(status_code=404, detail="SigningIntent no existe")
    if intent.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="SigningIntent no pertenece al project",
        )
    if intent.signable_type != "acta_comite":
        raise HTTPException(
            status_code=400,
            detail=(
                f"SigningIntent.signable_type='{intent.signable_type}' "
                f"esperado 'acta_comite'"
            ),
        )
    if intent.status != "signed":
        raise HTTPException(
            status_code=409,
            detail=f"SigningIntent status='{intent.status}' · esperado 'signed'",
        )

    try:
        meeting = await _service(db).process_acta_signoff(
            meeting_id=meeting_id,
            signing_intent_id=body.signing_intent_id,
        )
    except (ActaNotFoundError, ActaAlreadySignedError) as exc:
        raise _handle_service_error(exc) from exc

    await db.commit()

    return ActaFinalizeSignoffOut(
        meeting_id=meeting.id,
        signing_intent_id=body.signing_intent_id,
    )
