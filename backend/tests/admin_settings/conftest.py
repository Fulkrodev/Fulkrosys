"""Fixtures locales tests admin_settings.

``make_user`` factory: crea User sintético con role parametrizable.
Pattern coherente con ``backend/tests/auth/conftest.py::make_user``
(no se importa via cross-conftest porque pytest solo descubre
parents, no siblings).

Uso:
    async def test_x(db, make_user):
        owner = await make_user(role="owner", email="t@x.test")
        # owner es User instance lista para usar en service.update_section
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.crypto import hash_password
from backend.app.models.auth import User


@pytest.fixture
def make_user(db: AsyncSession):
    """Factory: crea User sintético role parametrizable.

    ``flush + refresh`` (no commit) — el fixture ``db`` mantiene
    transaction outer que rollback al final del test.

    Args:
        email: si None, genera test-<uuid>@example.com
        role: default "owner" (admin_settings tests requieren owner)
        password: default "TestP@ssw0rd123!"
        display_name: default "Test User Admin"
        is_active: default True
    """

    async def _make(
        email: str | None = None,
        role: str = "owner",
        password: str = "TestP@ssw0rd123!",
        display_name: str = "Test User Admin",
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
