"""M8 v5.1 — Tests del ZFP engine (5 gates).

Cada gate testeado en aislamiento + pipeline completo.
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.database import set_tenant_context
from backend.app.motors.m08_verification.fp_patterns.learner import (
    seed_catalog_to_db,
)
from backend.app.motors.m08_verification.zfp_engine import (
    ZfpFinding,
    compute_finding_hash,
    gate1_dedup,
    gate2_fp_filter,
    gate3_correlation,
    gate4_retest,
    gate5_classify,
    run_zfp_pipeline,
)
from backend.tests.conftest import setup_test_project


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════

def _candidate(
    *, tool="nuclei", title="Generic finding",
    host="10.0.1.5", port=443, severity="high",
    cve=None, metadata=None,
):
    return {
        "title": title,
        "description": f"Description of {title}",
        "severity": severity,
        "cve_id": cve,
        "cvss_score": None,
        "affected_host": host,
        "affected_port": port,
        "affected_service": "https",
        "affected_url": None,
        "raw_output_excerpt": "raw...",
        "tool": tool,
        "tool_metadata": metadata or {},
    }


# ════════════════════════════════════════════════════════════════════
# Gate 1 — Dedup
# ════════════════════════════════════════════════════════════════════

def test_gate1_dedup_merges_same_finding_from_two_tools():
    cands = [
        _candidate(tool="nuclei", title="Apache Log4j RCE",
                   cve="CVE-2021-44228", host="web.example.es", port=443),
        _candidate(tool="openvas", title="Apache Log4j RCE",
                   cve="CVE-2021-44228", host="web.example.es", port=443),
    ]
    deduped = gate1_dedup(cands)
    assert len(deduped) == 1
    assert set(deduped[0].tool_sources) == {"nuclei", "openvas"}
    assert deduped[0].zfp_gate1_dedup is True


def test_gate1_dedup_keeps_distinct_findings_separately():
    cands = [
        _candidate(tool="nuclei", title="Log4j RCE", cve="CVE-2021-44228",
                   host="a.example.es"),
        _candidate(tool="nuclei", title="Log4j RCE", cve="CVE-2021-44228",
                   host="b.example.es"),
    ]
    deduped = gate1_dedup(cands)
    # Distinto host → 2 findings distintos
    assert len(deduped) == 2


def test_gate1_dedup_promotes_max_severity():
    cands = [
        _candidate(tool="nuclei", title="X-Frame-Options Missing",
                   severity="info", host="web", port=443),
        _candidate(tool="zap", title="X-Frame-Options Missing",
                   severity="medium", host="web", port=443),
    ]
    deduped = gate1_dedup(cands)
    assert len(deduped) == 1
    assert deduped[0].severity == "medium"


def test_compute_finding_hash_stable_on_reorder():
    c1 = _candidate(host="HOST.EXAMPLE.ES", port=443, cve="CVE-2024-6387")
    c2 = _candidate(host="host.example.es", port=443, cve="CVE-2024-6387")
    assert compute_finding_hash(c1) == compute_finding_hash(c2)


# ════════════════════════════════════════════════════════════════════
# Gate 2 — FP filter
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_gate2_filters_known_fp_patterns(db):
    """Crea proyecto, carga catalogo, y verifica que un finding tipo
    'wordpress-detect' (info) se rechaza por FP."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    await seed_catalog_to_db(db)

    fp_cand = _candidate(
        tool="nuclei", title="wordpress-detect technology",
        severity="info",
    )
    deduped = gate1_dedup([fp_cand])
    kept, rejected = await gate2_fp_filter(db, deduped)
    assert len(kept) == 0
    assert len(rejected) == 1
    assert rejected[0].zfp_gate5_classification == "rejected"
    assert rejected[0].fp_pattern_id is not None


