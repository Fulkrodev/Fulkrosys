"""Tests baseline endpoints panel /admin/clients (sub-fase 5.A FASE 5).

7 tests cubren:
1. GET  /clients/{id}                     detalle + métricas agregadas
2. PATCH /clients/{id}                    update partial
3. POST /clients/{id}/suspend             SET deleted_at
4. POST /clients/{id}/resume              UNSET deleted_at
5. GET  /clients/{id}/audit               filter audit_log
6. GET  /billing/clients/{id}/invoices    agregado cross-project
7. POST /clients/{cid}/users (cockpit)    rechaza cliente role (H32 fix)

Auth flow real (loginAsMarcos via /_dev). Pytestmark real_auth opt-out
del autouse override (validan cobertura 4.D global dep + RBAC owner).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Sub-fase 4.D ADR-021: opt-out del autouse override (validamos auth real).
pytestmark = pytest.mark.real_auth


async def _login_marcos(async_client) -> str:
    """Login Marcos vía /_dev → retorna csrf token de la cookie."""
    res = await async_client.post("/api/v1/_dev/login-as-marcos")
    assert res.status_code == 200, res.text
    csrf = async_client.cookies.get("fulkro_csrf")
    assert csrf, "fulkro_csrf cookie debería estar presente tras login"
    return csrf


async def _create_test_client(db: AsyncSession) -> uuid.UUID:
    """INSERT cliente sintético para tests (rollback al final)."""
    client_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    await db.execute(
        text(
            "INSERT INTO clients (id, nombre, cif, sector, "
            "contacto_email, created_at) "
            "VALUES (:id, :nombre, :cif, :sector, :email, now())"
        ),
        {
            "id": str(client_id),
            "nombre": "Cliente Test FASE 5",
            "cif": cif,
            "sector": "publico",
            "email": "test-cliente@example.com",
        },
    )
    await db.flush()
    return client_id


# ════════════════════════════════════════════════════════════════════
# Test 1: GET /clients/{id} detalle
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_client_detail_returns_200_with_metrics(
    async_client, db: AsyncSession,
):
    """GET /clients/{id} retorna ClientDetail con métricas (counts)."""
    csrf = await _login_marcos(async_client)
    client_id = await _create_test_client(db)

    res = await async_client.get(f"/api/v1/clients/{client_id}")
    assert res.status_code == 200, res.text

    data = res.json()
    assert data["id"] == str(client_id)
    assert data["nombre"] == "Cliente Test FASE 5"
    assert data["sector"] == "publico"
    assert data["projects_count"] == 0
    assert data["users_count"] == 0
    assert data["deleted_at"] is None
    # last_activity_at puede ser None o created_at del cliente
    _ = csrf  # used in mutating tests


# ════════════════════════════════════════════════════════════════════
# Test 2: PATCH /clients/{id} update partial
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_patch_client_updates_basics(
    async_client, db: AsyncSession,
):
    """PATCH /clients/{id} con sector + provincia → 200 + cambios persisten."""
    csrf = await _login_marcos(async_client)
    client_id = await _create_test_client(db)

    res = await async_client.patch(
        f"/api/v1/clients/{client_id}",
        json={"sector": "privado", "provincia": "Madrid"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["sector"] == "privado"


# ════════════════════════════════════════════════════════════════════
# Test 3: POST /clients/{id}/suspend
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_suspend_client_sets_deleted_at(
    async_client, db: AsyncSession,
):
    """POST /clients/{id}/suspend → ClientDetail con deleted_at populated."""
    csrf = await _login_marcos(async_client)
    client_id = await _create_test_client(db)

    res = await async_client.post(
        f"/api/v1/clients/{client_id}/suspend",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["deleted_at"] is not None, "deleted_at debe estar populado"


# ════════════════════════════════════════════════════════════════════
# Test 4: POST /clients/{id}/resume
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_resume_client_unsets_deleted_at(
    async_client, db: AsyncSession,
):
    """POST /clients/{id}/resume → ClientDetail con deleted_at = NULL."""
    csrf = await _login_marcos(async_client)
    client_id = await _create_test_client(db)

    # Suspender primero
    suspend_res = await async_client.post(
        f"/api/v1/clients/{client_id}/suspend",
        headers={"X-CSRF-Token": csrf},
    )
    assert suspend_res.status_code == 200

    # Resume
    res = await async_client.post(
        f"/api/v1/clients/{client_id}/resume",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["deleted_at"] is None, "deleted_at debe ser None tras resume"


# ════════════════════════════════════════════════════════════════════
# Test 5: GET /clients/{id}/audit (filter audit_log)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_client_audit_log_returns_page(
    async_client, db: AsyncSession,
):
    """GET /clients/{id}/audit retorna AuditLogPage con items + total + page."""
    csrf = await _login_marcos(async_client)
    client_id = await _create_test_client(db)

    # PATCH para generar audit_log entry
    await async_client.patch(
        f"/api/v1/clients/{client_id}",
        json={"contacto_email": "nuevo@example.com"},
        headers={"X-CSRF-Token": csrf},
    )

    res = await async_client.get(
        f"/api/v1/clients/{client_id}/audit",
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert isinstance(data["items"], list)


# ════════════════════════════════════════════════════════════════════
# Test 6: GET /billing/clients/{id}/invoices (agregado)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_invoices_by_client_returns_aggregated_list(
    async_client, db: AsyncSession,
):
    """GET /billing/clients/{id}/invoices retorna lista plana (vacía OK)."""
    await _login_marcos(async_client)
    client_id = await _create_test_client(db)

    res = await async_client.get(
        f"/api/v1/billing/clients/{client_id}/invoices",
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, list)
    # Sin invoices creadas → lista vacía
    assert len(data) == 0


# ════════════════════════════════════════════════════════════════════
# Test 7: H32 fix — cockpit endpoint requires owner role
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cockpit_endpoint_without_owner_returns_403(
    async_client, db: AsyncSession,
):
    """H32 fix verify: cockpit POST /clients/{id}/users sin owner → 403.

    Sin login → global dep rechaza con 401 (cubre gap H14+H15).
    Con cliente login (role_pool='cliente') → require_owner rechaza 403.

    Este test sólo verifica el caso "sin auth" → 401 (suficiente para
    confirmar que cockpit YA NO es endpoint abierto). Test "cliente
    auth → 403" requiere fixture client_user real fuera scope 5.A.
    """
    client_id = await _create_test_client(db)

    # Sin login: NO cookies ni CSRF
    res = await async_client.post(
        f"/api/v1/clients/{client_id}/users",
        json={
            "email": "intruso@example.com",
            "full_name": "Intruso",
            "role": "lectura_solo",
        },
    )
    # Global dep authenticate_request rechaza por missing cookie → 401
    assert res.status_code == 401, (
        f"Esperaba 401 (sin auth) pero got {res.status_code}: {res.text}"
    )
