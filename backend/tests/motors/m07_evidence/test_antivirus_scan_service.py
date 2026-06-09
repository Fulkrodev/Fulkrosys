"""Tests m07 antivirus_scan_service · SAN-E v3.MB-6 atom 6.

12 tests cubren:
  Scan primitives (mocked clamd):
    1. test_scan_bytes_clean_returns_clean (mock OK verdict)
    2. test_scan_bytes_eicar_returns_infected (mock FOUND verdict + virus name)
    3. test_scan_bytes_clamd_connection_error_raises
  Evidence workflow:
    4. test_scan_evidence_clean_updates_status_and_timestamps
    5. test_scan_evidence_infected_quarantines_file_and_emits_alert
    6. test_scan_evidence_error_emits_alert_and_marks_error
    7. test_scan_evidence_missing_file_marks_error
  Admin quarantine workflow (Q2 B):
    8. test_admin_release_quarantined_restores_file_and_status
    9. test_admin_release_blocks_non_quarantined_evidence
   10. test_admin_permanent_delete_removes_file_and_soft_deletes
  Listing + model helpers:
   11. test_list_quarantined_filters_correctly
   12. test_evidence_model_helpers_status_transitions
"""
from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m07_evidence.antivirus_scan_service import (
    EICAR_TEST_STRING,
    ClamdConnectionError,
    InvalidQuarantineActionError,
    SCAN_STATUS_VALUES,
    admin_permanent_delete_quarantined,
    admin_release_quarantined,
    list_quarantined,
    scan_bytes,
    scan_evidence,
)
from backend.tests.conftest import setup_test_project


_REPO_ROOT = Path(__file__).resolve().parents[4]
_EVIDENCES_DIR = _REPO_ROOT / "var" / "evidences"
_QUARANTINE_DIR = _REPO_ROOT / "var" / "quarantine"


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _mock_clamd_clean() -> MagicMock:
    mock = MagicMock()
    mock.version.return_value = "ClamAV 1.3.0/27000/Mon May 11 12:00:00 2026"
    mock.instream.return_value = {"stream": ("OK", None)}
    return mock


def _mock_clamd_infected(virus_name: str = "Eicar-Signature") -> MagicMock:
    mock = MagicMock()
    mock.version.return_value = "ClamAV 1.3.0/27000/Mon May 11 12:00:00 2026"
    mock.instream.return_value = {"stream": ("FOUND", virus_name)}
    return mock


def _mock_clamd_unreachable() -> MagicMock:
    mock = MagicMock()
    mock.version.side_effect = ConnectionError("clamd down")
    mock.instream.side_effect = ConnectionError("clamd down")
    return mock


async def _seed_evidence_row(
    db: AsyncSession,
    project_id: str,
    *,
    file_bytes: bytes = b"benign pdf content",
    scan_status: str = "scanning",
    file_name: str = "test.pdf",
) -> tuple[uuid.UUID, Path]:
    """Insert minimal evidence row + persist file to disk."""
    evidence_id = uuid.uuid4()
    project_dir = _EVIDENCES_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    abs_path = project_dir / f"{evidence_id}.pdf"
    abs_path.write_bytes(file_bytes)
    relative_path = f"var/evidences/{project_id}/{evidence_id}.pdf"

    await db.execute(
        sa_text(
            "INSERT INTO evidence (id, project_id, tipo, fichero_path, "
            "hash_sha256, vigente, fichero_nombre_original, "
            "fichero_tamano_bytes, scan_status, created_at) "
            "VALUES (:id, :pid, 'test', :path, 'deadbeef', TRUE, :name, "
            ":size, :status, now())"
        ),
        {
            "id": str(evidence_id),
            "pid": project_id,
            "path": relative_path,
            "name": file_name,
            "size": len(file_bytes),
            "status": scan_status,
        },
    )
    await db.flush()
    return evidence_id, abs_path


# ════════════════════════════════════════════════════════════════════
# Scan primitives
# ════════════════════════════════════════════════════════════════════


def test_scan_bytes_clean_returns_clean():
    mock = _mock_clamd_clean()
    result = scan_bytes(b"benign content", clamd_client=mock)

    assert result.status == "clean"
    assert result.virus_name is None
    assert result.engine_version is not None
    assert "ClamAV" in result.engine_version
    assert result.duration_ms >= 0


