"""#23 Ola 5 · memoria conversacional · CRUD gaps + guard RLS project-scoped.

Cubre lo que test_client_id_fk (per-cliente) NO cubría:
- GET /copilot/projects devuelve el project_id REAL (NO client_id) · selector.
- get_conversation devuelve los mensajes en orden cronológico (recall).
- delete_conversation hace soft-delete (deleted_at) y desaparece de la lista.
- Aislamiento project-scoped bajo RLS (deny-by-default sin contexto).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text


pytestmark = [pytest.mark.asyncio, pytest.mark.requires_db]


async def _create_client_project(
    db, *, cif_prefix: str = "K", nombre: str = "Test CRUD",
) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert 1 client + 1 project bypass RLS · returns (client_id, project_id)."""
    from backend.tests.conftest import _admin_setup

    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"{cif_prefix}{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, :nombre, :cif, now())"
        ), {"id": str(client_id), "nombre": nombre, "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'CRUD Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
    return client_id, project_id


async def test_projects_endpoint_returns_real_project_id(async_client, db):
    """GET /copilot/projects · el selector trae project_id REAL (no client_id)."""
    client_id, project_id = await _create_client_project(
        db, cif_prefix="K", nombre="Cliente Selector",
    )

    resp = await async_client.get("/api/v1/copilot/projects")
    assert resp.status_code == 200, resp.text
    projects = resp.json()["projects"]
    match = [p for p in projects if p["project_id"] == str(project_id)]
    assert len(match) == 1, "el proyecto creado debe aparecer en el selector"
    # Regresión clave: el selector NO debe confundir project_id con client_id.
    assert match[0]["project_id"] != str(client_id)
    assert match[0]["cliente_nombre"] == "Cliente Selector"


async def test_get_conversation_returns_messages_in_order(async_client, db):
    """get_conversation devuelve los mensajes en orden cronológico (recall)."""
    _, project_id = await _create_client_project(db, cif_prefix="L")

    r = await async_client.post(
        f"/api/v1/projects/{project_id}/copilot/conversations",
        json={"titulo": "Memoria orden"},
    )
    assert r.status_code == 201, r.text
    conv_id = r.json()["id"]

    # Inserta 3 mensajes deterministas (bypass RLS · timestamps explícitos).
    from backend.tests.conftest import _admin_setup

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    seq = [("user", "hola"), ("assistant", "qué tal"), ("user", "bien")]
    async with _admin_setup(db):
        for i, (role, content) in enumerate(seq):
            await db.execute(text(
                "INSERT INTO copilot_messages "
                "(id, conversation_id, project_id, role, content, created_at) "
                "VALUES (:id, :cid, :pid, :role, :content, :ts)"
            ), {
                "id": str(uuid.uuid4()),
                "cid": conv_id,
                "pid": str(project_id),
                "role": role,
                "content": content,
                "ts": base + timedelta(minutes=i),
            })

    resp = await async_client.get(
        f"/api/v1/projects/{project_id}/copilot/conversations/{conv_id}"
    )
    assert resp.status_code == 200, resp.text
    msgs = resp.json()["messages"]
    assert [m["content"] for m in msgs] == ["hola", "qué tal", "bien"], (
        "los mensajes deben volver en orden cronológico ascendente"
    )


async def test_delete_conversation_soft_hides_from_list(async_client, db):
    """delete_conversation · soft delete (deleted_at) y fuera de la lista."""
    _, project_id = await _create_client_project(db, cif_prefix="M")

    r = await async_client.post(
        f"/api/v1/projects/{project_id}/copilot/conversations",
        json={"titulo": "a borrar"},
    )
    assert r.status_code == 201
    conv_id = r.json()["id"]

    d = await async_client.delete(
        f"/api/v1/projects/{project_id}/copilot/conversations/{conv_id}"
    )
    assert d.status_code == 200, d.text

    lst = await async_client.get(
        f"/api/v1/projects/{project_id}/copilot/conversations"
    )
    ids = [c["id"] for c in lst.json()["conversations"]]
    assert conv_id not in ids, "la conversación borrada no debe aparecer en la lista"

    from backend.tests.conftest import _admin_setup

    async with _admin_setup(db):
        deleted_at = (await db.execute(text(
            "SELECT deleted_at FROM copilot_conversations WHERE id = :id"
        ), {"id": conv_id})).scalar()
    assert deleted_at is not None, "soft delete · deleted_at debe estar seteado"


async def test_project_scoped_list_isolation_under_rls(async_client, db):
    """Guard empírico project-scoped · proyecto B NO ve conversaciones de A."""
    _, project_a = await _create_client_project(db, cif_prefix="N")
    _, project_b = await _create_client_project(db, cif_prefix="O")

    ra = await async_client.post(
        f"/api/v1/projects/{project_a}/copilot/conversations",
        json={"titulo": "A solo"},
    )
    assert ra.status_code == 201

    # Capa 1 · API: la lista de B no contiene la conversación de A.
    lb = await async_client.get(
        f"/api/v1/projects/{project_b}/copilot/conversations"
    )
    titles_b = [c["titulo"] for c in lb.json()["conversations"]]
    assert "A solo" not in titles_b

    # Capa 2 · DB directo bajo RLS (mirror test_cross_client_no_leak):
    #   contexto proyecto A → ve A · contexto B → 0 de A · sin contexto → 0.
    await db.execute(text("SELECT set_config('app.current_client_id', '', true)"))
    await db.execute(
        text("SELECT set_config('app.current_project_id', :p, true)"),
        {"p": str(project_a)},
    )
    count_a = (await db.execute(text(
        "SELECT COUNT(*) FROM copilot_conversations WHERE project_id = :p"
    ), {"p": str(project_a)})).scalar()
    assert count_a >= 1, f"contexto A debe ver su conversación (vio {count_a})"

    await db.execute(
        text("SELECT set_config('app.current_project_id', :p, true)"),
        {"p": str(project_b)},
    )
    count_b_sees_a = (await db.execute(text(
        "SELECT COUNT(*) FROM copilot_conversations WHERE project_id = :p"
    ), {"p": str(project_a)})).scalar()
    assert count_b_sees_a == 0, (
        f"LEAK: contexto proyecto B ve {count_b_sees_a} rows de proyecto A"
    )

    await db.execute(text("SELECT set_config('app.current_project_id', '', true)"))
    count_none = (await db.execute(text(
        "SELECT COUNT(*) FROM copilot_conversations WHERE project_id = :p"
    ), {"p": str(project_a)})).scalar()
    assert count_none == 0, "deny-by-default · sin contexto RLS, 0 rows"
