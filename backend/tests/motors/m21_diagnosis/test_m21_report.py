"""Tests del informe de diagnostico Fase 1 + quick wins + DOCX (M21-B)."""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m16_onboarding import pkg_service as pkg
from backend.app.motors.m16_onboarding.client_service import (
    _generate_session_secret,
    _hash_secret,
)
from backend.tests.conftest import setup_test_project

BASE_ONB = "/api/v1/onboarding"
BASE_DIAG = "/api/v1/diagnosis"


async def _issue_onboarding_session_auth(db, session_id: str) -> dict:
    """Seed client_auth_secret_hash on session + return headers.

    Post-MB-4.bis3 (ADR-020 v3): magic_link consume drop · cliente accede portal
    via ClientUser (test_portal_api.py covers wrappers). Para tests m21 que
    aun usan headers X-Onboarding-Session-* legacy, issue session_secret
    directamente via DB (bypass /onboarding/consume).
    """
    secret_plain = _generate_session_secret()
    secret_hash = _hash_secret(secret_plain)
    await db.execute(
        sa_text("""
            UPDATE onboarding_sessions
               SET client_auth_secret_hash = :h,
                   client_auth_issued_at = :now
             WHERE id = :sid
        """),
        {"h": secret_hash, "now": datetime.now(timezone.utc), "sid": session_id},
    )
    await db.flush()
    return {
        "X-Onboarding-Session-Id": session_id,
        "X-Onboarding-Session-Secret": secret_plain,
    }


async def _seed_full_and_run(async_client, db):
    """Seed project + onboarding + PKG + run diagnosis. Returns (project_id_str, run_id_str)."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    r = await async_client.post(
        f"{BASE_ONB}/projects/{project_id}/sessions",
        json={"sector": "servicios_profesionales", "role": "ti_cto", "interlocutor_email": "cto@t.com"},
    )
    assert r.status_code == 200, r.text
    session_id = r.json()["session_id"]

    headers = await _issue_onboarding_session_auth(db, session_id)

    for qid, val in [
        ("q-mfa_universal", "no_ninguno"),
        ("q-siem_activo", False),
        ("q-backup_estrategia", "informal"),
        ("q-endpoints_managed", "no"),
        ("q-email_identidad", "microsoft_365"),
    ]:
        await async_client.post(
            f"{BASE_ONB}/me/responses", headers=headers,
            json={"question_id": qid, "answer_value": val},
        )
    await async_client.post(
        f"{BASE_ONB}/me/submit", headers=headers, json={"allow_partial": True}
    )

    # PKG: NO sponsor, NO CTO => critical_gaps > 0
    erp = await pkg.add_node(db, pid, "system", "ERP Contable")
    proc1 = await pkg.add_node(db, pid, "process", "Facturacion")
    await pkg.add_node(db, pid, "asset", "AWS", properties={"asset_subtype": "cloud_provider"})
    await pkg.add_node(db, pid, "identity", "User 1", properties={"identity_type": "user", "mfa_enabled": False})
    await pkg.add_node(db, pid, "identity", "User 2", properties={"identity_type": "user", "mfa_enabled": False})
    await pkg.add_edge(db, pid, proc1, erp, "uses")
    await db.flush()

    run_r = await async_client.post(
        f"{BASE_DIAG}/projects/{project_id}/run",
        json={"sector": "servicios_profesionales"},
    )
    assert run_r.status_code == 200, run_r.text
    body = run_r.json()
    assert body["status"] == "completed"
    return project_id, body["id"]


class TestGenerateReport:
    @pytest.mark.asyncio
    async def test_generate_report_happy_path(self, async_client, db):
        project_id, run_id = await _seed_full_and_run(async_client, db)
        r = await async_client.post(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/generate-report"
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "generated"
        assert "report_data" in body
        rd = body["report_data"]
        assert "resumen_ejecutivo" in rd
        assert "quick_wins" in rd
        assert "recomendaciones_fase_2" in rd
        assert "stakeholders" in rd
        assert "maturity" in rd

    @pytest.mark.asyncio
    async def test_generate_report_requires_existing_run(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE_DIAG}/projects/{project_id}/runs/{uuid.uuid4()}/generate-report"
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_report_includes_critical_recommendation(self, async_client, db):
        project_id, run_id = await _seed_full_and_run(async_client, db)
        r = await async_client.post(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/generate-report"
        )
        assert r.status_code == 200
        recs = r.json()["report_data"]["recomendaciones_fase_2"]
        assert len(recs) >= 1
        assert any(rec["prioridad"] == "critica" for rec in recs), recs


class TestQuickWins:
    @pytest.mark.asyncio
    async def test_quick_wins_detect_mfa(self, async_client, db):
        project_id, run_id = await _seed_full_and_run(async_client, db)
        await async_client.post(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/generate-report"
        )
        r = await async_client.get(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/quick-wins"
        )
        assert r.status_code == 200
        ids = [qw["id"] for qw in r.json()["quick_wins"]]
        assert "qw-mfa-universal" in ids, ids

    @pytest.mark.asyncio
    async def test_quick_wins_detect_roles_gap(self, async_client, db):
        project_id, run_id = await _seed_full_and_run(async_client, db)
        await async_client.post(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/generate-report"
        )
        r = await async_client.get(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/quick-wins"
        )
        ids = [qw["id"] for qw in r.json()["quick_wins"]]
        assert "qw-roles-ens" in ids, ids

    @pytest.mark.asyncio
    async def test_quick_wins_sorted_by_priority(self, async_client, db):
        project_id, run_id = await _seed_full_and_run(async_client, db)
        await async_client.post(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/generate-report"
        )
        r = await async_client.get(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/quick-wins"
        )
        wins = r.json()["quick_wins"]
        assert len(wins) >= 2
        priority = {"critico": 0, "alto": 1, "medio": 2, "bajo": 3}
        for i in range(len(wins) - 1):
            assert priority.get(wins[i]["impacto"], 9) <= priority.get(
                wins[i + 1]["impacto"], 9
            ), wins


class TestDOCXGeneration:
    @pytest.mark.asyncio
    async def test_generate_docx(self, async_client, db):
        project_id, run_id = await _seed_full_and_run(async_client, db)
        await async_client.post(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/generate-report"
        )
        r = await async_client.post(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/generate-docx"
        )
        if r.status_code == 501:
            pytest.skip("docxtpl no disponible")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "generated"
        assert body["docx_path"].endswith(".docx")

    @pytest.mark.asyncio
    async def test_download_docx_after_generation(self, async_client, db):
        project_id, run_id = await _seed_full_and_run(async_client, db)
        await async_client.post(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/generate-report"
        )
        gen = await async_client.post(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/generate-docx"
        )
        if gen.status_code == 501:
            pytest.skip("docxtpl no disponible")
        r = await async_client.get(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/download-docx"
        )
        assert r.status_code == 200, r.text
        assert "openxmlformats" in r.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_download_docx_404_when_not_generated(self, async_client, db):
        project_id, run_id = await _seed_full_and_run(async_client, db)
        r = await async_client.get(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/download-docx"
        )
        assert r.status_code == 404


class TestReportErrors:
    @pytest.mark.asyncio
    async def test_quick_wins_404_when_report_not_generated(self, async_client, db):
        project_id, run_id = await _seed_full_and_run(async_client, db)
        r = await async_client.get(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/quick-wins"
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_docx_requires_report_first(self, async_client, db):
        project_id, run_id = await _seed_full_and_run(async_client, db)
        r = await async_client.post(
            f"{BASE_DIAG}/projects/{project_id}/runs/{run_id}/generate-docx"
        )
        assert r.status_code == 422