def test_scan_bytes_eicar_returns_infected():
    mock = _mock_clamd_infected("Eicar-Signature")
    result = scan_bytes(EICAR_TEST_STRING.encode(), clamd_client=mock)

    assert result.status == "infected"
    assert result.virus_name == "Eicar-Signature"
    assert result.engine_version is not None


def test_scan_bytes_clamd_connection_error_raises():
    mock = _mock_clamd_unreachable()
    with pytest.raises(ClamdConnectionError):
        scan_bytes(b"anything", clamd_client=mock)


# ════════════════════════════════════════════════════════════════════
# Evidence workflow
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_scan_evidence_clean_updates_status_and_timestamps(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    evidence_id, _ = await _seed_evidence_row(db, project_id)
    mock = _mock_clamd_clean()

    terminal = await scan_evidence(db, evidence_id, clamd_client=mock)

    assert terminal == "clean"
    row = await db.execute(
        sa_text(
            "SELECT scan_status, scan_started_at, scan_completed_at, "
            "scan_engine_version, scan_result_jsonb "
            "FROM evidence WHERE id = :id"
        ),
        {"id": str(evidence_id)},
    )
    hit = row.first()
    assert hit[0] == "clean"
    assert hit[1] is not None  # scan_started_at
    assert hit[2] is not None  # scan_completed_at
    assert "ClamAV" in (hit[3] or "")
    assert hit[4].get("status") == "clean"


@pytest.mark.asyncio
async def test_scan_evidence_infected_quarantines_file_and_emits_alert(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    evidence_id, original_abs = await _seed_evidence_row(
        db, project_id, file_bytes=EICAR_TEST_STRING.encode(),
    )
    mock = _mock_clamd_infected("Win.Test.EICAR_HDB-1")

    terminal = await scan_evidence(db, evidence_id, clamd_client=mock)

    assert terminal == "quarantined"
    row = await db.execute(
        sa_text(
            "SELECT scan_status, fichero_path, vigente, scan_result_jsonb "
            "FROM evidence WHERE id = :id"
        ),
        {"id": str(evidence_id)},
    )
    hit = row.first()
    assert hit[0] == "quarantined"
    assert hit[1].startswith("var/quarantine/")
    assert hit[2] is False
    assert hit[3]["virus_name"] == "Win.Test.EICAR_HDB-1"

    # File physically moved
    assert not original_abs.exists()
    quarantine_abs = _REPO_ROOT / hit[1]
    assert quarantine_abs.exists()

    # alert_queue row inserted
    alert_row = await db.execute(
        sa_text(
            "SELECT category, severity, metadata_jsonb FROM alert_queue "
            "WHERE project_id = :pid AND category = 'antivirus_infected'"
        ),
        {"pid": project_id},
    )
    alert_hit = alert_row.first()
    assert alert_hit is not None
    assert alert_hit[0] == "antivirus_infected"
    assert alert_hit[1] == "critical"
    assert alert_hit[2]["evidence_id"] == str(evidence_id)


@pytest.mark.asyncio
async def test_scan_evidence_error_emits_alert_and_marks_error(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    evidence_id, _ = await _seed_evidence_row(db, project_id)
    mock = _mock_clamd_unreachable()

    terminal = await scan_evidence(db, evidence_id, clamd_client=mock)

    assert terminal == "error"
    row = await db.execute(
        sa_text("SELECT scan_status FROM evidence WHERE id = :id"),
        {"id": str(evidence_id)},
    )
    assert row.scalar_one() == "error"

    alert_row = await db.execute(
        sa_text(
            "SELECT category FROM alert_queue "
            "WHERE project_id = :pid AND category = 'antivirus_scan_error'"
        ),
        {"pid": project_id},
    )
    assert alert_row.scalar_one_or_none() == "antivirus_scan_error"


@pytest.mark.asyncio
async def test_scan_evidence_missing_file_marks_error(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    evidence_id, abs_path = await _seed_evidence_row(db, project_id)
    abs_path.unlink()
    mock = _mock_clamd_clean()

    terminal = await scan_evidence(db, evidence_id, clamd_client=mock)

    assert terminal == "error"
    row = await db.execute(
        sa_text(
            "SELECT scan_status, scan_result_jsonb FROM evidence WHERE id = :id"
        ),
        {"id": str(evidence_id)},
    )
    hit = row.first()
    assert hit[0] == "error"
    assert "not found" in (hit[1].get("error_msg") or "").lower()


# ════════════════════════════════════════════════════════════════════
# Admin quarantine workflow (Q2 B)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_release_quarantined_restores_file_and_status(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    evidence_id, _ = await _seed_evidence_row(
        db, project_id, file_bytes=EICAR_TEST_STRING.encode(),
    )
    mock = _mock_clamd_infected()
    await scan_evidence(db, evidence_id, clamd_client=mock)

    admin_id = uuid.uuid4()
    await admin_release_quarantined(db, evidence_id, admin_id)

    row = await db.execute(
        sa_text(
            "SELECT scan_status, fichero_path, vigente, scan_result_jsonb "
            "FROM evidence WHERE id = :id"
        ),
        {"id": str(evidence_id)},
    )
    hit = row.first()
    assert hit[0] == "clean"
    assert hit[1].startswith("var/evidences/")
    assert hit[2] is True
    assert hit[3].get("admin_override") == "released_from_quarantine"
    assert hit[3].get("admin_user_id") == str(admin_id)


@pytest.mark.asyncio
async def test_admin_release_blocks_non_quarantined_evidence(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    evidence_id, _ = await _seed_evidence_row(
        db, project_id, scan_status="clean",
    )

    with pytest.raises(InvalidQuarantineActionError):
        await admin_release_quarantined(db, evidence_id, uuid.uuid4())


@pytest.mark.asyncio
async def test_admin_permanent_delete_removes_file_and_soft_deletes(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    evidence_id, _ = await _seed_evidence_row(
        db, project_id, file_bytes=EICAR_TEST_STRING.encode(),
    )
    mock = _mock_clamd_infected()
    await scan_evidence(db, evidence_id, clamd_client=mock)

    row = await db.execute(
        sa_text(
            "SELECT fichero_path FROM evidence WHERE id = :id"
        ),
        {"id": str(evidence_id)},
    )
    quarantine_path = row.scalar_one()
    quarantine_abs = _REPO_ROOT / quarantine_path
    assert quarantine_abs.exists()

    admin_id = uuid.uuid4()
    await admin_permanent_delete_quarantined(db, evidence_id, admin_id)

    # File deleted from disk
    assert not quarantine_abs.exists()

    # Evidence soft-deleted (deleted_at NOT NULL)
    row2 = await db.execute(
        sa_text(
            "SELECT deleted_at, vigente, scan_result_jsonb "
            "FROM evidence WHERE id = :id"
        ),
        {"id": str(evidence_id)},
    )
    hit = row2.first()
    assert hit[0] is not None
    assert hit[1] is False
    assert hit[2].get("admin_override") == "permanent_delete_from_quarantine"


# ════════════════════════════════════════════════════════════════════
# Listing + model helpers
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_quarantined_filters_correctly(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    # Mix: 1 quarantined + 1 clean + 1 scanning
    eid_q, _ = await _seed_evidence_row(
        db, project_id, file_bytes=EICAR_TEST_STRING.encode(),
    )
    await scan_evidence(db, eid_q, clamd_client=_mock_clamd_infected())

    eid_c, _ = await _seed_evidence_row(
        db, project_id, scan_status="clean", file_name="clean.pdf",
    )
    eid_s, _ = await _seed_evidence_row(
        db, project_id, scan_status="scanning", file_name="scanning.pdf",
    )

    listed = await list_quarantined(db, uuid.UUID(project_id))
    listed_ids = {r["id"] for r in listed}

    assert eid_q in listed_ids
    assert eid_c not in listed_ids
    assert eid_s not in listed_ids


def test_evidence_model_helpers_status_transitions():
    """Properties is_clean/is_quarantined/is_scan_pending/is_infected."""
    from backend.app.models.documents import Evidence

    assert set(SCAN_STATUS_VALUES) == {
        "clean", "scanning", "infected", "error", "quarantined",
    }

    e = Evidence()
    e.scan_status = "clean"
    assert e.is_clean is True
    assert e.is_quarantined is False
    assert e.is_scan_pending is False
    assert e.is_infected is False

    e.scan_status = "scanning"
    assert e.is_scan_pending is True
    assert e.is_clean is False

    e.scan_status = "quarantined"
    assert e.is_quarantined is True
    assert e.is_infected is True  # quarantined is treated infected for ENS
    assert e.is_clean is False

    e.scan_status = "infected"
    assert e.is_infected is True

    e.scan_status = "error"
    assert e.is_clean is False
    assert e.is_quarantined is False
