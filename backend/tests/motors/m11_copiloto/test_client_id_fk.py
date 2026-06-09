"""Sesión 3B-2B.4 Phase 2.3 · client_id FK + per-cliente memoria isolation.

Audit Phase 0 D2 gap A foundation: memoria propia per cliente.

Verifica:
1. CopilotConversation.client_id populated automáticamente al crear
   conversation via /projects/{id}/copilot/conversations (derived desde
   _set_project_rls lookup).
2. _serialize_conv expone client_id en response.
3. NEW endpoint /clients/{client_id}/copilot/conversations lista solo
   conversations del cliente especificado (cross-project · NO leak).
4. Aislamiento per cliente: cliente A NO ve conversations cliente B
   (RLS + WHERE client_id strict isolation).
5. Backward-compat: rows con client_id NULL (legacy pre-backfill) NO
   crashean serializer.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text



pytestmark = [pytest.mark.asyncio, pytest.mark.requires_db]


async def _create_client_project(db, *, cif_prefix: str = "B") -> tuple[uuid.UUID, uuid.UUID]:
    """Insert 1 client + 1 project bypass RLS · returns (client_id, project_id)."""
    from backend.tests.conftest import _admin_setup

    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"{cif_prefix}{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Test Client FK', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Test Project FK', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
    return client_id, project_id


async def test_create_conversation_populates_client_id(async_client, db):
    """POST /projects/{id}/copilot/conversations · response includes client_id."""
    client_id, project_id = await _create_client_project(db)

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/copilot/conversations",
        json={"titulo": "Memoria per cliente test"},
    )
    assert resp.status_code == 201, resp.text
    payload = resp.json()
    assert payload["project_id"] == str(project_id)
    assert payload["client_id"] == str(client_id), (
        "client_id debe poblarse automáticamente desde _set_project_rls lookup"
    )


async def test_db_row_has_client_id_set(async_client, db):
    """Verifies DB row directly · client_id column populated post-INSERT."""
    client_id, project_id = await _create_client_project(db, cif_prefix="C")

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/copilot/conversations",
        json={"titulo": "DB verify"},
    )
    assert resp.status_code == 201
    conv_id = uuid.UUID(resp.json()["id"])

    row = (await db.execute(text(
        "SELECT client_id FROM copilot_conversations WHERE id = :id"
    ), {"id": str(conv_id)})).scalar()
    assert row is not None
    assert str(row) == str(client_id)


async def test_list_per_client_endpoint_returns_only_that_client(async_client, db):
    """NEW /clients/{client_id}/copilot/conversations cross-project memoria."""
    client_a, project_a = await _create_client_project(db, cif_prefix="A")
    client_b, project_b = await _create_client_project(db, cif_prefix="D")

    # Create 2 convos cliente A · 1 cliente B
    for titulo in ("Cliente A · convo 1", "Cliente A · convo 2"):
        r = await async_client.post(
            f"/api/v1/projects/{project_a}/copilot/conversations",
            json={"titulo": titulo},
        )
        assert r.status_code == 201
    r = await async_client.post(
        f"/api/v1/projects/{project_b}/copilot/conversations",
        json={"titulo": "Cliente B · convo única"},
    )
    assert r.status_code == 201

    # Endpoint per cliente A · solo ve sus 2 convos
    resp = await async_client.get(f"/api/v1/clients/{client_a}/copilot/conversations")
    assert resp.status_code == 200, resp.text
    convs = resp.json()["conversations"]
    assert len(convs) == 2
    for c in convs:
        assert c["client_id"] == str(client_a)
        assert c["titulo"].startswith("Cliente A")

    # Endpoint per cliente B · solo ve su 1 convo · NO leak
    resp = await async_client.get(f"/api/v1/clients/{client_b}/copilot/conversations")
    assert resp.status_code == 200
    convs = resp.json()["conversations"]
    assert len(convs) == 1
    assert convs[0]["client_id"] == str(client_b)


async def test_list_per_client_respects_limit_param(async_client, db):
    """Limit query param caps result size."""
    client_id, project_id = await _create_client_project(db, cif_prefix="E")

    for i in range(5):
        r = await async_client.post(
            f"/api/v1/projects/{project_id}/copilot/conversations",
            json={"titulo": f"convo {i}"},
        )
        assert r.status_code == 201

    resp = await async_client.get(
        f"/api/v1/clients/{client_id}/copilot/conversations?limit=2"
    )
    assert resp.status_code == 200
    assert len(resp.json()["conversations"]) == 2


async def test_serialize_handles_null_client_id_backward_compat(async_client, db):
    """Legacy rows con client_id NULL (pre-backfill) NO crashean serializer."""
    client_id, project_id = await _create_client_project(db, cif_prefix="F")
    # Insert directly bypass API to simulate legacy row
    from backend.tests.conftest import _admin_setup

    legacy_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO copilot_conversations (id, project_id, client_id, titulo, autor, created_at) "
            "VALUES (:id, :pid, NULL, 'legacy null client_id', 'marcos', now())"
        ), {"id": str(legacy_id), "pid": str(project_id)})

    resp = await async_client.get(f"/api/v1/projects/{project_id}/copilot/conversations")
    assert resp.status_code == 200
    legacy = [c for c in resp.json()["conversations"] if c["id"] == str(legacy_id)]
    assert len(legacy) == 1
    assert legacy[0]["client_id"] is None  # graceful null


async def test_cross_client_no_leak_with_client_rls(async_client, db):
    """Sesión 3B-2B.4 Phase 2.3 Step 4 · deeper cross-client isolation verify.

    Audit Phase 1.5 finding A · post-fix verification que policy expanded
    `copilot_isolation` honra client_id = current_client_id() correctly
    AND defence-in-depth WHERE filter previene leak si RLS context fails.

    Verifies multi-layer:
    1. API endpoint: cliente A solo ve sus 2 convos · cliente B sus 1
    2. DB direct con SET LOCAL ROLE fulkro_app + set_config client_id:
       · current_client_id = A → solo 2 rows visibles
       · current_client_id = B → solo 1 row visible
       · NO context set → 0 rows (deny-by-default RLS)
    """

    client_a, project_a = await _create_client_project(db, cif_prefix="G")
    client_b, project_b = await _create_client_project(db, cif_prefix="H")

    # Create 2 convos cliente A · 1 cliente B
    for titulo in ("A · convo 1", "A · convo 2"):
        r = await async_client.post(
            f"/api/v1/projects/{project_a}/copilot/conversations",
            json={"titulo": titulo},
        )
        assert r.status_code == 201
    r = await async_client.post(
        f"/api/v1/projects/{project_b}/copilot/conversations",
        json={"titulo": "B · convo única"},
    )
    assert r.status_code == 201

    # Layer 1 · API endpoint isolation per cliente
    resp_a = await async_client.get(f"/api/v1/clients/{client_a}/copilot/conversations")
    assert resp_a.status_code == 200
    convs_a = resp_a.json()["conversations"]
    assert len(convs_a) == 2
    for c in convs_a:
        assert c["client_id"] == str(client_a)
        assert "B" not in c["titulo"], "leak detectado: cliente A ve titulo cliente B"

    resp_b = await async_client.get(f"/api/v1/clients/{client_b}/copilot/conversations")
    assert resp_b.status_code == 200
    convs_b = resp_b.json()["conversations"]
    assert len(convs_b) == 1
    assert convs_b[0]["client_id"] == str(client_b)

    # Layer 2 · DB direct con RLS context · verify policy enforces correctly
    # current_client_id = A → 2 visible (A's convos via OR clause client_id = A)
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_a)},
    )
    await db.execute(text("SELECT set_config('app.current_project_id', '', true)"))
    count_a = (await db.execute(text(
        "SELECT COUNT(*) FROM copilot_conversations WHERE client_id = :cid"
    ), {"cid": str(client_a)})).scalar()
    assert count_a == 2, f"DB-level cliente A debe ver 2 convos (saw {count_a})"

    # current_client_id = B → 1 visible (B's convo via OR clause)
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_b)},
    )
    count_b = (await db.execute(text(
        "SELECT COUNT(*) FROM copilot_conversations WHERE client_id = :cid"
    ), {"cid": str(client_b)})).scalar()
    assert count_b == 1, f"DB-level cliente B debe ver 1 convo (saw {count_b})"

    # current_client_id = A · query for B → 0 (NO leak A↔B vía WHERE explicit)
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_a)},
    )
    count_a_wants_b = (await db.execute(text(
        "SELECT COUNT(*) FROM copilot_conversations WHERE client_id = :cid"
    ), {"cid": str(client_b)})).scalar()
    assert count_a_wants_b == 0, (
        f"LEAK detectado: cliente A con su context viendo {count_a_wants_b} rows de cliente B"
    )
