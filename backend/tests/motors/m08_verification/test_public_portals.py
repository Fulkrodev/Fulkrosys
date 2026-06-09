"""Tests para los 3 portales publicos del Motor 8 v5.1 (Checkpoint 3B).

Cubren:
- Token validation (invalid, expired, revoked, purpose mismatch)
- Rate limiting (20 req/min)
- Remediation portal (GET data + fixed retest + guide)
- Pentester portal (GET + findings submit + complete)
- Verify-auth portal (GET + submit flow con OTP)
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.database import set_tenant_context
from backend.app.motors.m08_verification.models import (
    ExternalPentesterHandoff, VerificationFinding, VerificationRun,
)
from backend.app.motors.m08_verification import public_api as pub_mod
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService
from backend.tests.conftest import _admin_setup, setup_test_project


BASE = "/api/v1/public"


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════

async def _generate_magic_link(
    db, project_id, purpose: MagicLinkPurpose,
    *, recipient="cliente@example.com", max_usos=50,
):
    await set_tenant_context(db, client_id=None, project_id=project_id)
    # set tenant context via project
    client_id = (await db.execute(sa_text(
        "SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    svc = MagicLinkService(db)
    req = MagicLinkGenerateRequest(
        project_id=project_id,
        purpose=purpose,
        recipient_email=recipient,
        max_uses=max_usos,
    )
    resp = await svc.generate_magic_link(req, base_url="https://test.fulkro.es")
    await db.commit()
    return resp.token


async def _seed_run_and_findings(
    db, project_id, n_findings=2, with_handoff=False,
):
    async with _admin_setup(db):
        run = VerificationRun(
            project_id=project_id, category="BASICO",
            mode="external_handoff" if with_handoff else "internal",
            status="pending",
            scope_jsonb={
                "targets": ["app.dataforma.es"],
                "web_apps": ["https://app.dataforma.es"],
                "exclusions": [],
                "scan_window": "22:00-06:00",
            },
            tools_used=["nuclei", "testssl"],
            total_findings=n_findings,
            confirmed_findings=n_findings,
        )
        db.add(run)
        await db.flush()
        findings = []
        for i in range(n_findings):
            f = VerificationFinding(
                project_id=project_id, run_id=run.id,
                finding_hash=f"tpublic_{i}_{uuid.uuid4().hex[:8]}",
                title=f"Test finding {i}",
                description="Descripcion sintetica",
                severity="high" if i == 0 else "medium",
                affected_host="app.dataforma.es", affected_port=443,
                tool_sources=["nuclei"],
                raw_outputs=[{"tool": "nuclei", "excerpt": "x"}],
                confidence_score=0.95,
                zfp_gate1_dedup=True, zfp_gate2_fp_filter=True,
                zfp_gate3_cross_tool=1,
                zfp_gate4_retest="not_applicable",
                zfp_gate5_classification="confirmed",
                ens_measures=[{"measure": "op.exp.5", "title": "t"}],
                ens_primary_measure="op.exp.5",
                remediation_summary="apt upgrade",
                status="open",
            )
            db.add(f)
            findings.append(f)
        handoff = None
        if with_handoff:
            handoff = ExternalPentesterHandoff(
                project_id=project_id, run_id=run.id,
                package_documents=[
                    {"name": "01_Scope", "path": "var/verification_handoffs/fake/scope.md",
                     "hash_sha256": "a" * 64, "generated_at": "now"},
                ],
                status="portal_ready",
            )
            db.add(handoff)
        await db.flush()
        return run, findings, handoff


def _clear_rate_limit():
    pub_mod._RATE_STATE.clear()


# ════════════════════════════════════════════════════════════════════
# Token validation
# ════════════════════════════════════════════════════════════════════

class TestTokenValidation:
    @pytest.mark.asyncio
    async def test_invalid_token_returns_403(self, async_client, db):
        _clear_rate_limit()
        r = await async_client.get(f"{BASE}/remediation/not-a-real-token")
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_expired_token_returns_403(self, async_client, db):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.PORTAL_REMEDIACION,
        )
        # Expirar el link manualmente
        async with _admin_setup(db):
            await db.execute(sa_text(
                "UPDATE magic_links SET expira_at = now() - interval '1 day' "
                "WHERE project_id = :pid"
            ), {"pid": str(project_id)})
            await db.commit()
        r = await async_client.get(f"{BASE}/remediation/{token}")
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_revoked_token_returns_403(self, async_client, db):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.PORTAL_REMEDIACION,
        )
        async with _admin_setup(db):
            await db.execute(sa_text(
                "UPDATE magic_links SET revocado = true, revoked_at = now() "
                "WHERE project_id = :pid"
            ), {"pid": str(project_id)})
            await db.commit()
        r = await async_client.get(f"{BASE}/remediation/{token}")
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_purpose_mismatch_returns_403(self, async_client, db):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        # Token con purpose distinto al esperado
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.FIRMA_DOCUMENTO,
        )
        r = await async_client.get(f"{BASE}/remediation/{token}")
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_rate_limit_triggers_429(self, async_client, db):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.PORTAL_REMEDIACION,
        )
        # 20 requests OK, 21 → 429
        for _ in range(20):
            r = await async_client.get(f"{BASE}/remediation/{token}")
            assert r.status_code in (200, 404)
        r = await async_client.get(f"{BASE}/remediation/{token}")
        assert r.status_code == 429


# ════════════════════════════════════════════════════════════════════
# Remediation portal
# ════════════════════════════════════════════════════════════════════

class TestRemediationPortal:
    @pytest.mark.asyncio
    async def test_data_endpoint_returns_findings(self, async_client, db):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        run, findings, _ = await _seed_run_and_findings(db, project_id, 2)
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.PORTAL_REMEDIACION,
        )
        r = await async_client.get(f"{BASE}/remediation/{token}")
        assert r.status_code == 200
        data = r.json()
        assert data["progress"]["total"] == 2
        assert data["progress"]["pending"] == 2
        assert data["progress"]["resolved"] == 0
        assert len(data["pending_findings"]) == 2
        first = data["pending_findings"][0]
        # Non-technical fields present
        assert "summary_non_technical" in first
        assert "risk_real" in first
        assert "time_estimate" in first

    @pytest.mark.asyncio
    async def test_guide_endpoint_returns_steps(self, async_client, db):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        run, findings, _ = await _seed_run_and_findings(db, project_id, 1)
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.PORTAL_REMEDIACION,
        )
        fid = findings[0].id
        r = await async_client.get(
            f"{BASE}/remediation/{token}/findings/{fid}/guide",
        )
        assert r.status_code == 200
        data = r.json()
        assert data["finding_id"] == str(fid)
        assert data["guide"]["pasos"]
        assert all(
            "comando" in p and "verificacion" in p
            for p in data["guide"]["pasos"]
        )

    @pytest.mark.asyncio
    async def test_fixed_endpoint_triggers_retest(self, async_client, db):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        run, findings, _ = await _seed_run_and_findings(db, project_id, 1)
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.PORTAL_REMEDIACION,
        )
        fid = findings[0].id
        # Evitamos ejecutar retest real mockeando el dispatcher
        import backend.app.motors.m08_verification.remediation.retest_runner as rr

        async def _fake(_self, _finding):
            return "fixed", "nuclei --test", "0 findings detected"

        original = rr._DISPATCHERS.copy()
        rr._DISPATCHERS.clear()
        rr._DISPATCHERS.update(
            {k: (lambda f, _ok=_fake: _ok(None, f)) for k in original},
        )
        try:
            r = await async_client.post(
                f"{BASE}/remediation/{token}/findings/{fid}/fixed",
            )
            assert r.status_code == 200
            data = r.json()
            assert data["retest_result"] == "fixed"
            assert data["finding_status_after"] == "remediated"
        finally:
            rr._DISPATCHERS.clear()
            rr._DISPATCHERS.update(original)


# ════════════════════════════════════════════════════════════════════
# Pentester portal
# ════════════════════════════════════════════════════════════════════

class TestPentesterPortal:
    @pytest.mark.asyncio
    async def test_data_endpoint_returns_engagement(self, async_client, db):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        run, _, handoff = await _seed_run_and_findings(
            db, project_id, 0, with_handoff=True,
        )
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO,
        )
        r = await async_client.get(f"{BASE}/pentester-portal/{token}")
        assert r.status_code == 200
        data = r.json()
        assert data["engagement"]["run_id"] == str(run.id)
        assert data["engagement"]["handoff_id"] == str(handoff.id)
        assert data["documents"][0]["name"] == "01_Scope"
        assert "consultor_contact" in data

    @pytest.mark.asyncio
    async def test_findings_submit_creates_findings(self, async_client, db):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        run, _, handoff = await _seed_run_and_findings(
            db, project_id, 0, with_handoff=True,
        )
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO,
        )
        payload = {
            "findings": [
                {
                    "title": "SMB signing not required",
                    "description": "Permite ataques MITM con relay NTLM.",
                    "severity": "high",
                    "affected_host": "srv.dataforma.es",
                    "affected_port": 445,
                    "cvss_score": 7.5,
                    "remediation_summary": "Set RequireSecuritySignature=1",
                },
            ],
        }
        r = await async_client.post(
            f"{BASE}/pentester-portal/{token}/findings", json=payload,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["submitted"] == 1

    @pytest.mark.asyncio
    async def test_complete_marks_engagement(self, async_client, db):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        run, _, handoff = await _seed_run_and_findings(
            db, project_id, 0, with_handoff=True,
        )
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO,
        )
        r = await async_client.post(
            f"{BASE}/pentester-portal/{token}/complete",
        )
        assert r.status_code == 200
        assert r.json()["status"] == "report_received"

    @pytest.mark.asyncio
    async def test_document_download_404_when_index_out_of_range(
        self, async_client, db,
    ):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        run, _, handoff = await _seed_run_and_findings(
            db, project_id, 0, with_handoff=True,
        )
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO,
        )
        r = await async_client.get(
            f"{BASE}/pentester-portal/{token}/documents/999",
        )
        assert r.status_code == 404


# ════════════════════════════════════════════════════════════════════
# Verify-auth portal
# ════════════════════════════════════════════════════════════════════

class TestVerifyAuthPortal:
    @pytest.mark.asyncio
    async def test_data_endpoint_returns_scope(self, async_client, db):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        run, _, _ = await _seed_run_and_findings(db, project_id, 0)
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.AUTORIZAR_VERIFICACION_TECNICA,
        )
        r = await async_client.get(f"{BASE}/verify-auth/{token}")
        assert r.status_code == 200
        data = r.json()
        assert data["run"]["run_id"] == str(run.id)
        assert data["run"]["scope"]["targets"] == ["app.dataforma.es"]
        assert "legal_statement" in data
        assert "requires_otp" in data

    @pytest.mark.asyncio
    async def test_submit_requires_accepted_legal(self, async_client, db):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        await _seed_run_and_findings(db, project_id, 0)
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.AUTORIZAR_VERIFICACION_TECNICA,
        )
        r = await async_client.post(
            f"{BASE}/verify-auth/{token}/submit",
            json={"accepted_legal": False, "otp": "000000"},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_success_signs_run(self, async_client, db):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        run, _, _ = await _seed_run_and_findings(db, project_id, 0)
        # Use AUTORIZAR_PENTEST_EXTERNO que no requiere OTP (depende del config)
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.AUTORIZAR_VERIFICACION_TECNICA,
        )
        # Verificar si requiere OTP
        data_r = await async_client.get(f"{BASE}/verify-auth/{token}")
        payload: dict = {"accepted_legal": True}
        if data_r.json().get("requires_otp"):
            # Recuperar el OTP hash del link para generar OTP valido
            # (el hash no es reversible; el test usa el flow completo solo
            # para links sin OTP requerido).
            pytest.skip("Este test corre con links sin OTP")
        r = await async_client.post(
            f"{BASE}/verify-auth/{token}/submit", json=payload,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "signed"
        assert data["run_id"] == str(run.id)
        assert data["signature_hash"]

    @pytest.mark.asyncio
    async def test_request_otp_returns_metadata(self, async_client, db):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        await _seed_run_and_findings(db, project_id, 0)
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.AUTORIZAR_VERIFICACION_TECNICA,
        )
        # Determinar si este purpose requiere OTP
        data_r = await async_client.get(f"{BASE}/verify-auth/{token}")
        if not data_r.json().get("requires_otp"):
            # Backend responde 422 si no requiere OTP
            r = await async_client.post(
                f"{BASE}/verify-auth/{token}/request-otp",
                json={"delivery_method": "email"},
            )
            assert r.status_code == 422
        else:
            r = await async_client.post(
                f"{BASE}/verify-auth/{token}/request-otp",
                json={"delivery_method": "email"},
            )
            assert r.status_code == 200
            assert r.json()["delivery_method"] == "email"


# ════════════════════════════════════════════════════════════════════
# Purpose isolation across portals
# ════════════════════════════════════════════════════════════════════

class TestPurposeIsolation:
    @pytest.mark.asyncio
    async def test_remediation_token_rejected_by_pentester(
        self, async_client, db,
    ):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.PORTAL_REMEDIACION,
        )
        r = await async_client.get(f"{BASE}/pentester-portal/{token}")
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_pentester_token_rejected_by_verify_auth(
        self, async_client, db,
    ):
        _clear_rate_limit()
        _, project_id = await setup_test_project(db)
        token = await _generate_magic_link(
            db, project_id, MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO,
        )
        r = await async_client.get(f"{BASE}/verify-auth/{token}")
        assert r.status_code == 403
