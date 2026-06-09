"""Tests del endpoint GET .../verification/by-measure/{measure_code} (K.5)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m08_verification.models import (
    VerificationFinding, VerificationRun,
)
from backend.tests.conftest import _admin_setup, setup_test_project


BASE = "/api/v1"


async def _seed(db, project_id, measure="op.exp.5"):
    async with _admin_setup(db):
        run = VerificationRun(
            project_id=uuid.UUID(project_id),
            category="BASICO", mode="internal", status="completed",
            scope_jsonb={"targets": ["x"], "web_apps": [], "exclusions": []},
            tools_used=["nuclei"],
            completed_at=datetime.now(timezone.utc),
            total_findings=2, confirmed_findings=2,
        )
        db.add(run)
        await db.flush()
        a = VerificationFinding(
            project_id=uuid.UUID(project_id), run_id=run.id,
            finding_hash=f"bm_{uuid.uuid4().hex[:8]}",
            title="Critico primary", description="d", severity="critical",
            affected_host="h1", tool_sources=["nuclei"],
            raw_outputs=[{"tool": "nuclei", "excerpt": "x"}],
            confidence_score=0.95,
            zfp_gate1_dedup=True, zfp_gate2_fp_filter=True,
            zfp_gate3_cross_tool=1, zfp_gate4_retest="not_applicable",
            zfp_gate5_classification="confirmed",
            ens_measures=[{"measure": measure, "title": "t"}],
            ens_primary_measure=measure,
            remediation_summary="fix", status="open",
        )
        b = VerificationFinding(
            project_id=uuid.UUID(project_id), run_id=run.id,
            finding_hash=f"bm_{uuid.uuid4().hex[:8]}",
            title="Alto en ens_measures secundaria", description="d",
            severity="high",
            affected_host="h2", tool_sources=["testssl"],
            raw_outputs=[{"tool": "testssl", "excerpt": "x"}],
            confidence_score=0.90,
            zfp_gate1_dedup=True, zfp_gate2_fp_filter=True,
            zfp_gate3_cross_tool=1, zfp_gate4_retest="not_applicable",
            zfp_gate5_classification="confirmed",
            ens_measures=[
                {"measure": "mp.com.2", "title": "otra"},
                {"measure": measure, "title": "t"},
            ],
            ens_primary_measure="mp.com.2",
            remediation_summary="fix", status="remediated",
        )
        db.add_all([a, b])
        await db.flush()
    return run, a, b


class TestByMeasureEndpoint:
    @pytest.mark.asyncio
    async def test_returns_findings_matching_primary_measure(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _seed(db, project_id, measure="op.exp.5")
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/verification/by-measure/op.exp.5",
        )
        assert r.status_code == 200
        data = r.json()
        assert data["measure_code"] == "op.exp.5"
        assert data["counts"]["total"] == 2
        assert data["counts"]["open"] == 1
        assert data["counts"]["remediated"] == 1
        titles = [f["title"] for f in data["findings"]]
        assert "Critico primary" in titles
        assert "Alto en ens_measures secundaria" in titles

    @pytest.mark.asyncio
    async def test_empty_measure_returns_zero(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _seed(db, project_id, measure="op.exp.5")
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/verification/by-measure/op.exp.99",
        )
        assert r.status_code == 200
        data = r.json()
        assert data["counts"]["total"] == 0
        assert data["findings"] == []
        assert data["reports"] == []

    @pytest.mark.asyncio
    async def test_critical_high_count_reported(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _seed(db, project_id, measure="op.exp.5")
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/verification/by-measure/op.exp.5",
        )
        assert r.status_code == 200
        data = r.json()
        # Solo el critical sigue 'open' (el high esta 'remediated')
        assert data["counts"]["critical_or_high_open"] == 1

    @pytest.mark.asyncio
    async def test_last_verified_is_set(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _seed(db, project_id, measure="op.exp.5")
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/verification/by-measure/op.exp.5",
        )
        data = r.json()
        assert data["last_verified"] is not None

    @pytest.mark.asyncio
    async def test_deleted_findings_excluded(self, async_client, db):
        _, project_id = await setup_test_project(db)
        _, a, _ = await _seed(db, project_id, measure="op.exp.5")
        async with _admin_setup(db):
            await db.execute(sa_text(
                "UPDATE verification_findings SET deleted_at = now() "
                "WHERE id = :fid"
            ), {"fid": str(a.id)})
            await db.commit()
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/verification/by-measure/op.exp.5",
        )
        data = r.json()
        # 'a' estaba borrado; solo 'b' queda (severidad high y medida
        # secundaria op.exp.5).
        assert data["counts"]["total"] == 1
        assert data["findings"][0]["title"] == "Alto en ens_measures secundaria"

    @pytest.mark.asyncio
    async def test_findings_ordered_by_severity(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _seed(db, project_id, measure="op.exp.5")
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/verification/by-measure/op.exp.5",
        )
        data = r.json()
        sev = [f["severity"] for f in data["findings"]]
        # Critico debe ir primero antes que high
        assert sev.index("critical") < sev.index("high")

    @pytest.mark.asyncio
    async def test_invalid_project_returns_404(self, async_client, db):
        fake_id = "00000000-0000-0000-0000-000000000000"
        r = await async_client.get(
            f"{BASE}/projects/{fake_id}/verification/by-measure/op.exp.5",
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_medida_secundaria_via_ens_measures_jsonb(
        self, async_client, db,
    ):
        """Un finding con medida en ens_measures (no primaria) tambien aparece."""
        _, project_id = await setup_test_project(db)
        await _seed(db, project_id, measure="op.exp.5")
        # 'b' tiene ens_primary=mp.com.2 pero ens_measures incluye op.exp.5
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/verification/by-measure/mp.com.2",
        )
        data = r.json()
        # Solo 'b' matchea mp.com.2 como primary
        assert data["counts"]["total"] == 1
        assert data["findings"][0]["ens_primary_measure"] == "mp.com.2"
