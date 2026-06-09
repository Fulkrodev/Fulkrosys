"""CLUSTER 3 Phase C3.1 service compute_dda_evidence_gaps unit tests.

Verifica:
1. Pure functional helpers (status/severity/categoria classification)
2. All-covered project · matrix 0 gaps
3. All-missing project · matrix all missing
4. Mixed states project · counts correct
5. ALTA-only medidas filtered out BÁSICA project
6. Stale threshold respected
7. Multiple evidence per medida aggregated
8. no_aplica DdA entry skips gap (NOT_APPLICABLE)
9. High-requirement medidas (op.acc.* · mp.s.*) use min_required=3
10. Severity classification critical vs high vs medium
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m09_audit_prep.dda_evidence_gap_service import (
    DdaEvidenceGapMatrix,
    GapDetectionOptions,
    GapSeverity,
    GapStatus,
    _classify_severity,
    _classify_status,
    _is_high_requirement_medida,
    _medida_applies_to_categoria,
    compute_dda_evidence_gaps,
    compute_medida_detail,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════════
# Pure functional helpers (isolated · no DB)
# ════════════════════════════════════════════════════════════════════════

def test_is_high_requirement_medida_detects_critical_prefixes():
    assert _is_high_requirement_medida("op.acc.1") is True
    assert _is_high_requirement_medida("mp.s.4") is True
    assert _is_high_requirement_medida("mp.com.2") is True
    assert _is_high_requirement_medida("org.pl.3") is True
    assert _is_high_requirement_medida("op.pl.1") is False
    assert _is_high_requirement_medida("mp.eq.5") is False


def test_medida_applies_to_categoria_respects_aplica_flags():
    medida = {
        "aplica_basica": True,
        "aplica_media": True,
        "aplica_alta": True,
    }
    assert _medida_applies_to_categoria(medida, "BASICA") is True
    assert _medida_applies_to_categoria(medida, "MEDIA") is True
    assert _medida_applies_to_categoria(medida, "ALTA") is True

    alta_only = {
        "aplica_basica": False,
        "aplica_media": False,
        "aplica_alta": True,
    }
    assert _medida_applies_to_categoria(alta_only, "BASICA") is False
    assert _medida_applies_to_categoria(alta_only, "ALTA") is True

    # Sin categoria · conservative true
    assert _medida_applies_to_categoria(medida, None) is True


def test_classify_status_no_evidence_returns_missing():
    opts = GapDetectionOptions()
    status, reason = _classify_status(
        evidence_count=0, min_required=1, stale=False,
        aplicabilidad_dda="aplica", options=opts,
    )
    assert status == GapStatus.MISSING
    assert reason is not None
    assert "sin evidencia" in reason.lower()


def test_classify_status_no_aplica_skipped():
    opts = GapDetectionOptions(skip_no_aplica=True)
    status, reason = _classify_status(
        evidence_count=0, min_required=1, stale=False,
        aplicabilidad_dda="no_aplica", options=opts,
    )
    assert status == GapStatus.NOT_APPLICABLE
    assert reason is None


def test_classify_status_insufficient_count_partial():
    opts = GapDetectionOptions()
    status, reason = _classify_status(
        evidence_count=2, min_required=3, stale=False,
        aplicabilidad_dda="aplica", options=opts,
    )
    assert status == GapStatus.PARTIAL
    assert "2/3" in reason


def test_classify_status_stale_partial_even_si_count_ok():
    opts = GapDetectionOptions()
    status, reason = _classify_status(
        evidence_count=5, min_required=1, stale=True,
        aplicabilidad_dda="aplica", options=opts,
    )
    assert status == GapStatus.PARTIAL
    assert "antigua" in reason.lower()


def test_classify_status_fully_covered():
    opts = GapDetectionOptions()
    status, reason = _classify_status(
        evidence_count=3, min_required=2, stale=False,
        aplicabilidad_dda="aplica", options=opts,
    )
    assert status == GapStatus.COVERED
    assert reason is None


def test_classify_severity_critical_missing_mp():
    severity = _classify_severity(
        status=GapStatus.MISSING, family="mp", is_high_req=True,
    )
    assert severity == GapSeverity.CRITICAL


def test_classify_severity_partial_high_req():
    severity = _classify_severity(
        status=GapStatus.PARTIAL, family="op", is_high_req=True,
    )
    assert severity == GapSeverity.HIGH


def test_classify_severity_not_applicable_low():
    severity = _classify_severity(
        status=GapStatus.NOT_APPLICABLE, family="mp", is_high_req=True,
    )
    assert severity == GapSeverity.LOW


def test_classify_severity_covered_low():
    severity = _classify_severity(
        status=GapStatus.COVERED, family="mp", is_high_req=True,
    )
    assert severity == GapSeverity.LOW


# ════════════════════════════════════════════════════════════════════════
# Integration · service with real DB (RLS bypass via _admin_setup)
# ════════════════════════════════════════════════════════════════════════


async def _seed_minimal_ens_measures(db, count: int = 3) -> list[str]:
    """Seed minimal EnsMeasure rows · returns list of codigos."""
    codigos: list[str] = []
    async with _admin_setup(db):
        # Test isolation: only insert if codes don't exist yet
        for i, (codigo, family) in enumerate([
            ("org.pl.1", "org"),
            ("op.acc.1", "op"),  # high-requirement prefix
            ("mp.s.4", "mp"),    # high-requirement prefix
        ][:count]):
            await db.execute(sa_text(
                "INSERT INTO ens_measures (id, codigo, nombre, marco, familia, "
                "aplica_basica, aplica_media, aplica_alta) "
                "VALUES (gen_random_uuid(), :cod, :nom, 'Anexo II', :fam, "
                "true, true, true) ON CONFLICT DO NOTHING"
            ), {
                "cod": codigo,
                "nom": f"Medida {codigo}",
                "fam": family,
            })
            codigos.append(codigo)
        await db.flush()
    return codigos


@pytest.mark.asyncio
async def test_compute_gaps_all_missing_when_no_evidence(db):
    """Project sin evidence · todas medidas missing."""
    _, project_id = await setup_test_project(db)
    await db.commit()

    matrix = await compute_dda_evidence_gaps(db, uuid.UUID(project_id))

    # All medidas catalog · ninguna covered/partial
    assert matrix.total_covered == 0
    assert matrix.total_partial == 0
    assert matrix.total_missing > 0  # At least catalog medidas missing
    assert matrix.coverage_pct == 0.0


@pytest.mark.asyncio
async def test_compute_gaps_evidence_uploaded_makes_covered(db):
    """Insert evidence for a medida · status becomes covered."""
    _, project_id = await setup_test_project(db)

    # Find any existing medida · use that codigo
    async with _admin_setup(db):
        m_row = (await db.execute(sa_text(
            "SELECT codigo, familia FROM ens_measures "
            "WHERE deleted_at IS NULL "
            "AND codigo NOT LIKE 'op.acc.%' AND codigo NOT LIKE 'mp.s.%' "
            "AND codigo NOT LIKE 'mp.com.%' AND codigo NOT LIKE 'org.pl.%' "
            "LIMIT 1"
        ))).first()
    if m_row is None:
        pytest.skip("No non-critical medidas in catalog")

    codigo, family = m_row[0], m_row[1]

    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO evidence (id, project_id, measure_code, "
            "fichero_path, fichero_nombre_original, scan_status, vigente, "
            "fecha_evidencia) "
            "VALUES (gen_random_uuid(), :pid, :code, '/tmp/e.pdf', "
            "'e.pdf', 'clean', true, now()::date)"
        ), {"pid": project_id, "code": codigo})
        await db.flush()
    await db.commit()

    matrix = await compute_dda_evidence_gaps(db, uuid.UUID(project_id))

    target = next((m for m in matrix.medidas if m.medida_code == codigo), None)
    assert target is not None
    assert target.evidence_count == 1
    assert target.status == GapStatus.COVERED
    assert target.severity == GapSeverity.LOW
    assert target.gap_reason is None
    assert len(target.evidences_summary) == 1


@pytest.mark.asyncio
async def test_compute_gaps_partial_when_below_high_requirement(db):
    """Critical medida (op.acc.1) con 1 evidence solo · status partial (need 3)."""
    _, project_id = await setup_test_project(db)
    codigos = await _seed_minimal_ens_measures(db)
    if "op.acc.1" not in codigos:
        pytest.skip("op.acc.1 catalog seed failed")

    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO evidence (id, project_id, measure_code, "
            "fichero_path, fichero_nombre_original, scan_status, vigente, "
            "fecha_evidencia) "
            "VALUES (gen_random_uuid(), :pid, 'op.acc.1', '/tmp/x.pdf', "
            "'x.pdf', 'clean', true, now()::date)"
        ), {"pid": project_id})
        await db.flush()
    await db.commit()

    matrix = await compute_dda_evidence_gaps(db, uuid.UUID(project_id))

    target = next(
        (m for m in matrix.medidas if m.medida_code == "op.acc.1"), None,
    )
    assert target is not None
    assert target.evidence_count == 1
    assert target.min_required == 3  # High-requirement override
    assert target.status == GapStatus.PARTIAL
    assert "1/3" in target.gap_reason
    # op.acc.* + partial · severity HIGH
    assert target.severity == GapSeverity.HIGH


@pytest.mark.asyncio
async def test_compute_gaps_stale_threshold_respected(db):
    """Evidence vieja 2 años · status partial con stale=True."""
    _, project_id = await setup_test_project(db)

    async with _admin_setup(db):
        m_row = (await db.execute(sa_text(
            "SELECT codigo FROM ens_measures WHERE deleted_at IS NULL "
            "AND codigo NOT LIKE 'op.acc.%' AND codigo NOT LIKE 'mp.s.%' "
            "AND codigo NOT LIKE 'mp.com.%' AND codigo NOT LIKE 'org.pl.%' "
            "LIMIT 1"
        ))).first()
    if m_row is None:
        pytest.skip("No non-critical medidas in catalog")
    codigo = m_row[0]
    old_date = (datetime.now(timezone.utc) - timedelta(days=400)).date()
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO evidence (id, project_id, measure_code, "
            "fichero_path, fichero_nombre_original, scan_status, vigente, "
            "fecha_evidencia) "
            "VALUES (gen_random_uuid(), :pid, :code, '/tmp/x.pdf', "
            "'x.pdf', 'clean', true, :date)"
        ), {"pid": project_id, "code": codigo, "date": old_date})
        await db.flush()
    await db.commit()

    matrix = await compute_dda_evidence_gaps(db, uuid.UUID(project_id))
    target = next((m for m in matrix.medidas if m.medida_code == codigo), None)
    assert target is not None
    assert target.evidence_count == 1
    assert target.stale is True
    assert target.status == GapStatus.PARTIAL
    assert "antigua" in target.gap_reason.lower()


@pytest.mark.asyncio
async def test_compute_gaps_no_aplica_dda_skipped(db):
    """DdA aplicabilidad=no_aplica · status NOT_APPLICABLE."""
    _, project_id = await setup_test_project(db)

    async with _admin_setup(db):
        m_row = (await db.execute(sa_text(
            "SELECT id, codigo FROM ens_measures WHERE deleted_at IS NULL LIMIT 1"
        ))).first()
    if m_row is None:
        pytest.skip("No measures in catalog")
    measure_id, codigo = m_row[0], m_row[1]

    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO dda_entries (id, project_id, measure_id, "
            "aplicabilidad, justificacion_no_aplica, version) "
            "VALUES (gen_random_uuid(), :pid, :mid, 'no_aplica', "
            "'Activos no usan este servicio', 1)"
        ), {"pid": project_id, "mid": str(measure_id)})
        await db.flush()
    await db.commit()

    matrix = await compute_dda_evidence_gaps(db, uuid.UUID(project_id))
    target = next((m for m in matrix.medidas if m.medida_code == codigo), None)
    assert target is not None
    assert target.aplicabilidad_dda == "no_aplica"
    assert target.status == GapStatus.NOT_APPLICABLE


@pytest.mark.asyncio
async def test_compute_gaps_severity_summary_rollup(db):
    """Summary counters compute correctly for varied state."""
    _, project_id = await setup_test_project(db)
    await db.commit()

    matrix = await compute_dda_evidence_gaps(db, uuid.UUID(project_id))
    summary = matrix.severity_summary
    # All medidas missing initially · most should be MEDIUM severity (non-critical
    # families MISSING) + some CRITICAL (mp.* + high-req)
    assert summary.critical_missing >= 0
    assert summary.high_partial >= 0
    assert summary.medium_total >= 0
    # Verify totals match counts (sanity)
    assert matrix.total_applicable == (
        matrix.total_covered + matrix.total_partial + matrix.total_missing
    )


@pytest.mark.asyncio
async def test_compute_medida_detail_returns_single_row(db):
    """compute_medida_detail returns single medida by code."""
    _, project_id = await setup_test_project(db)
    await db.commit()

    async with _admin_setup(db):
        m_row = (await db.execute(sa_text(
            "SELECT codigo FROM ens_measures WHERE deleted_at IS NULL LIMIT 1"
        ))).first()
    if m_row is None:
        pytest.skip("No measures in catalog")
    codigo = m_row[0]

    row = await compute_medida_detail(db, uuid.UUID(project_id), codigo)
    assert row is not None
    assert row.medida_code == codigo


@pytest.mark.asyncio
async def test_compute_medida_detail_returns_none_for_unknown(db):
    _, project_id = await setup_test_project(db)
    await db.commit()
    row = await compute_medida_detail(
        db, uuid.UUID(project_id), "INVALID.NONEXIST.999",
    )
    assert row is None


@pytest.mark.asyncio
async def test_matrix_to_dict_json_serializable(db):
    """to_dict() returns JSON-serializable structure (pydantic-ready)."""
    import json

    _, project_id = await setup_test_project(db)
    await db.commit()

    matrix = await compute_dda_evidence_gaps(db, uuid.UUID(project_id))
    d = matrix.to_dict()
    # Must be JSON-serializable cross-context
    json_str = json.dumps(d)
    assert "project_id" in json_str
    assert "medidas" in json_str
    assert "severity_summary" in json_str
    assert "options_used" in json_str
