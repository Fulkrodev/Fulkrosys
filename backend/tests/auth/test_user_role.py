"""Tests columna role en User + factory make_user + constante ALLOWED_ROLES.

ADR-015 — role en BD (identidad invariante) vs capabilities en Settings
(toggles operacionales). Estos tests validan la parte BD del contrato.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.app.auth.constants import ALLOWED_ROLES, is_role_allowed
from backend.app.config import get_settings


@pytest.mark.asyncio
async def test_user_default_role_is_owner_via_server_default(db):
    """server_default 'owner' aplica a Marcos seed pre-existente.

    La migración a7f1e4b8c2d5 hizo INSERT INTO auth_users sin tocar la
    columna role (no existía). Tras migración c2af9c86c95d, el
    server_default rellena automáticamente 'owner' para users existentes.
    """
    # Email admin configurado (marcosmata@fulkro.es tras la rotación · migración
    # seed_admin_email_marcosmata_001) + email histórico, para ser robusto frente
    # a una BD de test reconstruida o aún sin la migración aplicada.
    admin_emails = [get_settings().marcos_admin_email, "marcos@fulkro.es"]
    result = await db.execute(
        text("SELECT role FROM auth_users WHERE email = ANY(:emails)"),
        {"emails": admin_emails},
    )
    row = result.first()
    assert row is not None, "admin seed (owner) no encontrado en BD"
    assert row[0] == "owner", f"admin role esperado 'owner', got {row[0]!r}"


@pytest.mark.asyncio
async def test_user_can_be_created_with_client_user_role(make_user):
    user = await make_user(role="client_user")
    assert user.role == "client_user"


@pytest.mark.asyncio
async def test_make_user_factory_default_role_is_client_user(make_user):
    """Factory default = client_user. Marcos owner es seed pre-existente
    en BD; otros usuarios creados sintéticamente arrancan como client_user
    salvo override explícito."""
    user = await make_user()
    assert user.role == "client_user"


def test_allowed_roles_constant_contains_5_values():
    assert ALLOWED_ROLES == frozenset(
        {
            "owner",
            "client_user",
            "partner_senior",
            "pentester_external",
            "introducer",
        }
    )
    assert is_role_allowed("owner") is True
    assert is_role_allowed("client_user") is True
    assert is_role_allowed("nonexistent") is False
    assert is_role_allowed("") is False
