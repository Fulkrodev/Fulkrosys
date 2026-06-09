"""Tests M14 Providers + C-002 · ADR-046 v3 SAN-E.MB-3.B.

Cubre:
- CRUD providers (list, create, delete soft)
- Auto-detect cross-compliance: cloud+ALTO/CRITICO → ENS18+GDPR28
- cloud+CRITICO → +NIS2 (3 gaps)
- saas+MEDIO sin gaps
- C-002 status / gaps recompute / generate
- mark_reviewed update timestamp
"""
from __future__ import annotations


import pytest

from backend.tests.conftest import setup_test_project


BASE = "/api/v1/projects"


@pytest.mark.asyncio
async def test_list_providers_empty(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.get(f"{BASE}/{project_id}/providers")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["providers"] == []
    assert body["counts"]["total"] == 0


@pytest.mark.asyncio
async def test_create_provider_cloud_alto_detects_ens_gdpr(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/providers",
        json={
            "name": "AWS Spain",
            "type": "cloud",
            "scope": "Hosting datos sensibles ENS",
            "criticality": "ALTO",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "AWS Spain"
    assert body["c002_status"] == "pendiente"
    assert body["gaps_count"] == 2
    frameworks = {g["framework"] for g in body["auto_detected_gaps"]}
    assert frameworks == {"ENS", "GDPR"}


@pytest.mark.asyncio
async def test_create_provider_cloud_critico_adds_nis2(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/providers",
        json={
            "name": "Azure infra",
            "type": "cloud",
            "scope": "Plataforma critica",
            "criticality": "CRITICO",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["gaps_count"] == 3
    frameworks = {g["framework"] for g in body["auto_detected_gaps"]}
    assert frameworks == {"ENS", "GDPR", "NIS2"}


@pytest.mark.asyncio
async def test_create_provider_saas_medio_no_gaps(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/providers",
        json={
            "name": "Notion",
            "type": "saas",
            "scope": "Documentacion interna no sensible",
            "criticality": "MEDIO",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["gaps_count"] == 0
    assert body["auto_detected_gaps"] == []


@pytest.mark.asyncio
async def test_create_provider_invalid_type_422(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/providers",
        json={
            "name": "ProvX",
            "type": "invalid_type",
            "scope": "Algun scope",
            "criticality": "ALTO",
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_c002_status_pendiente(async_client, db):
    _, project_id = await setup_test_project(db)
    create = await async_client.post(
        f"{BASE}/{project_id}/providers",
        json={"name": "Notion", "type": "saas", "scope": "Docs internas", "criticality": "MEDIO"},
    )
    assert create.status_code == 201, create.text
    pid = create.json()["id"]
    r = await async_client.get(f"{BASE}/{project_id}/providers/{pid}/c002-status")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pendiente"
    assert r.json()["generated_at"] is None


@pytest.mark.asyncio
async def test_get_gaps_recomputes(async_client, db):
    _, project_id = await setup_test_project(db)
    create = await async_client.post(
        f"{BASE}/{project_id}/providers",
        json={"name": "AWS", "type": "cloud", "scope": "Hosting datos", "criticality": "ALTO"},
    )
    pid = create.json()["id"]
    r = await async_client.get(f"{BASE}/{project_id}/providers/{pid}/gaps")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["gaps_count"] == 2
    assert body["last_gap_check_at"] is not None


@pytest.mark.asyncio
async def test_generate_c002_marks_firmado(async_client, db):
    _, project_id = await setup_test_project(db)
    create = await async_client.post(
        f"{BASE}/{project_id}/providers",
        json={"name": "AWS", "type": "cloud", "scope": "Hosting datos", "criticality": "ALTO"},
    )
    pid = create.json()["id"]
    r = await async_client.post(f"{BASE}/{project_id}/providers/{pid}/c002/generate")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "firmado"
    assert body["generated_at"] is not None
    assert len(body["covered_gaps"]) == 2


@pytest.mark.asyncio
async def test_mark_reviewed_updates_timestamp(async_client, db):
    _, project_id = await setup_test_project(db)
    create = await async_client.post(
        f"{BASE}/{project_id}/providers",
        json={"name": "Notion", "type": "saas", "scope": "Docs internas", "criticality": "MEDIO"},
    )
    pid = create.json()["id"]
    r = await async_client.post(f"{BASE}/{project_id}/providers/{pid}/review")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["last_reviewed_at"] is not None


@pytest.mark.asyncio
async def test_delete_provider_soft(async_client, db):
    _, project_id = await setup_test_project(db)
    create = await async_client.post(
        f"{BASE}/{project_id}/providers",
        json={"name": "Notion", "type": "saas", "scope": "Docs internas", "criticality": "MEDIO"},
    )
    pid = create.json()["id"]
    r = await async_client.delete(f"{BASE}/{project_id}/providers/{pid}")
    assert r.status_code == 204
    listing = await async_client.get(f"{BASE}/{project_id}/providers")
    assert listing.json()["counts"]["total"] == 0


@pytest.mark.asyncio
async def test_list_counts_aggregate(async_client, db):
    _, project_id = await setup_test_project(db)
    await async_client.post(
        f"{BASE}/{project_id}/providers",
        json={"name": "AWS", "type": "cloud", "scope": "Hosting datos", "criticality": "CRITICO"},
    )
    await async_client.post(
        f"{BASE}/{project_id}/providers",
        json={"name": "Notion", "type": "saas", "scope": "Docs internas", "criticality": "MEDIO"},
    )
    r = await async_client.get(f"{BASE}/{project_id}/providers")
    counts = r.json()["counts"]
    assert counts["total"] == 2
    assert counts["critico"] == 1
    assert counts["con_gaps"] == 1
