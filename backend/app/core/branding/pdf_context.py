"""Reusable cliente branding PDF context builder.

Sesión 3B-2B.4 Phase 4 · audit Phase 0 D3 finding · PDF reports cliente-facing
lack ClientBranding (logo + colors + footer_text). Esta helper fetcha
ClientBranding desde DB, materializa logo desde MinIO a temp file, y devuelve
estructura uniforme para docxtpl + Jinja2 templates cross-motor (M21 diagnosis ·
M22 discovery · M14 contracts · M27 conformity).

Pattern reused desde m06_document_factory.service._materialise_client_logo
(proven working 96 templates · backward-compatible si branding sin set).

Usage:
    from backend.app.core.branding import build_branding_pdf_context

    branding = await build_branding_pdf_context(db, project_id)
    context["branding"] = branding.template_dict()
    if branding.logo_path:
        cliente_logo_path = branding.logo_path  # pass to render_docx
"""
from __future__ import annotations

import re
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

_MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
}


@dataclass(frozen=True)
class BrandingPdfContext:
    """Branding bundle ready para inject into template context.

    Attributes:
        client_id: Cliente UUID (string) o None si project sin client.
        client_name: Razón social cliente (fallback templates antes logo).
        logo_path: Path local temp file logo descargado MinIO (caller cleans up).
            None si cliente no tiene logo OR descarga falló (graceful · NO error).
        primary_color: Hex #RRGGBB validated o None.
        secondary_color: Hex #RRGGBB validated o None.
        footer_text: Footer max 500 chars o None.
    """

    client_id: str | None
    client_name: str | None
    logo_path: Path | None
    primary_color: str | None
    secondary_color: str | None
    footer_text: str | None

    def template_dict(self) -> dict[str, Any]:
        """Returns dict listo para inject en Jinja2/docxtpl context bajo `branding`."""
        return {
            "client_id": self.client_id,
            "client_name": self.client_name,
            "primary_color": self.primary_color or "",
            "secondary_color": self.secondary_color or "",
            "footer_text": self.footer_text or "",
            "has_logo": self.logo_path is not None,
        }


async def materialize_client_logo(
    db: AsyncSession, project_id: uuid.UUID
) -> tuple[Path | None, str | None]:
    """Download cliente logo desde MinIO a temp file · returns (logo_path, mime).

    Mirror de m06_document_factory.service._materialise_client_logo · extracted
    here para reuso cross-motor (Sesión 3B-2B.4 Phase 4 · OPS-026 DRY firmísimo).

    Returns (None, None) graceful si:
    - project sin client (orphan · unlikely)
    - cliente sin logo configurado (logo_path NULL)
    - MinIO get_object lanza exception (network · permission · NOT FATAL)

    Caller responsibility: Path.unlink() temp file post-render (NO leak).
    """
    row = await db.execute(sa_text(
        "SELECT c.logo_path, c.logo_mime_type "
        "FROM clients c JOIN projects p ON p.client_id = c.id "
        "WHERE p.id = :pid"
    ), {"pid": str(project_id)})
    hit = row.first()
    if not hit or not hit[0]:
        return None, None
    logo_ref, mime_type = hit[0], hit[1] or "image/png"

    try:
        bucket, _, key = logo_ref.partition("/")
        from backend.app.core.storage.minio_client import get_object

        payload = get_object(bucket, key)
    except Exception as exc:  # pragma: no cover · graceful fallback non-fatal
        logger.warning("Could not fetch client logo {}: {}", logo_ref, exc)
        return None, None

    ext = _MIME_TO_EXT.get(mime_type, ".png")
    tmp_path = Path(tempfile.mkstemp(prefix="fulkro_logo_", suffix=ext)[1])
    tmp_path.write_bytes(payload)
    return tmp_path, mime_type


async def build_branding_pdf_context(
    db: AsyncSession, project_id: uuid.UUID
) -> BrandingPdfContext:
    """Fetch ClientBranding + materialize logo para project_id.

    Returns empty-but-non-null BrandingPdfContext si:
    - project sin client (orphan)
    - cliente sin branding configured (todos campos NULL)
    - logo descarga falla (logo_path=None resto branding aún present)

    Graceful path · templates render con text fallback (cliente.razon_social
    uppercase) cuando logo_path es None · existing M06 _inject_brand pattern.
    """
    # Fetch cliente metadata + branding columns single query (1 round-trip).
    row = await db.execute(sa_text(
        "SELECT c.id, c.nombre, c.primary_color, c.secondary_color, c.footer_text "
        "FROM clients c JOIN projects p ON p.client_id = c.id "
        "WHERE p.id = :pid"
    ), {"pid": str(project_id)})
    hit = row.first()
    if not hit:
        return BrandingPdfContext(
            client_id=None,
            client_name=None,
            logo_path=None,
            primary_color=None,
            secondary_color=None,
            footer_text=None,
        )

    client_id_str = str(hit[0])
    client_name = hit[1]
    primary_color = hit[2] if hit[2] and _HEX_COLOR_RE.match(hit[2]) else None
    secondary_color = hit[3] if hit[3] and _HEX_COLOR_RE.match(hit[3]) else None
    footer_text = hit[4]

    # Materialize logo (graceful · None on failure)
    logo_path, _mime = await materialize_client_logo(db, project_id)

    return BrandingPdfContext(
        client_id=client_id_str,
        client_name=client_name,
        logo_path=logo_path,
        primary_color=primary_color,
        secondary_color=secondary_color,
        footer_text=footer_text,
    )
