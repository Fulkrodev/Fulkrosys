"""Frente 2 · Pieza 1 · política de contraseña ClientUser (backend · autoridad).

8-16 caracteres + mayúscula + minúscula + número + símbolo · mensaje claro.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m21_portal_cliente import auth_service
from backend.app.motors.m21_portal_cliente.auth_service import (
    AuthError,
    validate_password_policy,
)
from backend.tests.conftest import setup_test_project

_CLARO = "entre 8 y 16"  # fragmento del mensaje único de la política


@pytest.mark.parametrize(
    "pw, motivo",
    [
        ("Ab1@", "corta (<8)"),
        ("Abcdefgh12345@xyz", "larga (>16)"),
        ("abcd1234@", "sin mayúscula"),
        ("ABCD1234@", "sin minúscula"),
        ("Abcdefg@", "sin número"),
        ("Abcd1234", "sin símbolo"),
    ],
)
def test_policy_rejects_each_case_with_clear_message(pw, motivo):
    with pytest.raises(AuthError) as exc:
        validate_password_policy(pw)
    assert _CLARO in str(exc.value), f"caso {motivo}: mensaje no claro"


def test_policy_accepts_valid():
    # 8 chars · A(mayús) bcd(minús) 123(núm) @(símbolo)
    validate_password_policy("Abcd123@")
    # 16 chars borde superior válido
    validate_password_policy("Abcdefghij12345@")


@pytest.mark.real_auth
@pytest.mark.asyncio
async def test_change_password_endpoint_enforces_policy(async_client, db):
    client_id_str, _p = await setup_test_project(db)
    _user, temp = await auth_service.create_user(
        db, uuid.UUID(client_id_str), "pw@example.com", "Cliente",
    )
    _u, token, csrf, _e = await auth_service.login(db, "pw@example.com", temp)
    await db.execute(text("RESET ROLE"))
    await db.flush()
    cookies = {"fulkro_session": token, "fulkro_csrf": csrf}
    headers = {"X-CSRF-Token": csrf}

    # Inválida → 400 con el mensaje claro (NO 422 genérico de Pydantic).
    r = await async_client.post(
        "/api/v1/client-auth/change-password",
        json={"old_password": temp, "new_password": "short"},
        cookies=cookies, headers=headers,
    )
    assert r.status_code == 400, r.text
    assert _CLARO in r.json()["detail"]

    # Válida (8-16 + 4 clases) → 200.
    r2 = await async_client.post(
        "/api/v1/client-auth/change-password",
        json={"old_password": temp, "new_password": "Abcd123@"},
        cookies=cookies, headers=headers,
    )
    assert r2.status_code == 200, r2.text