@pytest.mark.asyncio
async def test_gate2_keeps_findings_without_match(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    await seed_catalog_to_db(db)

    real_cand = _candidate(
        tool="nuclei", title="Apache Log4j Remote Code Execution",
        severity="critical", cve="CVE-2021-44228",
    )
    deduped = gate1_dedup([real_cand])
    kept, rejected = await gate2_fp_filter(db, deduped)
    assert len(kept) == 1
    assert len(rejected) == 0


# ════════════════════════════════════════════════════════════════════
# Gate 3 — Correlation
# ════════════════════════════════════════════════════════════════════

def test_gate3_three_tools_gives_max_confidence():
    cands = [
        _candidate(tool=t, title="Critical RCE", cve="CVE-2021-44228",
                   host="web", port=443)
        for t in ("nuclei", "openvas", "zap")
    ]
    deduped = gate1_dedup(cands)
    gate3_correlation(deduped)
    f = deduped[0]
    assert f.zfp_gate3_cross_tool == 3
    # base 0.50 + 0.40 (>=3 sources) = 0.90
    assert f.confidence_score == pytest.approx(0.90, abs=0.01)


def test_gate3_two_tools_plus_cve_gives_080():
    cands = [
        _candidate(tool="nuclei", title="X", cve="CVE-2024-6387", host="h"),
        _candidate(tool="openvas", title="X", cve="CVE-2024-6387", host="h"),
    ]
    deduped = gate1_dedup(cands)
    gate3_correlation(deduped)
    f = deduped[0]
    assert f.zfp_gate3_cross_tool == 2
    # 0.50 + 0.30 (2 sources) = 0.80
    assert f.confidence_score == pytest.approx(0.80, abs=0.01)


def test_gate3_one_tool_no_cve_low_confidence():
    cands = [_candidate(tool="nuclei", title="Generic", cve=None)]
    deduped = gate1_dedup(cands)
    gate3_correlation(deduped)
    # 0.50 base sin bonus = 0.50
    assert deduped[0].confidence_score == pytest.approx(0.50, abs=0.01)


# ════════════════════════════════════════════════════════════════════
# Gate 4 — Re-test
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_gate4_skips_high_confidence_findings():
    cands = [
        _candidate(tool=t, title="X", cve="CVE-2021-44228")
        for t in ("nuclei", "openvas", "zap")
    ]
    deduped = gate1_dedup(cands)
    gate3_correlation(deduped)
    # confidence 0.90 → not_applicable (no retest)
    await gate4_retest(deduped, retest_callback=None)
    assert deduped[0].zfp_gate4_retest == "not_applicable"
    assert deduped[0].confidence_score == pytest.approx(0.90, abs=0.01)


@pytest.mark.asyncio
async def test_gate4_retest_confirms_low_confidence():
    cands = [_candidate(tool="nuclei", title="X")]
    deduped = gate1_dedup(cands)
    gate3_correlation(deduped)
    # confidence 0.50 (sin CVE, 1 tool)
    initial = deduped[0].confidence_score

    async def confirm(_f):
        return "confirmed"

    await gate4_retest(deduped, retest_callback=confirm)
    assert deduped[0].zfp_gate4_retest == "confirmed"
    # +0.25 al confirmar
    assert deduped[0].confidence_score == pytest.approx(initial + 0.25, abs=0.01)


@pytest.mark.asyncio
async def test_gate4_retest_not_confirmed_drops_confidence():
    cands = [_candidate(tool="nuclei", title="X")]
    deduped = gate1_dedup(cands)
    gate3_correlation(deduped)

    async def reject(_f):
        return "not_confirmed"

    await gate4_retest(deduped, retest_callback=reject)
    assert deduped[0].confidence_score == pytest.approx(0.20, abs=0.01)


# ════════════════════════════════════════════════════════════════════
# Gate 5 — Classification
# ════════════════════════════════════════════════════════════════════

def test_gate5_classification_thresholds():
    findings = [
        ZfpFinding(finding_hash="a", title="t", description="", severity="high",
                   affected_host="h", affected_port=None, affected_service=None,
                   affected_url=None, confidence_score=0.95),
        ZfpFinding(finding_hash="b", title="t", description="", severity="high",
                   affected_host="h", affected_port=None, affected_service=None,
                   affected_url=None, confidence_score=0.80),
        ZfpFinding(finding_hash="c", title="t", description="", severity="high",
                   affected_host="h", affected_port=None, affected_service=None,
                   affected_url=None, confidence_score=0.60),
        ZfpFinding(finding_hash="d", title="t", description="", severity="high",
                   affected_host="h", affected_port=None, affected_service=None,
                   affected_url=None, confidence_score=0.40),
    ]
    gate5_classify(findings)
    assert findings[0].zfp_gate5_classification == "confirmed"
    assert findings[1].zfp_gate5_classification == "probable"
    assert findings[2].zfp_gate5_classification == "needs_review"
    assert findings[3].zfp_gate5_classification == "rejected"


def test_gate5_does_not_overwrite_rejected_from_gate2():
    f = ZfpFinding(
        finding_hash="x", title="t", description="", severity="info",
        affected_host="h", affected_port=None, affected_service=None,
        affected_url=None, confidence_score=0.0,
        zfp_gate5_classification="rejected",
    )
    gate5_classify([f])
    assert f.zfp_gate5_classification == "rejected"


# ════════════════════════════════════════════════════════════════════
# Pipeline completo
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_pipeline_e2e_three_tools_critical(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    await seed_catalog_to_db(db)

    cands = [
        _candidate(tool=t, title="Apache Log4j RCE",
                   cve="CVE-2021-44228", host="web", port=443,
                   severity="critical")
        for t in ("nuclei", "openvas", "zap")
    ]
    kept, rejected = await run_zfp_pipeline(db, cands)
    assert len(kept) == 1
    assert len(rejected) == 0
    f = kept[0]
    assert f.zfp_gate5_classification == "confirmed"
    assert f.confidence_score >= 0.90
    assert f.zfp_gate3_cross_tool == 3


@pytest.mark.asyncio
async def test_pipeline_filters_fp_and_keeps_real(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    await seed_catalog_to_db(db)

    cands = [
        # FP conocido
        _candidate(tool="nuclei", title="wordpress-detect tech",
                   severity="info"),
        # Real
        _candidate(tool="nuclei", title="OpenSSH regreSSHion CVE",
                   cve="CVE-2024-6387", severity="high"),
    ]
    kept, rejected = await run_zfp_pipeline(db, cands)
    assert len(kept) == 1
    assert len(rejected) == 1
    assert kept[0].cve_id == "CVE-2024-6387"
