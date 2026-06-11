"""Motor 30 — Client Contacts: REST API endpoints.

10 endpoints plan v4.2 FASE 5.5.C:
    GET    /clients/{client_id}/contacts                    list
    POST   /clients/{client_id}/contacts                    create
    GET    /clients/{client_id}/contacts/{contact_id}       detail
    PATCH  /clients/{client_id}/contacts/{contact_id}       update
    POST   /clients/{client_id}/contacts/{contact_id}/deactivate
    POST   /clients/{client_id}/contacts/{contact_id}/activate
    DELETE /clients/{client_id}/contacts/{contact_id}       hard delete
    GET    /clients/{client_id}/contacts/{contact_id}/timeline
    POST   /clients/{client_id}/contacts/import-csv
    GET    /clients/{client_id}/contacts/export-csv

RBAC: ``Depends(require_owner)`` router-level (M30 admin-only,
pattern canónico FASE 5.A + RBAC.D commit b5ae36f).
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m30_client_contacts.schemas import (
    ClientContactCreate,
    ClientContactListItem,
    ClientContactOut,
    ClientContactUpdate,
    TimelineEntryOut,
)
from backend.app.motors.m30_client_contacts.service import (
    ClientContactService,
    ContactNotFoundError,
    DuplicateContactEmailError,
)


async def _set_client_rls_context(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Fija el contexto RLS del cliente (FASE 0 fix · client_contacts es
    fail-closed ``tenant_isolation``).

    Antes los endpoints admin de M30 corrían como ``fulkro_app`` SIN contexto →
    la policy ``client_id = current_client_id() OR project_id =
    current_project_id()`` rechazaba INSERT/UPDATE (WITH CHECK) → 500 en prod.
    Como todo M30 está bajo ``/clients/{client_id}/contacts``, fijar
    ``current_client_id`` desde el path basta (más estricto que escalar a
    bypassrls: el contacto SIEMPRE queda atado al cliente del path)."""
    await set_tenant_context(db, client_id=client_id)


router = APIRouter(
    prefix="/clients/{client_id}/contacts",
    tags=["Motor 30 - Client Contacts"],
    dependencies=[Depends(require_owner), Depends(_set_client_rls_context)],
)


def _service(db: AsyncSession) -> ClientContactService:
    return ClientContactService(db)


def _resolve_user_id(request: Request) -> uuid.UUID | None:
    """Extrae user_id del auth_subject populado por authenticate_request.

    Si no hay subject (improbable post-FASE 4.D), devuelve None y deja
    que el trigger ``fn_audit_track`` registre ``audit_log.usuario`` vía
    ``current_setting('app.current_user', true)``.
    """
    subject = getattr(request.state, "auth_subject", None)
    if subject is None:
        return None
    user = getattr(subject, "user", None)
    if user is None:
        return None
    user_id = getattr(user, "id", None)
    if user_id is None:
        return None
    if isinstance(user_id, uuid.UUID):
        return user_id
    try:
        return uuid.UUID(str(user_id))
    except (TypeError, ValueError):
        return None


# ============================================================
# 1. List
# ============================================================


@router.get("", response_model=list[ClientContactListItem])
async def list_contacts(
    client_id: uuid.UUID,
    role_category: str | None = Query(None),
    is_active: bool | None = Query(True),
    is_signatory: bool | None = Query(None),
    search: str | None = Query(None, min_length=1, max_length=200),
    db: AsyncSession = Depends(get_db),
):
    """Listado contactos del cliente con filtros opcionales."""
    return await _service(db).list_contacts(
        client_id,
        role_category=role_category,
        is_active=is_active,
        is_signatory=is_signatory,
        search=search,
    )


# ============================================================
# 2. Create
# ============================================================


