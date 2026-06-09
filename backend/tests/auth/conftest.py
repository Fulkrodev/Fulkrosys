"""Fixtures compartidos tests auth — factory users sintéticos.

Pattern emergente FASE 3 S11: tests role-based necesitan crear users
con roles diferenciados (owner, client_user, partner_senior,
pentester_external, introducer) para validar middleware + dependencies
role-based. Factory reusable evita duplicar SQL crudo en cada test.

El factory hace ``db.flush()`` + ``db.refresh()`` (no ``commit``) para
mantener el patrón transaccional de ``backend/tests/conftest.py::db``
(rollback al final del test). NO se necesita cleanup explícito —
``trans.rollback()`` del fixture parent borra los inserts.

Aplica solo a tablas auth_* que no tienen RLS (ver docstring del
modelo User).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.crypto import hash_password
from backend.app.models.auth import User


# Credenciales fijas del seed user dedicado a tests auth API/RBAC.
# Email aislado del seed de producción dev para evitar acoplamiento
# test ↔ estado producción (SAN-A.A2.bis). Dominio @example.com porque
# pydantic email_validator rechaza TLDs reservados (.test, .invalid).
AUTH_SEED_EMAIL = "auth_seed_owner@example.com"
AUTH_SEED_PASSWORD = "TestP@ssw0rd-auth-seed!"
AUTH_SEED_DISPLAY_NAME = "Test Auth Seed Owner"


@pytest.fixture
def make_user(db: AsyncSession):
    """Factory: crea User sintético con role parametrizable.

    Uso:
        async def test_x(make_user):
            client = await make_user(role="client_user")
            assert client.role == "client_user"

            owner = await make_user(role="owner", email="extra-owner@x.test")
            assert owner.role == "owner"

    Args:
        email: si None, genera email aleatorio test-<uuid>@example.com
        role: default "client_user". Cualquier string en
            backend.app.auth.constants.ALLOWED_ROLES
        password: default "TestP@ssw0rd123!"
        display_name: default "Test User"
        is_active: default True
    """

    async def _make(
        email: str | None = None,
        role: str = "client_user",
        password: str = "TestP@ssw0rd123!",
        display_name: str = "Test User",
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email or f"test-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password(password),
            display_name=display_name,
            is_active=is_active,
            role=role,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    return _make


@pytest.fixture
async def auth_seed_user(db: AsyncSession) -> dict:
    """Usuario test dedicado para auth API/RBAC tests.

    Crea un User aislado con email y password fijos conocidos sin tocar
    el seed real de BD producción dev. Sin TOTP enrolled, sin WebAuthn,
    sin sesiones activas. Cleanup automático vía rollback transaccional
    del fixture ``db`` parent — no se persisten inserts ni aunque el
    test crashee a mitad.

    Returns:
        dict con keys:
            - id: str (uuid) del user creado
            - email: AUTH_SEED_EMAIL
            - password: AUTH_SEED_PASSWORD (plain, para login flow)
            - role: "owner"
            - display_name: AUTH_SEED_DISPLAY_NAME
            - user: instancia User SQLAlchemy
    """
    user = User(
        email=AUTH_SEED_EMAIL,
        password_hash=hash_password(AUTH_SEED_PASSWORD),
        display_name=AUTH_SEED_DISPLAY_NAME,
        is_active=True,
        role="owner",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return {
        "id": str(user.id),
        "email": AUTH_SEED_EMAIL,
        "password": AUTH_SEED_PASSWORD,
        "role": "owner",
        "display_name": AUTH_SEED_DISPLAY_NAME,
        "user": user,
    }
