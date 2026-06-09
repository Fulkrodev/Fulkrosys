"""M30 · project-scoped portal user creation API · sub-atom 1.C.F.1.

Endpoint admin idempotent para asegurar que un proyecto tiene 1 ClientUser
portal asociado (a su client_id parent). Reutiliza:

- ``m21.auth_service.create_user`` para alta ClientUser (ADR-013 v3 ·
  1 ClientUser activo por client).
- ``m30.project_scope_api`` para crear ClientContact project-scoped con
  ``has_portal_access=true`` (constraint v3 · 1 portal contact por proyecto).

Idempotente: si ya existe ClientUser activo para el client y/o contact
con portal en el project, retorna el estado sin duplicar nada.

RBAC: admin Marcos-only (``require_owner``).
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente import auth_service
from backend.app.motors.m21_portal_cliente.auth_service import AuthError
from backend.app.motors.m30_client_contacts.models import ClientContact


router = APIRouter(
    prefix="/projects/{project_id}/portal-user",
    tags=["Motor 30 - Project Portal User (1.C.F)"],
    dependencies=[Depends(require_owner)],
)


class EnsurePortalUserBody(BaseModel):
    """Body para asegurar usuario portal del proyecto.

    Si el client ya tiene un ClientUser activo (ADR-013 v3), se ignora el
    email/full_name y se reutiliza. Si NO existe, se crea uno con esos
    datos.

    ``create_contact``: si True (default), se crea también un ClientContact
    project-scoped con ``has_portal_access=true`` vinculado al ClientUser
    (constraint v3 m30: 1 portal contact por proyecto · idempotente).
    """

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    create_contact: bool = True


async def _get_client_id_for_project(
    project_id: uuid.UUID, db: AsyncSession,
) -> uuid.UUID:
    cid = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    if not cid:
        raise HTTPException(status_code=404, detail="Project not found")
    return cid if isinstance(cid, uuid.UUID) else uuid.UUID(str(cid))


@router.get("")
async def get_portal_user_status(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Status del usuario portal del proyecto (ClientUser + portal contact).

    Returns:
        {
            "project_id": str,
            "client_id": str,
            "client_user": {...} | None,
            "portal_contact": {...} | None,
            "complete": bool  # True si user+contact existen
        }
    """
    client_id = await _get_client_id_for_project(project_id, db)

    user = (await db.execute(
        select(ClientUser).where(
            ClientUser.client_id == client_id,
            ClientUser.deleted_at.is_(None),
            ClientUser.deactivated_at.is_(None),
        ).limit(1),
    )).scalar_one_or_none()

    contact = (await db.execute(
        select(ClientContact).where(
            ClientContact.project_id == project_id,
            ClientContact.has_portal_access.is_(True),
            ClientContact.deleted_at.is_(None),
        ).limit(1),
    )).scalar_one_or_none()

    return {
        "project_id": str(project_id),
        "client_id": str(client_id),
        "client_user": (
            {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "must_change_password": user.must_change_password,
                "last_login": (
                    user.last_login.isoformat() if user.last_login else None
                ),
            } if user else None
        ),
        "portal_contact": (
            {
                "id": str(contact.id),
                "full_name": contact.full_name,
                "email": contact.email,
                "role_title": contact.role_title,
                "role_category": contact.role_category,
                "client_user_id": (
                    str(contact.client_user_id)
                    if contact.client_user_id else None
                ),
            } if contact else None
        ),
        "complete": bool(user and contact),
    }


@router.post("", status_code=201)
async def ensure_portal_user(
    project_id: uuid.UUID,
    body: EnsurePortalUserBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Idempotente · asegura 1 ClientUser + (opcional) 1 portal contact.

    Algoritmo:

    1. Resuelve ``client_id`` desde ``project_id``.
    2. Busca ClientUser activo para ese client (ADR-013 v3 max 1).
       - Si existe · lo reutiliza.
       - Si NO existe · ``auth_service.create_user`` (genera temp password).
    3. Si ``create_contact`` (default True):
       - Busca ClientContact portal-access en este project.
       - Si existe · lo reutiliza · ajusta ``client_user_id`` si falta.
       - Si NO existe · crea ClientContact con ``has_portal_access=True``.
    4. Retorna estado completo + ``temp_password`` SOLO si user recién
       creado (admin debe enviarla al cliente vía resend-invite separado).
    """
    client_id = await _get_client_id_for_project(project_id, db)

    user = (await db.execute(
        select(ClientUser).where(
            ClientUser.client_id == client_id,
            ClientUser.deleted_at.is_(None),
            ClientUser.deactivated_at.is_(None),
        ).limit(1),
    )).scalar_one_or_none()

    temp_password: str | None = None
    created_user = False
    if user is None:
        try:
            user, temp_password = await auth_service.create_user(
                db,
                client_id=client_id,
                email=str(body.email),
                full_name=body.full_name,
            )
            created_user = True
        except AuthError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    contact: ClientContact | None = None
    created_contact = False
    if body.create_contact:
        contact = (await db.execute(
            select(ClientContact).where(
                ClientContact.project_id == project_id,
                ClientContact.has_portal_access.is_(True),
                ClientContact.deleted_at.is_(None),
            ).limit(1),
        )).scalar_one_or_none()

        if contact is None:
            contact = ClientContact(
                client_id=client_id,
                project_id=project_id,
                full_name=body.full_name,
                email=str(body.email).strip().lower(),
                role_title="Usuario portal",
                role_category="otros",
                has_portal_access=True,
                client_user_id=user.id,
            )
            db.add(contact)
            await db.flush()
            created_contact = True
        elif contact.client_user_id is None:
            contact.client_user_id = user.id
            await db.flush()

    await db.commit()

    return {
        "project_id": str(project_id),
        "client_id": str(client_id),
        "client_user_id": str(user.id),
        "portal_contact_id": str(contact.id) if contact else None,
        "created_user": created_user,
        "created_contact": created_contact,
        "temp_password": temp_password,
    }
