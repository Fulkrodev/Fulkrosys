"""Cliente-facing GDPR data subject rights endpoints (atom 9.bis.2).

Three endpoints, all requiring a cliente authentication cookie:

- GET  /api/v1/portal/rgpd/access       (Art. 15 · ZIP descarga)
- POST /api/v1/portal/rgpd/erasure      (Art. 17 · request submission)
- GET  /api/v1/portal/rgpd/portability  (Art. 20 · JSON-LD)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import text

from backend.app.auth.dependencies import require_client_user
from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m_compliance.rgpd_services import (
    RGPDAccessService,
    RGPDErasureService,
    RGPDPortabilityService,
)


async def _set_cliente_tenant(db: AsyncSession, cliente: ClientUser) -> None:
    """Set ``app.current_client_id`` so RLS-protected SELECTs see the cliente."""
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(cliente.client_id)},
    )


router = APIRouter(
    prefix="/portal/rgpd",
    tags=["MB-9.bis atom 2 — Cliente RGPD rights"],
    dependencies=[Depends(require_client_user)],
)


# ── GET /access (Art. 15) ──────────────────────────────────────────────


@router.get("/access")
async def get_access_zip(
    db: AsyncSession = Depends(get_db),
    cliente: ClientUser = Depends(require_client_user),
) -> Response:
    """Return a ZIP with the cliente's cross-motor data."""
    await _set_cliente_tenant(db, cliente)
    buf = await RGPDAccessService(db).build_zip(cliente.id)
    filename = f"fulkro_export_{cliente.id}.zip"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── POST /erasure (Art. 17) ────────────────────────────────────────────


class ErasureRequestBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    reason: str | None = Field(default=None, max_length=2000)


class ErasureRequestOut(BaseModel):
    request_id: UUID
    status: str
    requested_at: datetime
    message: str


@router.post(
    "/erasure",
    response_model=ErasureRequestOut,
    status_code=status.HTTP_201_CREATED,
)
async def post_erasure_request(
    body: ErasureRequestBody,
    db: AsyncSession = Depends(get_db),
    cliente: ClientUser = Depends(require_client_user),
) -> ErasureRequestOut:
    await _set_cliente_tenant(db, cliente)
    svc = RGPDErasureService(db)
    row = await svc.request_erasure(
        cliente.id,
        tenant_client_id=cliente.client_id,
        reason=body.reason,
    )
    await db.commit()
    return ErasureRequestOut(
        request_id=row.id,
        status=row.status,
        requested_at=row.requested_at,
        message=(
            "Tu solicitud ha sido registrada. Será revisada por nuestro DPO "
            "y recibirás respuesta por email en un plazo máximo de 1 mes "
            "(Art. 12.3 RGPD)."
        ),
    )


# ── GET /portability (Art. 20) ─────────────────────────────────────────


@router.get("/portability")
async def get_portability_jsonld(
    db: AsyncSession = Depends(get_db),
    cliente: ClientUser = Depends(require_client_user),
) -> dict[str, Any]:
    """Return the cliente's data in machine-readable JSON-LD format."""
    await _set_cliente_tenant(db, cliente)
    return await RGPDPortabilityService(db).build_payload(cliente.id)
