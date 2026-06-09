"""Fixtures locales tests motor m21_portal_cliente.

make_client_user: factory para crear ClientUser sinteticos.
ADR-013 v3 single-user-RW: 1 user por cliente con acceso RW unico.

NO cleanup explicito: db fixture transaccional hace rollback al
final del test (auth_users + clients + client_users etc. son
gestionadas por la misma session bound a una transaccion).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.crypto import hash_password
from backend.app.models.client_portal import ClientUser
from backend.tests.conftest import _admin_setup


@pytest.fixture
def make_client_user(db: AsyncSession):
    """Factory: crea Client + ClientUser sinteticos.

    Cada llamada crea un Client nuevo + un ClientUser asociado para
    aislamiento entre tests. El FK client_id requiere clients table
    poblada; usamos _admin_setup para escapar RLS durante el INSERT
    en clients.

    Args:
        email: si None, genera test-client-<uuid>@example.com
        password: default "TestP@ssw0rd123!"
        must_change_password: default False
    """

    async def _make(
        email: str | None = None,
        password: str = "TestP@ssw0rd123!",
        must_change_password: bool = False,
    ) -> ClientUser:
        client_id = uuid.uuid4()
        unique_cif = f"B{uuid.uuid4().hex[:8].upper()}"
        email = email or f"test-client-{uuid.uuid4().hex[:8]}@example.com"
        async with _admin_setup(db):
            await db.execute(
                text(
                    "INSERT INTO clients (id, nombre, cif, created_at) "
                    "VALUES (:id, 'Test Client M21 Baseline', :cif, now())"
                ),
                {"id": str(client_id), "cif": unique_cif},
            )
            user = ClientUser(
                client_id=client_id,
                email=email,
                password_hash=hash_password(password),
                must_change_password=must_change_password,
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)
        # Set tenant context · client_users tiene RLS post-SAN-B.MB-2.1.
        await db.execute(
            text("SELECT set_config('app.current_client_id', :cid, true)"),
            {"cid": str(client_id)},
        )
        return user

    return _make
