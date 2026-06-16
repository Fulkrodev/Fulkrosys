"""Tests for Motor 7 evidence API endpoints.

Uses async_client fixture for HTTP testing. Pattern consistent
with M05 obligations test_api_endpoints.py.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from backend.tests.conftest import setup_test_project
from backend.app.motors.m07_evidence.ingestion_service import _EVIDENCES_DIR
from backend.app.motors.m07_evidence.signing import reset_cache_for_tests
from backend.app.motors.m07_evidence.catalog_loader import reset_cache

BASE = "/api/v1"

_FAKE_PDF = b"%PDF-1.4 fake content for testing purposes " + b"x" * 100


@pytest.fixture(autouse=True)
def _reset_caches():
    reset_cache_for_tests()
    reset_cache()
    yield
    reset_cache_for_tests()
    reset_cache()


@pytest.fixture
def cleanup_evidences():
    dirs_to_clean: list[Path] = []
    yield dirs_to_clean
    for d in dirs_to_clean:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)


class TestPublicKey:

    @pytest.mark.asyncio
    async def test_get_public_key_200(self, async_client, db):
        """GET /evidence/public-key returns 200 with PEM key."""
        r = await async_client.get(f"{BASE}/evidence/public-key")
        assert r.status_code == 200
        data = r.json()
        assert data["algorithm"] == "Ed25519"
        assert "BEGIN PUBLIC KEY" in data["public_key_pem"]


class TestUpload:

    @pytest.mark.asyncio
    async def test_post_upload_200(self, async_client, db, cleanup_evidences):
        """POST upload returns 200 with evidence details."""
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/evidence/projects/{project_id}/upload",
            files={"file": ("politica.pdf", _FAKE_PDF, "application/pdf")},
            data={
                "evidence_type_id": "EVT-politica_firmada-001",
                "measure_code": "org.1",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "evidence_id" in data
        assert len(data["hash_sha256"]) == 64
        assert len(data["firma_ed25519_hex"]) == 128
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)

    @pytest.mark.asyncio
    async def test_post_upload_wrong_mime_422(self, async_client, db):
        """POST upload con contenido suplantado se rechaza.

        'photo.png' con bytes 'fakepng' (no es PNG real) → la validación
        magic-bytes de borde lo rechaza con 415 (auditoría 2026-06-07);
        antes lo cazaba la ingestión más adentro con 422. Ambos son rechazos
        válidos del upload malicioso."""
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/evidence/projects/{project_id}/upload",
            files={"file": ("photo.png", b"fakepng", "image/png")},
            data={
                "evidence_type_id": "EVT-politica_firmada-001",
                "measure_code": "org.1",
            },
        )
        assert r.status_code in (415, 422)


class TestList:

    @pytest.mark.asyncio
    async def test_get_list_200(self, async_client, db, cleanup_evidences):
        """GET list returns 200 with items."""
        _, project_id = await setup_test_project(db)
        # Upload one evidence first
        await async_client.post(
            f"{BASE}/evidence/projects/{project_id}/upload",
            files={"file": ("politica.pdf", _FAKE_PDF, "application/pdf")},
            data={
                "evidence_type_id": "EVT-politica_firmada-001",
                "measure_code": "org.1",
            },
        )
        r = await async_client.get(
            f"{BASE}/evidence/projects/{project_id}/list"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


class TestExpiring:

    @pytest.mark.asyncio
    async def test_get_expiring_empty_200(self, async_client, db):
        """GET expiring for empty project returns 200."""
        _, project_id = await setup_test_project(db)
        r = await async_client.get(
            f"{BASE}/evidence/projects/{project_id}/expiring"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestUploadCatalog:

    @pytest.mark.asyncio
    async def test_get_upload_catalog_200(self, async_client, db):
        """Admin upload-catalog returns evidence types + applicable measures."""
        _, project_id = await setup_test_project(db)
        r = await async_client.get(
            f"{BASE}/evidence/projects/{project_id}/upload-catalog"
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["project_id"] == project_id
        # Evidence types catalog surfaced with the fields the FE form needs.
        assert len(data["evidence_types"]) >= 1
        first = data["evidence_types"][0]
        assert first["id"].startswith("EVT-")
        assert first["label"]
        assert isinstance(first["allowed_mime"], list)
        assert isinstance(first["allowed_extensions"], list)
        assert first["max_size_mb"] > 0
        # Applicable ENS measures present (full set when category is NULL).
        assert len(data["measures"]) >= 1
        codes = {m["codigo"] for m in data["measures"]}
        assert "org.1" in codes

    @pytest.mark.asyncio
    async def test_get_upload_catalog_unknown_project_404(self, async_client, db):
        """Unknown project id returns 404."""
        import uuid as _uuid

        r = await async_client.get(
            f"{BASE}/evidence/projects/{_uuid.uuid4()}/upload-catalog"
        )
        assert r.status_code == 404


class TestVerify:

    @pytest.mark.asyncio
    async def test_get_verify_ok_200(self, async_client, db, cleanup_evidences):
        """GET verify returns 200 with ok verdict."""
        _, project_id = await setup_test_project(db)
        # Upload evidence via API
        r_upload = await async_client.post(
            f"{BASE}/evidence/projects/{project_id}/upload",
            files={"file": ("politica.pdf", _FAKE_PDF, "application/pdf")},
            data={
                "evidence_type_id": "EVT-politica_firmada-001",
                "measure_code": "org.1",
            },
        )
        assert r_upload.status_code == 200
        evidence_id = r_upload.json()["evidence_id"]

        r = await async_client.get(
            f"{BASE}/evidence/projects/{project_id}/evidence/{evidence_id}/verify"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["verdict"] == "ok"
        assert data["hash_matches"] is True
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)
