"""Tests for Motor 7 evidence renewal service.

Uses _admin_setup to bypass RLS for data setup.
"""
import uuid
import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup, setup_test_project
from backend.app.motors.m07_evidence.renewal_service import (
    create_renewal_request,
    create_renewal_requests_from_freshness_report,
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
class TestRenewalCreation:

    async def test_creates_pending_request(self, db, cleanup_evidences):
        """Creates a pending renewal request for valid evidence."""
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
            result = await create_renewal_request(
                db, outcome.evidence_id, motivo="test_renewal"
            )
        assert result.created is True
        assert result.renewal_id is not None
        assert result.already_pending is False
        assert result.motivo == "test_renewal"
        assert result.error is None
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


@pytest.mark.asyncio
class TestRenewalIdempotent:

    async def test_idempotent_second_call(self, db, cleanup_evidences):
        """Second call returns same id without creating duplicate."""
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
            r1 = await create_renewal_request(
                db, outcome.evidence_id, motivo="test"
            )
            r2 = await create_renewal_request(
                db, outcome.evidence_id, motivo="test"
            )
        assert r1.created is True
        assert r2.created is False
        assert r2.already_pending is True
        assert r1.renewal_id == r2.renewal_id
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


@pytest.mark.asyncio
class TestRenewalUnknownEvidence:

    async def test_unknown_evidence_returns_error(self, db):
        """Unknown evidence_id returns an error outcome."""
        result = await create_renewal_request(db, uuid.uuid4())
        assert result.error == "Evidence not found"
        assert result.created is False
        assert result.renewal_id is None


@pytest.mark.asyncio
class TestRenewalAutoDetectsMotivo:

    async def test_auto_detects_motivo_caducada(self, db, cleanup_evidences):
        """Auto-detects motivo='caducada' when evidence is expired."""
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
            yesterday = date.today() - timedelta(days=1)
            await db.execute(
                text("UPDATE evidence SET fecha_caducidad = :fc WHERE id = :eid"),
                {"fc": yesterday, "eid": str(outcome.evidence_id)},
            )
            result = await create_renewal_request(db, outcome.evidence_id)
        assert result.motivo == "caducada"
        assert result.created is True
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


@pytest.mark.asyncio
class TestRenewalBatchFromFreshness:

    async def test_batch_from_freshness_report(self, db, cleanup_evidences):
        """Batch creates renewals for expiring/expired items."""
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
            # Make it expired
            yesterday = date.today() - timedelta(days=1)
            await db.execute(
                text("UPDATE evidence SET fecha_caducidad = :fc WHERE id = :eid"),
                {"fc": yesterday, "eid": str(outcome.evidence_id)},
            )
            outcomes = await create_renewal_requests_from_freshness_report(
                db, uuid.UUID(project_id)
            )
        assert len(outcomes) == 1
        assert outcomes[0].created is True
        assert outcomes[0].motivo == "caducada"
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)
