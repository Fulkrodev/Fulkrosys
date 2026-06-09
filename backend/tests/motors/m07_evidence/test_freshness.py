"""Tests for Motor 7 evidence freshness service.

Uses _admin_setup to bypass RLS for data setup.
"""
import uuid
import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup, setup_test_project
from backend.app.motors.m07_evidence.freshness_service import (
    check_freshness_for_project,
    is_evidence_fresh,
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
class TestFreshnessEmptyProject:

    async def test_empty_project_returns_zeros(self, db):
        """Empty project returns report with all zeros."""
        _, project_id = await setup_test_project(db)
        report = await check_freshness_for_project(db, uuid.UUID(project_id))
        assert report.total == 0
        assert report.vigentes == 0
        assert report.caducadas == 0
        assert report.proxima_caducidad == 0
        assert report.sin_caducidad == 0
        assert report.items == []


@pytest.mark.asyncio
class TestFreshnessRecentEvidence:

    async def test_recent_evidence_is_vigente(self, db, cleanup_evidences):
        """Evidence with future fecha_caducidad is classified as vigente."""
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
            report = await check_freshness_for_project(db, uuid.UUID(project_id))
        assert report.total == 1
        assert report.vigentes + report.sin_caducidad >= 1
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


@pytest.mark.asyncio
class TestFreshnessExpiredEvidence:

    async def test_expired_evidence_detected(self, db, cleanup_evidences):
        """Evidence with past fecha_caducidad is classified as caducada."""
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
            # Set fecha_caducidad to yesterday
            yesterday = date.today() - timedelta(days=1)
            await db.execute(
                text("UPDATE evidence SET fecha_caducidad = :fc WHERE id = :eid"),
                {"fc": yesterday, "eid": str(outcome.evidence_id)},
            )
            report = await check_freshness_for_project(db, uuid.UUID(project_id))
        assert report.total == 1
        assert report.caducadas == 1
        assert report.items[0].estado == "caducada"
        assert report.items[0].dias_restantes is not None
        assert report.items[0].dias_restantes < 0
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


@pytest.mark.asyncio
class TestFreshnessProximaCaducidad:

    async def test_proxima_caducidad_detected(self, db, cleanup_evidences):
        """Evidence expiring within warning_days is proxima_caducidad."""
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
            # Set fecha_caducidad to 5 days from now
            near_future = date.today() + timedelta(days=5)
            await db.execute(
                text("UPDATE evidence SET fecha_caducidad = :fc WHERE id = :eid"),
                {"fc": near_future, "eid": str(outcome.evidence_id)},
            )
            report = await check_freshness_for_project(
                db, uuid.UUID(project_id), warning_days=30
            )
        assert report.total == 1
        assert report.proxima_caducidad == 1
        assert report.items[0].estado == "proxima_caducidad"
        assert report.items[0].dias_restantes == 5
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


@pytest.mark.asyncio
class TestIsEvidenceFreshTrue:

    async def test_is_evidence_fresh_true_for_recent(self, db, cleanup_evidences):
        """is_evidence_fresh returns True for non-expired evidence."""
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
            fresh, status = await is_evidence_fresh(db, outcome.evidence_id)
        assert fresh is True
        assert status is not None
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


@pytest.mark.asyncio
class TestIsEvidenceFreshFalse:

    async def test_is_evidence_fresh_false_for_expired(self, db, cleanup_evidences):
        """is_evidence_fresh returns False for expired evidence."""
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
            yesterday = date.today() - timedelta(days=1)
            await db.execute(
                text("UPDATE evidence SET fecha_caducidad = :fc WHERE id = :eid"),
                {"fc": yesterday, "eid": str(outcome.evidence_id)},
            )
            fresh, status = await is_evidence_fresh(db, outcome.evidence_id)
        assert fresh is False
        assert status is not None
        assert status.estado == "caducada"
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


@pytest.mark.asyncio
class TestIsEvidenceFreshNotFound:

    async def test_is_evidence_fresh_not_found(self, db):
        """is_evidence_fresh returns (False, None) for missing evidence."""
        fresh, status = await is_evidence_fresh(db, uuid.uuid4())
        assert fresh is False
        assert status is None
