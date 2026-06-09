"""Service layer Clients (sub-fase 5.A FASE 5).

Funciones añadidas para panel /admin/clients/{id}:
- ``get_client_by_id`` retorna ``ClientDetail`` con métricas agregadas
- ``update_client`` PATCH partial
- ``suspend_client`` / ``resume_client`` toggle ``deleted_at``
- ``get_client_audit_log`` query filtrada por client_id + projects asociados

Auth + audit_log.usuario poblados por ``authenticate_request`` global dep
(ADR-021). Estos métodos son puro CRUD/lookup sobre ``db: AsyncSession``.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_log import AuditLog
from backend.app.models.client_portal import ClientUser
from backend.app.models.commercial import Invoice
from backend.app.models.core import Client, Project


class ClientNotFoundError(Exception):
    """404 marker — el handler mappea a HTTPException."""


async def get_client_by_id(
    db: AsyncSession,
    client_id: uuid.UUID,
) -> dict[str, Any]:
    """Retorna detalle Client + métricas agregadas.

    Agrega:
    - ``projects_count``: COUNT(projects WHERE client_id)
    - ``users_count``: COUNT(client_users WHERE client_id)
    - ``last_activity_at``: MAX(updated_at) entre Client + Projects + Invoices

    Raises:
        ClientNotFoundError si no existe (incluso soft-deleted retorna —
        Marcos ve el cliente "suspendido" en el panel).
    """
    client = await db.get(Client, client_id)
    if client is None:
        raise ClientNotFoundError(f"Client {client_id} not found")

    projects_count = await db.scalar(
        select(func.count(Project.id)).where(
            Project.client_id == client_id,
            Project.deleted_at.is_(None),
        )
    ) or 0

    users_count = await db.scalar(
        select(func.count(ClientUser.id)).where(
            ClientUser.client_id == client_id,
            ClientUser.deactivated_at.is_(None),
        )
    ) or 0

    project_max = await db.scalar(
        select(func.max(Project.updated_at)).where(
            Project.client_id == client_id,
        )
    )
    invoice_max = await db.scalar(
        select(func.max(Invoice.updated_at)).where(
            Invoice.client_id == client_id,
        )
    )
    candidates = [client.updated_at, project_max, invoice_max]
    last_activity_at = max(
        (c for c in candidates if c is not None),
        default=None,
    )

    return {
        "id": client.id,
        "nombre": client.nombre,
        "cif": client.cif,
        "sector": client.sector,
        "provincia": client.provincia,
        "numero_empleados": client.numero_empleados,
        "contacto_email": client.contacto_email,
        "contacto_telefono": client.contacto_telefono,
        "lead_source": client.lead_source,
        "logo_path": client.logo_path,
        "created_at": client.created_at,
        "updated_at": client.updated_at,
        "deleted_at": client.deleted_at,
        "projects_count": projects_count,
        "users_count": users_count,
        "last_activity_at": last_activity_at,
    }


async def update_client(
    db: AsyncSession,
    client_id: uuid.UUID,
    payload: dict[str, Any],
) -> Client:
    """PATCH partial. Aplica solo los campos presentes en ``payload``.

    El trigger ``tg_audit_clients`` registra la mutación con
    ``usuario`` poblado por el global dep (set_config en
    ``authenticate_request``).
    """
    client = await db.get(Client, client_id)
    if client is None:
        raise ClientNotFoundError(f"Client {client_id} not found")

    for field, value in payload.items():
        setattr(client, field, value)

    await db.flush()
    await db.refresh(client)
    return client


async def suspend_client(
    db: AsyncSession,
    client_id: uuid.UUID,
) -> Client:
    """Soft delete: SET deleted_at = now() (idempotent).

    Política H2 (audit pre-FASE 5): reuse SoftDeleteMixin.deleted_at en
    lugar de añadir field nuevo. Trade-off colission semántica con "delete
    real" aceptable para MVP.
    """
    client = await db.get(Client, client_id)
    if client is None:
        raise ClientNotFoundError(f"Client {client_id} not found")

    if client.deleted_at is None:
        client.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(client)
    return client


async def resume_client(
    db: AsyncSession,
    client_id: uuid.UUID,
) -> Client:
    """Reactivar cliente suspendido: SET deleted_at = NULL."""
    client = await db.get(Client, client_id)
    if client is None:
        raise ClientNotFoundError(f"Client {client_id} not found")

    if client.deleted_at is not None:
        client.deleted_at = None
        await db.flush()
        await db.refresh(client)
    return client


async def get_client_audit_log(
    db: AsyncSession,
    client_id: uuid.UUID,
    page: int = 1,
    size: int = 25,
) -> tuple[list[AuditLog], int]:
    """Query ``audit_log`` filtrada por client_id + projects asociados.

    Tablas incluidas:
    - ``clients`` con ``registro_id == client_id``
    - ``projects`` con ``registro_id IN (project_ids del cliente)``
    - ``invoices`` con ``registro_id IN (invoice_ids del cliente)``

    Pagination ``page`` (1-indexed) + ``size`` (max 100).

    Returns:
        ``(items, total_count)``.
    """
    project_ids = await db.scalars(
        select(Project.id).where(Project.client_id == client_id)
    )
    project_ids_list = list(project_ids.all())

    invoice_ids = await db.scalars(
        select(Invoice.id).where(Invoice.client_id == client_id)
    )
    invoice_ids_list = list(invoice_ids.all())

    filter_clauses = [
        and_(AuditLog.tabla == "clients", AuditLog.registro_id == client_id),
    ]
    if project_ids_list:
        filter_clauses.append(
            and_(
                AuditLog.tabla == "projects",
                AuditLog.registro_id.in_(project_ids_list),
            )
        )
    if invoice_ids_list:
        filter_clauses.append(
            and_(
                AuditLog.tabla == "invoices",
                AuditLog.registro_id.in_(invoice_ids_list),
            )
        )

    where_clause = or_(*filter_clauses)

    total = await db.scalar(
        select(func.count(AuditLog.id)).where(where_clause)
    ) or 0

    offset = (page - 1) * size
    res = await db.execute(
        select(AuditLog)
        .where(where_clause)
        .order_by(AuditLog.timestamp.desc())
        .limit(size)
        .offset(offset)
    )
    return list(res.scalars().all()), total
