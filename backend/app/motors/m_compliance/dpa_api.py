"""DPA endpoints — Article 28 GDPR (atom 9.bis.3).

Two routers:

- ``dpa_public_router`` (no auth): GET /api/v1/legal/dpa-template/download
  streams the DOCX template populated with FULKRO controller data and
  placeholders for the cliente to fill.

- ``dpa_admin_router`` (require_owner): POST /api/v1/admin/clients/{id}/dpa/sign
  records the cliente's signed DPA (uploaded out-of-band to MinIO via
  M05 signing_intent + M06 evidence flow) and updates the clients row.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.core import Client
from backend.app.core.fiscal_identity import get_fiscal_identity
from backend.app.motors.m_compliance.dpa_template import (
    DPA_VERSION,
    build_dpa_docx,
)
from backend.app.motors.m_compliance.ropa_service import RoPAService


# ── Public download ────────────────────────────────────────────────────


dpa_public_router = APIRouter(prefix="/legal", tags=["MB-9.bis atom 3 — DPA"])


@dpa_public_router.get("/dpa-template/download")
async def download_dpa_template(
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Stream the DPA DOCX template with FULKRO data pre-populated."""
    fi = await get_fiscal_identity(db)
    # Anexo I sub-encargados derive from the canonical RoPA table (single
    # source of truth · punto #366) so the published DPA never drifts from
    # the independently-editable RoPA registry.
    sub_processors = await RoPAService(db).sub_processors_for_dpa()
    buf = build_dpa_docx(
        {
            "FULKRO_NOMBRE": fi.nombre_fiscal or "Marcos Mata García",
            "FULKRO_CIF": fi.nif,
            "FULKRO_DOMICILIO": fi.domicilio_completo or "Madrid (España)",
        },
        sub_processors=sub_processors or None,
    )
    headers = {
        "Content-Disposition": (
            f'attachment; filename="DPA_FULKRO_v{DPA_VERSION}.docx"'
        ),
    }
    return Response(
        content=buf.getvalue(),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers=headers,
    )


# ── Admin sign ─────────────────────────────────────────────────────────


dpa_admin_router = APIRouter(
    prefix="/admin/clients",
    tags=["MB-9.bis atom 3 — DPA admin"],
    dependencies=[Depends(require_owner)],
)


class DPASignBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    dpa_version: str = Field(default=DPA_VERSION, max_length=20)
    signed_minio_path: str = Field(min_length=1, max_length=1000)
    cliente_signature_timestamp: datetime
    fulkro_signature_timestamp: datetime | None = None


class DPASignResult(BaseModel):
    client_id: UUID
    dpa_signed_at: datetime
    dpa_version: str
    dpa_signed_minio_path: str


@dpa_admin_router.post(
    "/{client_id}/dpa/sign",
    response_model=DPASignResult,
    status_code=status.HTTP_200_OK,
)
async def record_dpa_signature(
    client_id: UUID,
    body: DPASignBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> DPASignResult:
    """Record a signed DPA against the cliente."""

    client = (
        await db.execute(select(Client).where(Client.id == client_id))
    ).scalar_one_or_none()
    if client is None:
        raise HTTPException(404, detail="Cliente not found")

    signed_at = body.fulkro_signature_timestamp or datetime.now(timezone.utc)
    await db.execute(
        update(Client)
        .where(Client.id == client_id)
        .values(
            dpa_signed_at=signed_at,
            dpa_version=body.dpa_version,
            dpa_signed_minio_path=body.signed_minio_path,
        )
    )
    await db.commit()

    refreshed = (
        await db.execute(select(Client).where(Client.id == client_id))
    ).scalar_one()

    return DPASignResult(
        client_id=refreshed.id,
        dpa_signed_at=refreshed.dpa_signed_at,
        dpa_version=refreshed.dpa_version,
        dpa_signed_minio_path=refreshed.dpa_signed_minio_path,
    )
