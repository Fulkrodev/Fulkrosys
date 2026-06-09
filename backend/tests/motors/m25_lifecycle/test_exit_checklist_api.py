"""Tests M25 Exit Checklist · ADR-046 v3 SAN-E.MB-3.A.

Cubre:
- Lazy seed: primera GET crea 16 default items (4 categorias x 4)
- Complete / uncomplete / set-status (no_aplica, bloqueado)
- check-readiness con criticos pendientes vs todos completados
- progress aggregation y by_category
"""
from __future__ import annotations

import uuid

import pytest

from backend.tests.conftest import setup_test_project


BASE = "/api/v1/projects"


@pytest.mark.asyncio
async def test_list_seeds_default_items(async_client, db):
    """H1: primera GET seeds 16 default items y devuelve progress."""
    _, project_id = await setup_test_project(db)
    r = await async_client.get(f"{BASE}/{project_id}/exit-checklist")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["project_id"] == project_id
    assert len(data["items"]) == 16
    assert data["progress"]["total"] == 16
    assert data["progress"]["completed"] == 0
    assert data["progress"]["completed_pct"] == 0.0
    categories = {it["category"] for it in data["items"]}
    assert categories == {"legal", "tecnico", "documentacion", "operacional"}
    by_cat = data["progress"]["by_category"]
    for cat in ("legal", "tecnico", "documentacion", "operacional"):
        assert by_cat[cat]["total"] == 4


@pytest.mark.asyncio
async def test_list_idempotent_no_double_seed(async_client, db):
    """H2: segunda GET NO duplica items."""
    _, project_id = await setup_test_project(db)
    r1 = await async_client.get(f"{BASE}/{project_id}/exit-checklist")
    r2 = await async_client.get(f"{BASE}/{project_id}/exit-checklist")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert len(r1.json()["items"]) == len(r2.json()["items"]) == 16


@pytest.mark.asyncio
async def test_complete_item_happy_path(async_client, db):
    """H3: complete marca status=completado, completed_at, completed_by."""
    _, project_id = await setup_test_project(db)
    listing = await async_client.get(f"{BASE}/{project_id}/exit-checklist")
    item = next(i for i in listing.json()["items"] if i["item_code"] == "contrato_firmado")
    r = await async_client.post(
        f"{BASE}/{project_id}/exit-checklist/{item['id']}/complete",
        json={"note": "Firmado e2e"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completado"
    assert body["completed_at"] is not None
    assert body["item_code"] == "contrato_firmado"


@pytest.mark.asyncio
async def test_uncomplete_item_resets(async_client, db):
    """H4: uncomplete revierte a pendiente y limpia completed_at."""
    _, project_id = await setup_test_project(db)
    listing = await async_client.get(f"{BASE}/{project_id}/exit-checklist")
    item = listing.json()["items"][0]
    await async_client.post(
        f"{BASE}/{project_id}/exit-checklist/{item['id']}/complete",
        json={},
    )
    r = await async_client.post(
        f"{BASE}/{project_id}/exit-checklist/{item['id']}/uncomplete",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "pendiente"


@pytest.mark.asyncio
async def test_set_status_no_aplica(async_client, db):
    """H5: set-status no_aplica permite descartar item del calculo readiness."""
    _, project_id = await setup_test_project(db)
    listing = await async_client.get(f"{BASE}/{project_id}/exit-checklist")
    item = next(i for i in listing.json()["items"] if i["item_code"] == "feedback_NPS")
    r = await async_client.post(
        f"{BASE}/{project_id}/exit-checklist/{item['id']}/set-status",
        json={"status": "no_aplica", "note": "Cliente declina NPS"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "no_aplica"


@pytest.mark.asyncio
async def test_check_readiness_blocked_by_default(async_client, db):
    """H6: readiness inicial NO ready_to_close porque criticos pendientes."""
    _, project_id = await setup_test_project(db)
    # Forzar seed
    await async_client.get(f"{BASE}/{project_id}/exit-checklist")
    r = await async_client.post(f"{BASE}/{project_id}/exit-checklist/check-readiness")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ready_to_close"] is False
    assert body["total"] == 16
    assert body["completed"] == 0
    assert len(body["blockers"]) >= 1
    # contrato_firmado es critico
    assert any("contrato_firmado".lower() in b.lower() or "Contrato" in b for b in body["blockers"])


@pytest.mark.asyncio
async def test_check_readiness_ready_when_all_critical_done(async_client, db):
    """H7: readiness ready_to_close=True cuando criticos completados o no_aplica."""
    from backend.app.motors.m25_lifecycle.exit_checklist_service import CRITICAL_ITEMS

    _, project_id = await setup_test_project(db)
    listing = await async_client.get(f"{BASE}/{project_id}/exit-checklist")
    items = listing.json()["items"]
    # Marcar todos los criticos como completados
    for it in items:
        if it["item_code"] in CRITICAL_ITEMS:
            r = await async_client.post(
                f"{BASE}/{project_id}/exit-checklist/{it['id']}/complete",
                json={},
            )
            assert r.status_code == 200, r.text
    # Marcar el resto como no_aplica para limpiar warnings
    for it in items:
        if it["item_code"] not in CRITICAL_ITEMS:
            r = await async_client.post(
                f"{BASE}/{project_id}/exit-checklist/{it['id']}/set-status",
                json={"status": "no_aplica"},
            )
            assert r.status_code == 200, r.text
    r = await async_client.post(f"{BASE}/{project_id}/exit-checklist/check-readiness")
    body = r.json()
    assert body["ready_to_close"] is True
    assert body["blockers"] == []
    assert body["completed"] == len(CRITICAL_ITEMS)


@pytest.mark.asyncio
async def test_complete_unknown_item_404(async_client, db):
    """H8: complete sobre item_id inexistente devuelve 404."""
    _, project_id = await setup_test_project(db)
    fake_id = str(uuid.uuid4())
    r = await async_client.post(
        f"{BASE}/{project_id}/exit-checklist/{fake_id}/complete",
        json={},
    )
    assert r.status_code == 404
