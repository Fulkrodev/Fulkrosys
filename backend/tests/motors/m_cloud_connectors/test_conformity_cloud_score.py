"""Tests M27 Conformity cloud verification score · sub-fase 1.D.J.B.M27.

Verifica integrations layer additive:
- get_conformity_cloud_score() helper deterministic R1 count-based
- Compatibility scenarios: zero connectors · partial coverage · full coverage
- R1 INVIOLABLE: score formula pure count-based · NUNCA LLM
- Per familia aggregates: op.acc · op.exp · mp.s · mp.info · op.cont · org

Pattern K-light ADDITIVE sostener: NO motor M27 source-code modification ·
ADR-025 + ADR-039 + OPS-045 32ª aplicación consecutiva sostenida.
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import text

from backend.app.motors.m_cloud_connectors import (
    CloudConnectorProvider,
    CloudConnectorService,
    DiagnosticGapEngine,
)
from backend.app.motors.m_cloud_connectors.integrations import (
    get_conformity_cloud_score,
)
from backend.tests.conftest import setup_test_project


async def _seed_identity_users(
    db,
    *,
    project_id: uuid.UUID,
    connector_id: uuid.UUID,
    count: int,
    mfa_enabled: bool,
) -> None:
    for i in range(count):
        await db.execute(
            text(
                "INSERT INTO cloud_resources "
                "(id, project_id, connector_id, resource_type, "
                "resource_external_id, resource_name, attributes) "
                "VALUES (:id, :pid, :cid, 'identity.user', "
                ":ext, :name, CAST(:attrs AS JSONB))"
            ),
            {
                "id": str(uuid.uuid4()),
                "pid": str(project_id),
                "cid": str(connector_id),
                "ext": f"user_{i}",
                "name": f"User {i}",
                "attrs": f'{{"mfa_enabled": {str(mfa_enabled).lower()}}}',
            },
        )
    await db.flush()


# ============================================================
# Scenario 1 · Zero connectors · graceful empty state R29
# ============================================================


@pytest.mark.asyncio
async def test_conformity_score_zero_connectors_returns_zero_no_crash(db):
    """Project sin CloudConnector · score=0% sin crash · R29 graceful."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    score = await get_conformity_cloud_score(db, project_id=pid)

    assert score.project_id == pid
    assert score.measures_cloud_verified == 0
    # 8 measures base RULE_CATALOG (project sin categoria_objetivo · full)
    assert score.measures_total_aplicable == 8
    assert score.score_percentage == 0.0
    # Familia breakdown · 6 distinct: op.acc · op.exp · mp.s · mp.info · op.cont · org
    familias = {b.familia for b in score.per_familia_breakdown}
    assert familias == {"op.acc", "op.exp", "mp.s", "mp.info", "op.cont", "org"}
    # All familia verified=0
    assert all(b.verified == 0 for b in score.per_familia_breakdown)


# ============================================================
# Scenario 2 · Partial coverage · mixed implemented/missing
# ============================================================


@pytest.mark.asyncio
async def test_conformity_score_partial_coverage_mixed_status(db):
    """Project con connectors · MFA gap missing + otras implemented."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    svc = CloudConnectorService(db)
    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.MICROSOFT_365,
    )
    # Seed 3 users sin MFA → emite gap op.acc.6 (missing structural)
    await _seed_identity_users(
        db, project_id=pid, connector_id=connector.id, count=3, mfa_enabled=False,
    )

    # Run diagnosis · genera gap op.acc.6 + org.1 documental
    engine = DiagnosticGapEngine(db)
    await engine.run_diagnosis(project_id=pid, category="BASICA")

    score = await get_conformity_cloud_score(db, project_id=pid)

    # Project default sin categoria_objetivo · helper usa RULE_CATALOG full (8)
    assert score.project_category is None
    assert score.measures_total_aplicable == 8

    # Status verified count empírico:
    # op.acc.6 → missing (gap structural · NOT verified)
    # op.exp.1 → inventory documental gap (NOT verified)
    # org.1 → documental policy missing (NOT verified)
    # Resto 5 measures sin gap → implemented (verified)
    # Verified = 5/8 = 62.5%
    assert score.measures_cloud_verified == 5
    assert score.score_percentage == pytest.approx(62.5, abs=0.1)

    # Per familia: op.acc verified=1/2 (op.acc.5 verified · op.acc.6 missing)
    op_acc = next(b for b in score.per_familia_breakdown if b.familia == "op.acc")
    assert op_acc.total == 2  # op.acc.5 + op.acc.6
    assert op_acc.verified == 1
    # org familia: 1/1 (org.1 documental status NOT verified per logic)
    # Actually org.1 detect_documental_policy_missing emite gap "documental"
    # logic: documental → status="documental" → NOT verified
    org_fam = next(b for b in score.per_familia_breakdown if b.familia == "org")
    assert org_fam.total == 1


# ============================================================
# Scenario 3 · Full coverage · all measures verified
# ============================================================


@pytest.mark.asyncio
async def test_conformity_score_full_coverage_when_no_gaps_emitted(db):
    """Project con connector + sin gaps emitted · all 8 measures verified."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    svc = CloudConnectorService(db)
    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.MICROSOFT_365,
    )
    # Seed 3 users CON MFA → NO emite gap op.acc.6
    await _seed_identity_users(
        db, project_id=pid, connector_id=connector.id, count=3, mfa_enabled=True,
    )

    # NO run diagnosis · NO gaps · BUT measures sin gap = implemented
    # (get_measure_cloud_status logic · supported + no_gap → implemented)

    score = await get_conformity_cloud_score(db, project_id=pid)

    # All 8 measures verified (sin gaps · status="implemented" each)
    assert score.measures_cloud_verified == 8
    assert score.measures_total_aplicable == 8
    assert score.score_percentage == 100.0


# ============================================================
# Scenario 4 · R1 INVIOLABLE deterministic · NO LLM in pipeline
# ============================================================


@pytest.mark.asyncio
async def test_conformity_score_is_deterministic_no_llm_invoked(db):
    """R1 INVIOLABLE · pipeline score 0 LLM invocations · pure count-based."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    svc = CloudConnectorService(db)
    await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.MICROSOFT_365,
    )

    # Patch anthropic.Anthropic · si LLM se invocaría · test FAIL
    with patch("anthropic.Anthropic") as anthropic_mock:
        score = await get_conformity_cloud_score(db, project_id=pid)
        # Score returned · NO LLM client constructed
        assert anthropic_mock.call_count == 0
        assert score.measures_total_aplicable == 8


# ============================================================
# Scenario 5 · Categoria filter scopes applicable rules
# ============================================================


@pytest.mark.asyncio
async def test_conformity_score_basica_category_filters_to_5_measures(db):
    """Project BASICA · solo 5 measures aplicables (no op.acc.5/op.exp.8/op.cont.3)."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    # Set project.categoria_objetivo = 'BASICA' via raw SQL update
    await db.execute(
        text("UPDATE projects SET categoria_objetivo='BASICA' WHERE id=:pid"),
        {"pid": str(pid)},
    )
    await db.flush()

    score = await get_conformity_cloud_score(db, project_id=pid)

    # BASICA rules: op.acc.6 + op.exp.1 + mp.info.3 + mp.s.2 + org.1 = 5
    assert score.measures_total_aplicable == 5
    assert score.project_category == "BASICA"
