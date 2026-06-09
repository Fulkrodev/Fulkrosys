"""Tests API integration GET /projects/{id}/feature-flags · sub-atom 1.C.C.A.

Verifica que el endpoint, tras cambiar la dep de ``require_owner`` a
``require_marcos_or_client``:
  - Cliente autenticado puede leer features de su propio proyecto (200).
  - Cliente autenticado obtiene 403 al intentar leer otro proyecto.

Marcos (admin pool) sigue accediendo igual que antes (require_marcos_or_client
admite ambos pools); no test explícito aquí porque las admin pages existentes
ya lo ejercitan en flujos manuales y los service-layer tests cubren la lógica.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.crypto import hash_password
from backend.tests.conftest import _admin_setup


pytestmark = [pytest.mark.asyncio, pytest.mark.real_auth]


async def _seed_client_user_with_project(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    categoria: str = "MEDIA",
) -> tuple[uuid.UUID, uuid.UUID]:
    """Seed Client + ClientUser + Project · returns (client_user_id, project_id)."""
    client_id = uuid.uuid4()
    cu_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'Test 1CC.A', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, "
                "categoria_objetivo, created_at) "
                "VALUES (:pid, :cid, 'Proj 1CC.A', :cat, now())"
            ),
            {"pid": str(project_id), "cid": str(client_id), "cat": categoria},
        )
        await db.execute(
            text(
                "INSERT INTO client_users (id, client_id, email, password_hash, "
                "full_name, created_at, must_change_password, failed_attempts) "
                "VALUES (:id, :cid, :em, :ph, 'T', now(), false, 0)"
            ),
            {
                "id": str(cu_id),
                "cid": str(client_id),
                "em": email,
                "ph": hash_password(password),
            },
        )
    await db.flush()
    return cu_id, project_id


async def test_client_user_can_read_own_project_feature_flags(
    async_client: AsyncClient,
    db: AsyncSession,
):
    """ClientUser autenticado lee feature-flags de su propio proyecto (200)."""
    email = f"client-1cca-own-{uuid.uuid4().hex[:8]}@example.com"
    password = "TestP@ssw0rd123!"
    _cu_id, project_id = await _seed_client_user_with_project(
        db, email=email, password=password, categoria="ALTA",
    )

    login = await async_client.post(
        "/api/v1/client-auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    res = await async_client.get(
        f"/api/v1/projects/{project_id}/feature-flags",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["categoria"] == "ALTA"
    # ALTA habilita alta_red_team per YAML (categoria_archetype_features.yaml).
    assert data["features"]["alta_red_team"] is True
    # BASICA-only feature debe estar OFF para proyecto ALTA.
    assert data["features"]["basica_autoevaluacion"] is False


async def test_client_user_gets_403_for_other_clients_project(
    async_client: AsyncClient,
    db: AsyncSession,
):
    """Cross-tenant isolation: 403 si project_id no pertenece al cliente."""
    password = "TestP@ssw0rd123!"
    # Lowercase emails: auth_service normaliza con `.lower()` antes de query.
    emailA = f"client-1cca-tenant-a-{uuid.uuid4().hex[:8]}@example.com"
    _cuA_id, _projectA_id = await _seed_client_user_with_project(
        db, email=emailA, password=password, categoria="BASICA",
    )
    emailB = f"client-1cca-tenant-b-{uuid.uuid4().hex[:8]}@example.com"
    _cuB_id, projectB_id = await _seed_client_user_with_project(
        db, email=emailB, password=password, categoria="MEDIA",
    )

    # Login como clienteA, intentar leer projectB.
    login = await async_client.post(
        "/api/v1/client-auth/login",
        json={"email": emailA, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    res = await async_client.get(
        f"/api/v1/projects/{projectB_id}/feature-flags",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403, res.text
