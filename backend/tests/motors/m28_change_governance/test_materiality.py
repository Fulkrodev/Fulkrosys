"""Tests for M28 materiality engine + topology + APIs."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m28_change_governance.materiality_engine import (
    IMPACT_QUESTIONS,
    assess,
)
from backend.app.motors.m28_change_governance.topology_service import (
    TOPOLOGY_LIBRARY,
    list_patterns,
    recommend_pattern,
    requires_memo,
)
from backend.tests.conftest import setup_test_project


def _all_no() -> dict:
    return {q: False for q in IMPACT_QUESTIONS}


class TestMaterialityEngine:
    def test_questions_count_is_10(self):
        assert len(IMPACT_QUESTIONS) == 10

    def test_minor_when_no_triggers(self):
        out = assess(_all_no())
        assert out["materiality_level"] == "MINOR"
        assert out["materiality_score"] == 0

    def test_relevant_when_only_evidence(self):
        ans = _all_no()
        ans["affects_evidence"] = True
        out = assess(ans)
        assert out["materiality_level"] == "RELEVANT"

    def test_material_when_category(self):
        ans = _all_no()
        ans["affects_category"] = True
        out = assess(ans)
        assert out["materiality_level"] == "MATERIAL"
        assert "recategorization" in out["required_workflows"]
        assert "E-048" in out["required_documents"]

    def test_material_when_extraordinary(self):
        ans = _all_no()
        ans["requires_extraordinary"] = True
        out = assess(ans)
        assert out["materiality_level"] == "MATERIAL"
        assert "extraordinary_audit" in out["required_workflows"]
        assert out["deadline_policy"] == "1d"

    def test_missing_answers_raises(self):
        with pytest.raises(ValueError):
            assess({"affects_evidence": True})

    def test_score_high_when_all_true(self):
        out = assess({q: True for q in IMPACT_QUESTIONS})
        assert out["materiality_score"] >= 90
        assert out["materiality_level"] == "MATERIAL"


class TestTopologyLibrary:
    def test_5_patterns(self):
        assert len(TOPOLOGY_LIBRARY) == 5
        assert {"PATTERN_A", "PATTERN_B", "PATTERN_C", "PATTERN_D", "PATTERN_E"} == set(TOPOLOGY_LIBRARY.keys())

    def test_list_returns_all(self):
        assert len(list_patterns()) == 5

    def test_recommend_alta_returns_pattern_e(self):
        assert recommend_pattern("generico", 200, True, True, False, "ALTA") == "PATTERN_E"

    def test_recommend_micro_pyme_returns_d(self):
        assert recommend_pattern("generico", 10, False, False, False, "BASICA") == "PATTERN_D"

    def test_pattern_d_requires_memo(self):
        assert requires_memo("PATTERN_D") is True
        assert requires_memo("PATTERN_A") is False


@pytest.mark.asyncio
class TestM28Api:
    async def test_intake_and_assess(self, async_client, db: AsyncSession):
        _, pid = await setup_test_project(db)
        r = await async_client.post(
            f"/api/v1/changes/projects/{pid}/changes",
            json={"description": "Migracion de servidor de email a Microsoft 365 cloud", "requested_by": "marcos"},
        )
        assert r.status_code == 201, r.text
        cid = r.json()["change_id"]

        r2 = await async_client.post(
            f"/api/v1/changes/projects/{pid}/changes/{cid}/assess",
            json={"answers": {q: False for q in IMPACT_QUESTIONS} | {
                "affects_evidence": True,
                "affects_documentation": True,
                "affects_controls": True,
            }},
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["materiality_level"] == "RELEVANT"

    async def test_assess_missing_answers_422(self, async_client, db: AsyncSession):
        _, pid = await setup_test_project(db)
        r = await async_client.post(
            f"/api/v1/changes/projects/{pid}/changes",
            json={"description": "abc def ghi jkl mno pqr stu vwx", "requested_by": "marcos"},
        )
        cid = r.json()["change_id"]
        bad = await async_client.post(
            f"/api/v1/changes/projects/{pid}/changes/{cid}/assess",
            json={"answers": {"affects_evidence": True}},
        )
        assert bad.status_code == 422

    async def test_topology_review(self, async_client, db: AsyncSession):
        _, pid = await setup_test_project(db)
        r = await async_client.post(
            f"/api/v1/changes/projects/{pid}/roles/topology/review",
            json={
                "sector": "saas_tech", "employees": 200,
                "has_internal_it": True, "has_internal_ciso": True,
                "multi_site": False, "category": "MEDIA",
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["recommended_pattern"] in TOPOLOGY_LIBRARY
