"""Tests for Motor 7 evidence verification service.

Uses _admin_setup to bypass RLS for data setup.
"""
import uuid
import shutil
from pathlib import Path

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup, setup_test_project
from backend.app.motors.m07_evidence.verification_service import (
    verify_evidence,
    _REPO_ROOT,
)
from backend.app.motors.m07_evidence.ingestion_service import (
    ingest_evidence,
    _EVIDENCES_DIR,
)
from backend.app.motors.m07_evidence.ingestion_types import IngestionRequest
from backend.app.motors.m07_evidence.signing import reset_cache_for_tests
from backend.app.motors.m07_evidence.catalog_loader import reset_cache


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


def _make_request(project_id: str, **kwargs) -> IngestionRequest:
    defaults = dict(
        project_id=uuid.UUID(project_id),
        evidence_type_id="EVT-politica_firmada-001",
        measure_code="org.1",
        file_bytes=_FAKE_PDF,
        file_name="politica_seguridad.pdf",
        mime_type="application/pdf",
    )
    defaults.update(kwargs)
    return IngestionRequest(**defaults)


@pytest.mark.asyncio
class TestVerifyOk:

    async def test_verify_ok_for_valid_evidence(self, db, cleanup_evidences):
        """Verification returns ok for unmodified evidence."""
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
            report = await verify_evidence(db, outcome.evidence_id)
        assert report.verdict == "ok"
        assert report.hash_matches is True
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


@pytest.mark.asyncio
class TestVerifyTampered:

    async def test_detects_tampered_file(self, db, cleanup_evidences):
        """Verification detects file modified on disk."""
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
            # Tamper with the file on disk
            file_path = _REPO_ROOT / outcome.fichero_path
            file_path.write_bytes(b"TAMPERED CONTENT")
            report = await verify_evidence(db, outcome.evidence_id)
        assert report.verdict == "tampered"
        assert report.hash_matches is False
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


@pytest.mark.asyncio
class TestVerifyMissing:

    async def test_detects_missing_file(self, db, cleanup_evidences):
        """Verification detects file deleted from disk."""
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
            # Delete the file from disk
            file_path = _REPO_ROOT / outcome.fichero_path
            file_path.unlink()
            report = await verify_evidence(db, outcome.evidence_id)
        assert report.verdict == "missing"
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


@pytest.mark.asyncio
class TestVerifyUnknown:

    async def test_unknown_evidence_id(self, db):
        """Verification returns unknown for non-existent evidence."""
        report = await verify_evidence(db, uuid.uuid4())
        assert report.verdict == "unknown"
        assert report.detail is not None
