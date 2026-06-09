"""Admin branding API · MB-9 atom 9.1 Q6.B."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.motors.m21_portal_cliente.branding_service import (
    BrandingError,
    ClientBrandingService,
    ClientBrandingView,
)


router = APIRouter(
    prefix="/admin/clients",
    tags=["admin - Client Branding"],
    dependencies=[Depends(require_owner)],
)


class BrandingPatch(BaseModel):
    primary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    footer_text: Optional[str] = Field(None, max_length=500)
    unset_primary: bool = False
    unset_secondary: bool = False
    unset_footer: bool = False


def _view_to_dict(view: ClientBrandingView) -> dict:
    return {
        "client_id": view.client_id,
        "primary_color": view.primary_color,
        "secondary_color": view.secondary_color,
        "footer_text": view.footer_text,
        "logo_path": view.logo_path,
        "logo_mime_type": view.logo_mime_type,
        "has_logo": view.has_logo,
    }


@router.get("/{client_id}/branding")
async def get_branding(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = ClientBrandingService()
    view = await svc.get_for_client(db, client_id)
    if view is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return _view_to_dict(view)


@router.patch("/{client_id}/branding")
async def patch_branding(
    client_id: uuid.UUID,
    body: BrandingPatch,
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = ClientBrandingService()
    try:
        view = await svc.update_branding(
            db,
            client_id=client_id,
            primary_color=body.primary_color,
            secondary_color=body.secondary_color,
            footer_text=body.footer_text,
            unset_primary=body.unset_primary,
            unset_secondary=body.unset_secondary,
            unset_footer=body.unset_footer,
        )
    except BrandingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _view_to_dict(view)


@router.delete("/{client_id}/branding/logo")
async def delete_logo(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = ClientBrandingService()
    try:
        view = await svc.delete_logo(db, client_id)
    except BrandingError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return _view_to_dict(view)