@router.post("", response_model=ClientContactOut, status_code=201)
async def create_contact(
    client_id: uuid.UUID,
    payload: ClientContactCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Crea un contacto. 409 si email duplicado para el cliente."""
    try:
        result = await _service(db).create_contact(
            client_id, payload,
            created_by_user_id=_resolve_user_id(request),
        )
    except DuplicateContactEmailError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.commit()
    return result


# ============================================================
# 3-9. /{contact_id} sub-resource
# ============================================================


@router.get(
    "/{contact_id}", response_model=ClientContactOut,
)
async def get_contact_detail(
    client_id: uuid.UUID,
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Detalle. 404 si no existe o eliminado (soft delete deleted_at)."""
    try:
        contact = await _service(db).get_contact_by_id(contact_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if contact.client_id != client_id:
        raise HTTPException(
            status_code=404, detail="Contacto no pertenece al cliente",
        )
    return contact


@router.patch(
    "/{contact_id}", response_model=ClientContactOut,
)
async def update_contact(
    client_id: uuid.UUID,
    contact_id: uuid.UUID,
    payload: ClientContactUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Actualización parcial PATCH semantics."""
    try:
        existing = await _service(db).get_contact_by_id(contact_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if existing.client_id != client_id:
        raise HTTPException(
            status_code=404, detail="Contacto no pertenece al cliente",
        )
    try:
        result = await _service(db).update_contact(contact_id, payload)
    except DuplicateContactEmailError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.commit()
    return result


@router.post(
    "/{contact_id}/deactivate", response_model=ClientContactOut,
)
async def deactivate_contact(
    client_id: uuid.UUID,
    contact_id: uuid.UUID,
    reason: Annotated[
        str, Body(..., embed=True, min_length=1, max_length=200)
    ],
    db: AsyncSession = Depends(get_db),
):
    """Marca is_active=False con motivo. Conserva interacciones."""
    try:
        existing = await _service(db).get_contact_by_id(contact_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if existing.client_id != client_id:
        raise HTTPException(
            status_code=404, detail="Contacto no pertenece al cliente",
        )
    result = await _service(db).deactivate_contact(contact_id, reason)
    await db.commit()
    return result


@router.post(
    "/{contact_id}/activate", response_model=ClientContactOut,
)
async def activate_contact(
    client_id: uuid.UUID,
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Re-activa contacto previamente desactivado."""
    try:
        existing = await _service(db).get_contact_by_id(contact_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if existing.client_id != client_id:
        raise HTTPException(
            status_code=404, detail="Contacto no pertenece al cliente",
        )
    result = await _service(db).activate_contact(contact_id)
    await db.commit()
    return result


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(
    client_id: uuid.UUID,
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Hard delete (FK CASCADE → elimina interactions). 204 No Content."""
    try:
        existing = await _service(db).get_contact_by_id(contact_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if existing.client_id != client_id:
        raise HTTPException(
            status_code=404, detail="Contacto no pertenece al cliente",
        )
    await _service(db).delete_contact_cascade(contact_id)
    await db.commit()


@router.get(
    "/{contact_id}/timeline",
    response_model=list[TimelineEntryOut],
)
async def get_contact_timeline(
    client_id: uuid.UUID,
    contact_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Timeline interacciones DESC. Limit 1-500."""
    try:
        existing = await _service(db).get_contact_by_id(contact_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if existing.client_id != client_id:
        raise HTTPException(
            status_code=404, detail="Contacto no pertenece al cliente",
        )
    return await _service(db).get_timeline(contact_id, limit=limit)


# ============================================================
# 10. CSV import / export
# ============================================================


@router.post("/import-csv", response_model=list[ClientContactOut])
async def import_contacts_csv(
    client_id: uuid.UUID,
    request: Request,
    csv_content: Annotated[
        str, Body(..., embed=True, min_length=10),
    ],
    db: AsyncSession = Depends(get_db),
):
    """Importa contactos desde body CSV string. Filas duplicadas (email)
    se omiten silenciosamente, devuelve los creados."""
    result = await _service(db).import_csv(
        client_id, csv_content,
        created_by_user_id=_resolve_user_id(request),
    )
    await db.commit()
    return result


@router.get("/export-csv", response_class=PlainTextResponse)
async def export_contacts_csv(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Exporta contactos del cliente a CSV plano (text/csv)."""
    csv_text = await _service(db).export_csv(client_id)
    return PlainTextResponse(content=csv_text, media_type="text/csv")


# ============================================================
# 11. Validación roles ENS canónicos (SAN-C.MB-9.5 · CCN-STIC 801)
# ============================================================


@router.get("/validate-roles-ens")
async def validate_roles_ens(
    client_id: uuid.UUID,
    target_category: str = Query("BASICA", pattern="^(BASICA|MEDIA|ALTA)$"),
    db: AsyncSession = Depends(get_db),
):
    """Valida segregación funcional de roles ENS para el cliente.

    Verifica:

    * **CCN-STIC 801**: RSEG y RSIS no pueden recaer en la misma persona
      (severity ``mayor``).
    * Roles obligatorios per categoría: BÁSICA exige RI/RS/RSEG/RSIS ·
      MEDIA añade POC · ALTA añade Comité Seguridad (severity ``menor``).

    Returns JSON con ``compliant: bool``, lista de ``violations`` y
    ``assigned_roles`` actuales. Útil pre-firma DdA y pre-auditoría externa.
    """
    from backend.app.motors.m30_client_contacts.roles_ens import (
        validate_role_segregation,
    )

    report = await validate_role_segregation(db, client_id, target_category)
    return {
        "client_id": str(report.client_id),
        "target_category": target_category,
        "compliant": report.compliant,
        "assigned_roles": {
            cat: [str(cid) for cid in ids]
            for cat, ids in report.assigned_roles.items()
        },
        "missing_roles": report.missing_roles,
        "violations": [
            {
                "rule": v.rule,
                "severity": v.severity,
                "detail": v.detail,
                "contact_ids": [str(cid) for cid in v.contact_ids],
            }
            for v in report.violations
        ],
    }
