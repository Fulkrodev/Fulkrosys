"""Tests for ClientBrandingService · MB-9 atom 9.1."""
import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m21_portal_cliente.branding_service import (
    BrandingError,
    ClientBrandingService,
    validate_hex,
    validate_footer,
)
from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


async def _seed_client(db) -> uuid.UUID:
    client_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Brand Co', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
    await db.flush()
    return client_id


def test_validate_hex_ok():
    validate_hex("#ABC123", "primary_color")
    validate_hex("#000000", "primary_color")
    validate_hex(None, "primary_color")


def test_validate_hex_invalid_raises():
    with pytest.raises(BrandingError):
        validate_hex("#XYZ", "primary_color")
    with pytest.raises(BrandingError):
        validate_hex("red", "primary_color")


def test_validate_footer_too_long():
    with pytest.raises(BrandingError):
        validate_footer("x" * 501)


def test_validate_footer_ok():
    validate_footer("Tu organización · contacto@cliente.com")
    validate_footer(None)


async def test_get_for_client_returns_view(db):
    cid = await _seed_client(db)
    svc = ClientBrandingService()
    view = await svc.get_for_client(db, cid)
    assert view is not None
    assert view.client_id == str(cid)
    assert view.primary_color is None
    assert view.has_logo is False


async def test_update_branding_colors_only(db):
    cid = await _seed_client(db)
    svc = ClientBrandingService()
    view = await svc.update_branding(
        db, client_id=cid,
        primary_color="#FF0000", secondary_color="#0000FF",
    )
    assert view.primary_color == "#FF0000"
    assert view.secondary_color == "#0000FF"


async def test_update_branding_invalid_color_raises(db):
    cid = await _seed_client(db)
    svc = ClientBrandingService()
    with pytest.raises(BrandingError):
        await svc.update_branding(
            db, client_id=cid, primary_color="not-hex",
        )


async def test_update_branding_footer_validates_length(db):
    cid = await _seed_client(db)
    svc = ClientBrandingService()
    with pytest.raises(BrandingError):
        await svc.update_branding(
            db, client_id=cid, footer_text="x" * 501,
        )


async def test_update_branding_unset_clears_fields(db):
    cid = await _seed_client(db)
    svc = ClientBrandingService()
    await svc.update_branding(
        db, client_id=cid, primary_color="#ABCDEF", footer_text="Test",
    )
    view = await svc.update_branding(
        db, client_id=cid, unset_primary=True, unset_footer=True,
    )
    assert view.primary_color is None
    assert view.footer_text is None


async def test_get_for_project_resolves_client(db):
    cid = await _seed_client(db)
    project_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
            "VALUES (:id, :cid, 'P', 'diagnostico', now())"
        ), {"id": str(project_id), "cid": str(cid)})
    await db.execute(
        text("SELECT set_config('app.current_client_id', :v, true)"),
        {"v": str(cid)},
    )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": str(project_id)},
    )
    await db.flush()

    svc = ClientBrandingService()
    await svc.update_branding(db, client_id=cid, primary_color="#123456")

    view = await svc.get_for_project(db, project_id)
    assert view is not None
    assert view.primary_color == "#123456"


async def test_delete_logo_clears_path_and_hash(db):
    cid = await _seed_client(db)
    async with _admin_setup(db):
        await db.execute(text(
            "UPDATE clients SET logo_path = 'clients/foo/logo.png', "
            "logo_mime_type = 'image/png', logo_sha256 = 'abc123' "
            "WHERE id = :id"
        ), {"id": str(cid)})
    await db.flush()

    svc = ClientBrandingService()
    view = await svc.delete_logo(db, cid)
    assert view.logo_path is None
    assert view.logo_mime_type is None
    assert view.has_logo is False


async def test_update_branding_unknown_client_raises(db):
    svc = ClientBrandingService()
    with pytest.raises(BrandingError):
        await svc.update_branding(
            db, client_id=uuid.uuid4(), primary_color="#ABCDEF",
        )
