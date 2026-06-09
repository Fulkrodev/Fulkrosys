"""Tests baseline logo upload endpoint (sub-bloque 4.A.3.a).

3 tests cubriendo:
1. Upload PNG válido → 200 + branding.logo_url poblado URL absoluta
2. Upload SVG → 422 (XSS attack vector blocked)
3. Upload PNG > 2MB → 422 (size cap)

audit_log integration via trigger ``tg_audit_admin_settings`` ya
testeado en test_settings_service.py — no duplicado aquí.
"""
from __future__ import annotations

import struct
import zlib
from io import BytesIO

import pytest

# Sub-fase 4.D ADR-021: opt-out del autouse override (validamos auth real).
pytestmark = pytest.mark.real_auth


def _build_minimal_png(extra_padding: int = 0) -> bytes:
    """Genera PNG válido mínimo (1x1 pixel) + padding opcional.

    Estructura PNG:
    - Signature: 8 bytes
    - IHDR chunk: 25 bytes
    - IDAT chunk: 12 bytes data
    - IEND chunk: 12 bytes

    Total minimal ~70 bytes. ``extra_padding`` añade bytes al final
    (técnicamente inválido PNG pero sirve para test de oversize:
    backend solo valida MIME + size, no contenido).
    """
    signature = b"\x89PNG\r\n\x1a\n"

    # IHDR: width=1, height=1, bit_depth=8, color_type=2 (RGB)
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data)
    ihdr = (
        struct.pack(">I", len(ihdr_data))
        + b"IHDR"
        + ihdr_data
        + struct.pack(">I", ihdr_crc)
    )

    # IDAT: deflate-compressed scanline (1 byte filter + 3 bytes RGB)
    idat_raw = b"\x00\xff\x00\x00"  # filter=0, RGB rojo
    idat_data = zlib.compress(idat_raw)
    idat_crc = zlib.crc32(b"IDAT" + idat_data)
    idat = (
        struct.pack(">I", len(idat_data))
        + b"IDAT"
        + idat_data
        + struct.pack(">I", idat_crc)
    )

    # IEND
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND"))

    return signature + ihdr + idat + iend + (b"\x00" * extra_padding)


# ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_logo_png_returns_200(async_client, make_user):
    """Upload PNG válido → 200 + branding.logo_url URL pública absoluta."""
    # Login Marcos via /_dev/login-as-marcos (cookies session+csrf)
    login = await async_client.post("/api/v1/_dev/login-as-marcos")
    assert login.status_code == 200
    csrf = async_client.cookies.get("fulkro_csrf")
    assert csrf, "csrf cookie debería estar presente"

    png_bytes = _build_minimal_png()
    files = {"file": ("logo.png", BytesIO(png_bytes), "image/png")}

    res = await async_client.post(
        "/api/v1/admin/settings/branding/logo",
        files=files,
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text

    data = res.json()
    logo_url = data["branding"].get("logo_url")
    assert logo_url, "branding.logo_url debe estar populado tras upload"
    assert "fulkro-admin-assets" in logo_url
    assert logo_url.endswith(".png")


@pytest.mark.asyncio
async def test_upload_logo_svg_returns_422(async_client):
    """Upload SVG → 422 (XSS attack vector blocked)."""
    login = await async_client.post("/api/v1/_dev/login-as-marcos")
    assert login.status_code == 200
    csrf = async_client.cookies.get("fulkro_csrf")

    svg_content = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    files = {"file": ("evil.svg", BytesIO(svg_content), "image/svg+xml")}

    res = await async_client.post(
        "/api/v1/admin/settings/branding/logo",
        files=files,
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert "MIME" in detail or "permitido" in detail.lower()


@pytest.mark.asyncio
async def test_upload_logo_oversize_returns_422(async_client):
    """Upload PNG > 2MB → 422 (size cap)."""
    login = await async_client.post("/api/v1/_dev/login-as-marcos")
    assert login.status_code == 200
    csrf = async_client.cookies.get("fulkro_csrf")

    # PNG válido + 3MB padding → total > 2MB cap
    oversize_bytes = _build_minimal_png(extra_padding=3 * 1024 * 1024)
    assert len(oversize_bytes) > 2 * 1024 * 1024

    files = {"file": ("big.png", BytesIO(oversize_bytes), "image/png")}
    res = await async_client.post(
        "/api/v1/admin/settings/branding/logo",
        files=files,
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert "tamaño" in detail.lower() or "size" in detail.lower()
