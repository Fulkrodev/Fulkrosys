"""Tests for Motor 7 evidence ingestion pipeline.

Uses _admin_setup to bypass RLS for data setup and ingestion operations
since the evidence table has project_isolation RLS policy.
"""
import uuid
import shutil
from pathlib import Path

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup, setup_test_project
from backend.app.motors.m07_evidence.ingestion_service import (
    ingest_evidence,
    _EVIDENCES_DIR,
)
from backend.app.motors.m07_evidence.ingestion_types import (
    IngestionRequest,
    IngestionError,
)
from backend.app.motors.m07_evidence.signing import (
    reset_cache_for_tests,
)
from backend.app.motors.m07_evidence.catalog_loader import reset_cache


# A minimal valid PDF header (enough to pass as application/pdf content)
_FAKE_PDF = b"%PDF-1.4 fake content for testing purposes " + b"x" * 100


@pytest.fixture(autouse=True)
def _reset_signing_cache():
    """Reset signing cache before each test."""
    reset_cache_for_tests()
    reset_cache()
    yield
    reset_cache_for_tests()
    reset_cache()


@pytest.fixture
def cleanup_evidences():
    """Clean up evidence files written during tests."""
    dirs_to_clean: list[Path] = []
    yield dirs_to_clean
    for d in dirs_to_clean:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)


def _make_request(
    project_id: str,
    evidence_type_id: str = "EVT-politica_firmada-001",
    measure_code: str = "org.1",
    file_bytes: bytes = _FAKE_PDF,
    file_name: str = "politica_seguridad.pdf",
    mime_type: str = "application/pdf",
    **kwargs,
) -> IngestionRequest:
    return IngestionRequest(
        project_id=uuid.UUID(project_id),
        evidence_type_id=evidence_type_id,
        measure_code=measure_code,
        file_bytes=file_bytes,
        file_name=file_name,
        mime_type=mime_type,
        **kwargs,
    )


@pytest.mark.asyncio
class TestIngestionValidPDF:

    async def test_valid_pdf_ingestion_succeeds(self, db, cleanup_evidences):
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
        assert outcome.evidence_id is not None
        assert len(outcome.hash_sha256) == 64
        assert len(outcome.firma_ed25519_hex) == 128  # 64 bytes as hex
        assert outcome.evidence_type_id == "EVT-politica_firmada-001"
        assert outcome.nombre_tipo == "Politica firmada"
        assert outcome.fecha_caducidad is not None
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


@pytest.mark.asyncio
class TestIngestionMIMEValidation:

    async def test_wrong_mime_rejected(self, db):
        _, project_id = await setup_test_project(db)
        request = _make_request(
            project_id,
            mime_type="image/png",  # politica only allows PDF
        )
        with pytest.raises(IngestionError, match="INVALID_MIME"):
            async with _admin_setup(db):
                await ingest_evidence(db, request)


@pytest.mark.asyncio
class TestIngestionSizeValidation:

    async def test_oversized_file_rejected(self, db):
        _, project_id = await setup_test_project(db)
        # EVT-dmarc_dig-001 has 1MB limit
        big_data = b"x" * (2 * 1024 * 1024)  # 2 MB
        request = _make_request(
            project_id,
            evidence_type_id="EVT-dmarc_dig-001",
            measure_code="mp.com.1",
            file_bytes=big_data,
            file_name="dmarc.txt",
            mime_type="text/plain",
        )
        with pytest.raises(IngestionError, match="FILE_TOO_LARGE"):
            async with _admin_setup(db):
                await ingest_evidence(db, request)


@pytest.mark.asyncio
class TestIngestionTypeValidation:

    async def test_unknown_evidence_type_rejected(self, db):
        _, project_id = await setup_test_project(db)
        request = _make_request(
            project_id,
            evidence_type_id="EVT-nonexistent-999",
        )
        with pytest.raises(IngestionError, match="UNKNOWN_TYPE"):
            async with _admin_setup(db):
                await ingest_evidence(db, request)


@pytest.mark.asyncio
class TestIngestionMeasureValidation:

    async def test_unknown_measure_rejected(self, db):
        _, project_id = await setup_test_project(db)
        request = _make_request(
            project_id,
            measure_code="FAKE.99",
        )
        with pytest.raises(IngestionError, match="UNKNOWN_MEASURE"):
            async with _admin_setup(db):
                await ingest_evidence(db, request)


@pytest.mark.asyncio
class TestIngestionSignatureVerification:

    async def test_signature_verification_roundtrip_from_db(self, db, cleanup_evidences):
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
            # Read back from DB
            result = await db.execute(
                text("SELECT firma_ed25519, firma_payload_sha256 FROM evidence WHERE id = :id"),
                {"id": str(outcome.evidence_id)},
            )
        row = result.fetchone()
        assert row is not None
        firma_hex = row[0]
        # Verify it's a valid hex string
        sig_bytes = bytes.fromhex(firma_hex)
        assert len(sig_bytes) == 64
        # firma_payload_sha256 matches outcome
        assert row[1] == outcome.firma_payload_sha256
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


@pytest.mark.asyncio
class TestIngestionCaducidad:

    async def test_certificate_has_no_caducidad(self, db, cleanup_evidences):
        _, project_id = await setup_test_project(db)
        request = _make_request(
            project_id,
            evidence_type_id="EVT-certificado_ssl-001",
            measure_code="mp.com.2",
            file_bytes=b"-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----\n",
            file_name="server.pem",
            mime_type="application/x-pem-file",
        )
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
        assert outcome.fecha_caducidad is None
        cleanup_evidences.append(_EVIDENCES_DIR / project_id)


@pytest.mark.asyncio
class TestIngestionFilePersistence:

    async def test_file_written_to_disk(self, db, cleanup_evidences):
        _, project_id = await setup_test_project(db)
        request = _make_request(project_id)
        async with _admin_setup(db):
            outcome = await ingest_evidence(db, request)
        # Check file exists on disk
        expected_dir = _EVIDENCES_DIR / project_id
        files = list(expected_dir.iterdir())
        assert len(files) == 1
        assert files[0].read_bytes() == _FAKE_PDF
        cleanup_evidences.append(expected_dir)


@pytest.mark.asyncio
class TestIngestionEmptyFile:

    async def test_empty_file_rejected(self, db):
        _, project_id = await setup_test_project(db)
        request = _make_request(
            project_id,
            file_bytes=b"",
        )
        with pytest.raises(IngestionError, match="EMPTY_FILE"):
            async with _admin_setup(db):
                await ingest_evidence(db, request)
