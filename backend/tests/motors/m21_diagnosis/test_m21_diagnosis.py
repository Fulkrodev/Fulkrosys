"""Tests del Motor 21 Organizational Diagnosis."""
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


async def _seed_full(async_client, db):
    """Seed via API (M16 onboarding flow) + direct PKG inserts."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    # Create session via API + issue session_secret directly (ADR-020 v3 · no magic_link)
    r = await async_client.post(
        f"{BASE_ONB}/projects/{project_id}/sessions",
        json={"sector": "servicios_profesionales", "role": "ti_cto", "interlocutor_email": "cto@t.com"},
    )
    assert r.status_code == 200, r.text
    sess = r.json()
    session_id = sess["session_id"]

    headers = await _issue_onboarding_session_auth(db, session_id)

    # Gate RGPD (Art. 13) · registrar el consentimiento ANTES de responder · sin
    # él /me/responses devuelve 403 consent_required (capa legal Batch A).
    cr = await async_client.post(
        f"{BASE_ONB}/me/consent", headers=headers, json={"consented": True},
    )
    assert cr.status_code == 200, cr.text

    for qid, val in [
        ("q-mfa_universal", "si_todos"), ("q-siem_activo", True),
        ("q-backup_estrategia", "cloud_automatico"), ("q-endpoints_managed", "si_mdm"),
        ("q-email_identidad", "microsoft_365"),
    ]:
        rr = await async_client.post(
            f"{BASE_ONB}/me/responses", headers=headers,
            json={"question_id": qid, "answer_value": val},
        )
        assert rr.status_code == 200, rr.text

    await async_client.post(f"{BASE_ONB}/me/submit", headers=headers, json={"allow_partial": True})

    # PKG nodes (no RLS)
    await pkg.add_node(db, pid, "person", "Ana Sponsor", properties={"role": "sponsor"})
    await pkg.add_node(db, pid, "person", "Pedro CTO", properties={"role": "cto"})
    erp = await pkg.add_node(db, pid, "system", "ERP Contable")
    proc1 = await pkg.add_node(db, pid, "process", "Facturacion")
    await pkg.add_node(db, pid, "asset", "AWS", properties={"asset_subtype": "cloud_provider"})
    await pkg.add_node(db, pid, "identity", "User 1", properties={"identity_type": "user", "mfa_enabled": True})
    await pkg.add_node(db, pid, "identity", "User 2", properties={"identity_type": "user", "mfa_enabled": False})
    persons = await pkg.get_nodes_by_type(db, pid, "person")
    await pkg.add_edge(db, pid, persons[0]["id"], erp, "owns")
    await pkg.add_edge(db, pid, proc1, erp, "uses")
    await db.flush()

    return pid, project_id


async def _seed_empty(async_client, db):
    _, project_id = await setup_test_project(db)
    return uuid.UUID(project_id), project_id


class TestRunDiagnosis:
    @pytest.mark.asyncio
    async def test_happy_path(self, async_client, db):
        _, project_id = await _seed_full(async_client, db)
        r = await async_client.post(f"{BASE_DIAG}/projects/{project_id}/run", json={"sector": "servicios_profesionales"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "completed"
        assert body["stakeholder_analysis"] is not None
        assert body["maturity_scoring"] is not None
        assert body["summary"] is not None

    @pytest.mark.asyncio
    async def test_empty_project(self, async_client, db):
        _, project_id = await _seed_empty(async_client, db)
        r = await async_client.post(f"{BASE_DIAG}/projects/{project_id}/run", json={"sector": "generico"})
        assert r.status_code == 200
        assert r.json()["stakeholder_analysis"]["total_people"] == 0

    @pytest.mark.asyncio
    async def test_with_notes(self, async_client, db):
        _, project_id = await _seed_full(async_client, db)
        r = await async_client.post(f"{BASE_DIAG}/projects/{project_id}/run",
            json={"sector": "servicios_profesionales", "confidential_notes": "CTO resistant"})
        assert r.status_code == 200
        assert "confidential_notes" in r.json()


class TestStakeholders:
    @pytest.mark.asyncio
    async def test_missing_roles(self, async_client, db):
        _, project_id = await _seed_full(async_client, db)
        await async_client.post(f"{BASE_DIAG}/projects/{project_id}/run", json={"sector": "servicios_profesionales"})
        r = await async_client.get(f"{BASE_DIAG}/projects/{project_id}/stakeholders")
        assert r.status_code == 200
        assert r.json()["critical_gaps"] > 0
        assert "rseg" in [m["role_key"] for m in r.json()["missing_required_roles"]]

    @pytest.mark.asyncio
    async def test_finds_sponsor(self, async_client, db):
        _, project_id = await _seed_full(async_client, db)
        await async_client.post(f"{BASE_DIAG}/projects/{project_id}/run", json={"sector": "servicios_profesionales"})
        r = await async_client.get(f"{BASE_DIAG}/projects/{project_id}/stakeholders")
        assert "sponsor" in r.json()["roles_found"]


class TestMaturity:
    @pytest.mark.asyncio
    async def test_7_domains(self, async_client, db):
        _, project_id = await _seed_full(async_client, db)
        await async_client.post(f"{BASE_DIAG}/projects/{project_id}/run", json={"sector": "servicios_profesionales"})
        r = await async_client.get(f"{BASE_DIAG}/projects/{project_id}/maturity")
        assert r.status_code == 200
        assert len(r.json()["domains"]) == 7

    @pytest.mark.asyncio
    async def test_mfa_boosts_op_acc(self, async_client, db):
        _, project_id = await _seed_full(async_client, db)
        await async_client.post(f"{BASE_DIAG}/projects/{project_id}/run", json={"sector": "servicios_profesionales"})
        r = await async_client.get(f"{BASE_DIAG}/projects/{project_id}/maturity")
        assert r.json()["domains"]["op_acc"]["points"] >= 3

    @pytest.mark.asyncio
    async def test_siem_boosts_op_mon(self, async_client, db):
        _, project_id = await _seed_full(async_client, db)
        await async_client.post(f"{BASE_DIAG}/projects/{project_id}/run", json={"sector": "servicios_profesionales"})
        r = await async_client.get(f"{BASE_DIAG}/projects/{project_id}/maturity")
        assert r.json()["domains"]["op_mon"]["points"] >= 3


class TestCompliance:
    @pytest.mark.asyncio
    async def test_ens_rgpd(self, async_client, db):
        _, project_id = await _seed_full(async_client, db)
        await async_client.post(f"{BASE_DIAG}/projects/{project_id}/run", json={"sector": "servicios_profesionales"})
        r = await async_client.get(f"{BASE_DIAG}/projects/{project_id}/compliance")
        codes = [n["code"] for n in r.json()["applicable"]]
        assert "ENS" in codes and "RGPD" in codes

    @pytest.mark.asyncio
    async def test_fintech_psd2_dora(self, async_client, db):
        _, project_id = await _seed_full(async_client, db)
        await async_client.post(f"{BASE_DIAG}/projects/{project_id}/run", json={"sector": "fintech"})
        r = await async_client.get(f"{BASE_DIAG}/projects/{project_id}/compliance")
        codes = [n["code"] for n in r.json()["applicable"]]
        assert "PSD2" in codes and "DORA" in codes


class TestDiagnosisAPI:
    @pytest.mark.asyncio
    async def test_latest_404(self, async_client, db):
        _, project_id = await _seed_empty(async_client, db)
        r = await async_client.get(f"{BASE_DIAG}/projects/{project_id}/latest")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_list_runs(self, async_client, db):
        _, project_id = await _seed_full(async_client, db)
        await async_client.post(f"{BASE_DIAG}/projects/{project_id}/run", json={"sector": "servicios_profesionales"})
        await async_client.post(f"{BASE_DIAG}/projects/{project_id}/run", json={"sector": "servicios_profesionales"})
        r = await async_client.get(f"{BASE_DIAG}/projects/{project_id}/runs")
        assert len(r.json()) == 2

    @pytest.mark.asyncio
    async def test_nonexistent_404(self, async_client):
        r = await async_client.post(f"{BASE_DIAG}/projects/{uuid.uuid4()}/run", json={"sector": "generico"})
        assert r.status_code == 404
