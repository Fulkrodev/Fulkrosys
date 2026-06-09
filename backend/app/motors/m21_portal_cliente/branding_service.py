"""ClientBrandingService · MB-9 atom 9.1 Q1.B + Q2.C.

Per-cliente branding metadata (primary/secondary color + footer_text) +
MinIO-backed logo (logo_path already existing). Q5.3 cement: cliente NEVER
sees other clientes' brand · admin can read+update any client's brand.
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import Client


logger = logging.getLogger(__name__)


HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
FOOTER_MAX_LEN = 500


class BrandingError(Exception):
    """Validation or persistence error for branding service."""


@dataclass
class ClientBrandingView:
    client_id: str
    primary_color: Optional[str]
    secondary_color: Optional[str]
    footer_text: Optional[str]
    logo_path: Optional[str]
    logo_mime_type: Optional[str]
    has_logo: bool


def _to_view(client: Client) -> ClientBrandingView:
    return ClientBrandingView(
        client_id=str(client.id),
        primary_color=client.primary_color,
        secondary_color=client.secondary_color,
        footer_text=client.footer_text,
        logo_path=client.logo_path,
        logo_mime_type=client.logo_mime_type,
        has_logo=bool(client.logo_path),
    )


def validate_hex(color: Optional[str], field_name: str) -> None:
    if color is None:
        return
    if not HEX_COLOR_RE.match(color):
        raise BrandingError(
            f"{field_name} debe ser hex #RRGGBB (got {color!r})",
        )


def validate_footer(text: Optional[str]) -> None:
    if text is None:
        return
    if len(text) > FOOTER_MAX_LEN:
        raise BrandingError(
            f"footer_text excede {FOOTER_MAX_LEN} caracteres (got {len(text)})",
        )


class ClientBrandingService:
    """6 methods · per-cliente brand metadata + logo signed URL."""

    async def get_for_client(
        self, db: AsyncSession, client_id: uuid.UUID,
    ) -> Optional[ClientBrandingView]:
        client = (await db.execute(
            select(Client).where(Client.id == client_id)
        )).scalar_one_or_none()
        if client is None:
            return None
        return _to_view(client)

    async def get_for_project(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> Optional[ClientBrandingView]:
        """Resolve client via project FK · returns brand."""
        from sqlalchemy import text as sa_text

        row = (await db.execute(sa_text(
            "SELECT client_id FROM projects WHERE id = :pid"
        ), {"pid": str(project_id)})).first()
        if row is None:
            return None
        return await self.get_for_client(db, row[0])

    async def update_branding(
        self,
        db: AsyncSession,
        *,
        client_id: uuid.UUID,
        primary_color: Optional[str] = None,
        secondary_color: Optional[str] = None,
        footer_text: Optional[str] = None,
        unset_primary: bool = False,
        unset_secondary: bool = False,
        unset_footer: bool = False,
    ) -> ClientBrandingView:
        """Patch branding fields · only fields explicitly passed are touched.

        Pass ``unset_*=True`` to clear a field back to NULL.
        """
        client = (await db.execute(
            select(Client).where(Client.id == client_id)
        )).scalar_one_or_none()
        if client is None:
            raise BrandingError(f"Client {client_id} not found")

        if primary_color is not None:
            validate_hex(primary_color, "primary_color")
            client.primary_color = primary_color
        elif unset_primary:
            client.primary_color = None

        if secondary_color is not None:
            validate_hex(secondary_color, "secondary_color")
            client.secondary_color = secondary_color
        elif unset_secondary:
            client.secondary_color = None

        if footer_text is not None:
            validate_footer(footer_text)
            client.footer_text = footer_text
        elif unset_footer:
            client.footer_text = None

        await db.flush()
        return _to_view(client)

    async def delete_logo(
        self, db: AsyncSession, client_id: uuid.UUID,
    ) -> ClientBrandingView:
        """Clear logo_path + logo_mime_type + logo_sha256.

        Note: MinIO object removal is best-effort externally · here we
        clear DB references and let storage GC handle eventual removal.
        """
        client = (await db.execute(
            select(Client).where(Client.id == client_id)
        )).scalar_one_or_none()
        if client is None:
            raise BrandingError(f"Client {client_id} not found")
        client.logo_path = None
        client.logo_mime_type = None
        client.logo_sha256 = None
        await db.flush()
        return _to_view(client)

    def build_logo_url(self, logo_path: Optional[str]) -> Optional[str]:
        """Return a URL for the cliente to fetch the logo.

        For MVP this returns the existing API endpoint /api/v1/clients/{id}/logo
        which already proxies MinIO. Signed URLs deferred.
        """
        if not logo_path:
            return None
        # logo_path is stored as relative storage path · return null marker
        # so caller infers via API endpoint instead.
        return None
