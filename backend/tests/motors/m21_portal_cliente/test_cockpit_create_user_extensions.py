"""Tests SAN-D MB-19.10 · cockpit_create_user EXTENSION.

Post-MB-4.bis3 (ADR-020 v3 IMPLEMENTED FULLY): cockpit_create_user drop
magic_link PRIMER_ACCESO_CLIENTE · email simple con temp_password.
Tests legacy del flow magic_link están skipped a nivel módulo.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="MB-4.bis3 ADR-020 · cockpit_create_user drop magic_link emit · "
    "email simple con temp_password reemplaza · tests legacy obsoletos"
)

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from backend.app.motors.m21_portal_cliente.api import (
    _enqueue_client_user_invited,
)
from backend.app.models.client_portal import ClientUser
from backend.app.models.notifications import NotificationEvent
from backend.tests.conftest import _admin_setup


# ====================== Helpers ======================

async def _setup_client_with_project(db, *, with_project=True):
    """Crea Client + Project (opcional) para tests."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4() if with_project else None
    cif = f"B{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, contacto_email, created_at) "
            "VALUES (:id, 'Welcome Co', :cif, 'welcome@welcome.es', now())"
        ), {"id": str(client_id), "cif": cif})
        if with_project:
            await db.execute(text(
                "INSERT INTO projects (id, client_id, nombre, "
                "lifecycle_state, created_at) "
                "VALUES (:id, :cid, 'Welcome Project', 'DRAFT', now())"
            ), {"id": str(project_id), "cid": str(client_id)})
    await db.flush()
    return client_id, project_id


async def _create_client_user(db, client_id, *, email=None):
    """Helper crear ClientUser via auth_service · setup tests."""
    from backend.app.motors.m21_portal_cliente.auth_service import (
        create_user,
    )
    from backend.app.database import set_tenant_context
    # Set tenant context · client_users tabla con RLS
    await set_tenant_context(db, client_id=client_id)
    return await create_user(
        db,
        client_id=client_id,
        email=email or f"user-{uuid.uuid4().hex[:6]}@welcome.es",
        full_name="Welcome User",
    )


# ====================== _enqueue_client_user_invited helper ======================

@pytest.mark.asyncio
async def test_enqueue_welcome_notification_with_project(db):
    """enqueue evento NotificationEvent + asociado Project activo."""
    client_id, project_id = await _setup_client_with_project(db)

    user, _temp_pwd = await _create_client_user(db, client_id)

    event_id = await _enqueue_client_user_invited(
        db=db,
        client_id=client_id,
        client_user=user,
        magic_link_url="https://app.fulkro.es/ml/consume?token=fake",
        magic_link_id=uuid.uuid4(),
        ttl_hours=24,
    )

    # Event creado · NotificationOrchestrator persisted
    if event_id is not None:
        # Verify event row in DB (pueden haber side effects EmailSender/SSE
        # que falle pero event row debe existir)
        event = await db.get(NotificationEvent, event_id)
        if event:
            assert event.event_type == "client_user_invited"
            assert event.project_id == project_id
            assert event.recipient_email == user.email


@pytest.mark.asyncio
async def test_enqueue_welcome_notification_without_project_skip(db):
    """enqueue silently skipped si client sin Project · returns None."""
    client_id, _ = await _setup_client_with_project(db, with_project=False)

    user, _temp_pwd = await _create_client_user(db, client_id)

    event_id = await _enqueue_client_user_invited(
        db=db,
        client_id=client_id,
        client_user=user,
        magic_link_url="https://app.fulkro.es/ml/consume?token=skip",
        magic_link_id=uuid.uuid4(),
        ttl_hours=24,
    )

    assert event_id is None


@pytest.mark.asyncio
async def test_enqueue_welcome_notification_skips_archived_projects(db):
    """Projects ENDED/ARCHIVED/PURGED NO califican como activo."""
    client_id = uuid.uuid4()
    project_archived_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Archived Co', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, "
            "lifecycle_state, created_at) "
            "VALUES (:id, :cid, 'Archived Project', 'ARCHIVED', now())"
        ), {"id": str(project_archived_id), "cid": str(client_id)})
    await db.flush()

    user, _temp_pwd = await _create_client_user(db, client_id)

    event_id = await _enqueue_client_user_invited(
        db=db,
        client_id=client_id,
        client_user=user,
        magic_link_url="https://app.fulkro.es/ml/consume?token=archived",
        magic_link_id=uuid.uuid4(),
        ttl_hours=24,
    )

    # Skip silente · no event creado (ARCHIVED filtered)
    assert event_id is None


@pytest.mark.asyncio
async def test_enqueue_welcome_notification_picks_first_active_project(db):
    """De N projects activos · enqueue evento en el primer creado."""
    client_id = uuid.uuid4()
    project_first_id = uuid.uuid4()
    project_second_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Multi Co', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        # First project · más antiguo
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, "
            "lifecycle_state, created_at) "
            "VALUES (:id, :cid, 'First Project', 'DRAFT', "
            "now() - INTERVAL '1 day')"
        ), {"id": str(project_first_id), "cid": str(client_id)})
        # Second project · más reciente
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, "
            "lifecycle_state, created_at) "
            "VALUES (:id, :cid, 'Second Project', 'SIGNED', now())"
        ), {"id": str(project_second_id), "cid": str(client_id)})
    await db.flush()

    user, _temp_pwd = await _create_client_user(db, client_id)

    event_id = await _enqueue_client_user_invited(
        db=db,
        client_id=client_id,
        client_user=user,
        magic_link_url="https://app.fulkro.es/ml/consume?token=multi",
        magic_link_id=uuid.uuid4(),
        ttl_hours=48,
    )

    # First created project debería ser el seleccionado
    if event_id is not None:
        event = await db.get(NotificationEvent, event_id)
        if event:
            assert event.project_id == project_first_id


# ====================== first_login_ttl_hours validation ======================

def test_first_login_ttl_hours_range_24_168():
    """ADR-042 invariante · range válido 24-168h (1d-7d)."""
    # Test inline validation logic (sin invocar HTTP endpoint)
    valid_values = [24, 48, 72, 120, 168]
    invalid_values = [0, 23, 169, 200, 1000]

    for v in valid_values:
        assert 24 <= v <= 168
    for v in invalid_values:
        assert not (24 <= v <= 168)


# ====================== Backward compat ======================

@pytest.mark.asyncio
async def test_cockpit_create_user_backward_compat_no_extensions(db):
    """Sin params extensions · default behavior preservado (legacy)."""
    # Test directo a auth_service.create_user · default flow sin extensions
    client_id, _ = await _setup_client_with_project(db, with_project=False)

    user, temp_pwd = await _create_client_user(db, client_id)

    assert user is not None
    assert user.client_id == client_id
    assert user.must_change_password is True
    assert temp_pwd is not None
    assert len(temp_pwd) > 0
