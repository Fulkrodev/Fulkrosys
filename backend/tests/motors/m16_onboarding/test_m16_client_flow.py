"""Tests del flujo cliente M16-B: consume, responses, branching, submit.

Post-MB-4.bis3 (ADR-020 v3 IMPLEMENTED FULLY): cliente accede onboarding
vía /client-portal/onboarding (MB-4.3) con sesión ClientUser. NO magic_link
consume. Tests legacy del flow M16-B magic_link están skipped a nivel módulo.

Reemplazo: backend/tests/motors/m16_onboarding/test_portal_api.py creado
en MB-4.2.bis cubre wrappers /portal/onboarding/projects/{id}/* + ClientUser auth.
"""
import uuid
from urllib.parse import parse_qs, urlparse

import pytest

from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m16_onboarding.enums import Role, Sector
from backend.app.motors.m16_onboarding.service import create_session
from backend.tests.conftest import setup_test_project


BASE = "/api/v1/onboarding"


# ================================================================
# HELPERS
# ================================================================

async def _seed_project(db):
    _, project_id = await setup_test_project(db)
    return project_id


async def _create_session_con_enlace(db, project_id, role="sponsor"):
    """Sesion con enlace magico para entrar por ``/consume`` sin cuenta.

    Desde ADR-020 v3 ``POST /projects/{id}/sessions`` ya NO emite enlace: el
    cliente responde dentro de su portal. El enlace sin cuenta solo se emite
    con el proposito DIAGNOSTICO_PRECLIENTE, y ``/consume`` + ``/me/*`` siguen
    siendo el camino de ese lead. Se crea por el servicio (como
    test_m16_precliente_magic_link) para conservar la plantilla de
    servicios_profesionales que estos tests recorren; lo que se prueba,
    consume y /me/*, va por HTTP.
    """
    result = await create_session(
        db, project_id=uuid.UUID(str(project_id)),
        sector=Sector.SERVICIOS_PROFESIONALES, role=Role(role),
        interlocutor_email=f"{role}@test.example", interlocutor_name=None,
        ttl_hours=168, language="es", metadata_extra=None,
        purpose=MagicLinkPurpose.DIAGNOSTICO_PRECLIENTE,
    )
    await db.flush()
    return {**result, "session_id": str(result["session_id"])}


def _extract_token(magic_link_url: str) -> str:
    """Extract JWT token from M12 URL: http://host/ml/consume?token=JWT."""
    parsed = urlparse(magic_link_url)
    params = parse_qs(parsed.query)
    tokens = params.get("token", [])
    assert tokens, f"No token in URL: {magic_link_url}"
    return tokens[0]


async def _consume_and_get_auth(async_client, create_resp):
    """Consume magic link and return auth headers + consume body."""
    token = _extract_token(create_resp["magic_link_url"])
    r = await async_client.post(
        f"{BASE}/consume",
        json={"token": token, "otp": create_resp.get("otp")},
    )
    assert r.status_code == 200, f"Consume failed: {r.text}"
    body = r.json()
    headers = {
        "X-Onboarding-Session-Id": body["session_id"],
        "X-Onboarding-Session-Secret": body["session_secret"],
    }
    # El lead acepta la informacion del art. 13 RGPD ANTES de responder: sin
    # ese registro, /me/next-question y /me/responses devuelven 403.
    rc = await async_client.post(
        f"{BASE}/me/consent", json={"consented": True}, headers=headers,
    )
    assert rc.status_code == 200, f"Consent failed: {rc.text}"
    return headers, body


# ================================================================
# CONSUME TESTS
# ================================================================

class TestClientConsume:

    @pytest.mark.asyncio
    async def test_consume_returns_session_and_secret(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        token = _extract_token(create_resp["magic_link_url"])

        r = await async_client.post(
            f"{BASE}/consume",
            json={"token": token},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "session_secret" in body
        assert len(body["session_secret"]) > 20
        assert body["total_questions"] > 0
        assert body["state"] == "created"

    @pytest.mark.asyncio
    async def test_consume_wrong_token_401(self, async_client, db):
        r = await async_client.post(
            f"{BASE}/consume",
            json={"token": "fake.jwt.token.that.is.long.enough"},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_consume_already_consumed_fails(self, async_client, db):
        """El enlace de precliente admite max_uses=3 (re-clic desde el email).

        Los tres primeros consumos entran; el cuarto se rechaza.
        """
        from backend.app.motors.m12_magic_link.purposes import get_config

        max_uses = get_config(MagicLinkPurpose.DIAGNOSTICO_PRECLIENTE)["max_uses"]
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        token = _extract_token(create_resp["magic_link_url"])

        for _ in range(max_uses):
            r = await async_client.post(f"{BASE}/consume", json={"token": token})
            assert r.status_code == 200, r.text

        r_extra = await async_client.post(f"{BASE}/consume", json={"token": token})
        assert r_extra.status_code == 401


# ================================================================
# SAVE ANSWER TESTS
# ================================================================

class TestSaveAnswer:

    @pytest.mark.asyncio
    async def test_save_transitions_to_in_progress(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        # Mark sent first so transition is SENT -> IN_PROGRESS
        await async_client.post(f"{BASE}/sessions/{create_resp['session_id']}/mark-sent")
        headers, _ = await _consume_and_get_auth(async_client, create_resp)

        r = await async_client.post(
            f"{BASE}/me/responses", headers=headers,
            json={"question_id": "q-motivacion_ens", "answer_value": "licitacion_publica"},
        )
        assert r.status_code == 200
        assert r.json()["state"] == "in_progress"

    @pytest.mark.asyncio
    async def test_save_increments_progress(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        headers, initial = await _consume_and_get_auth(async_client, create_resp)

        r = await async_client.post(
            f"{BASE}/me/responses", headers=headers,
            json={"question_id": "q-motivacion_ens", "answer_value": "licitacion_publica"},
        )
        assert r.json()["progress_percentage"] > initial["progress_percentage"]

    @pytest.mark.asyncio
    async def test_save_duplicate_updates_not_increments(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        headers, _ = await _consume_and_get_auth(async_client, create_resp)

        r1 = await async_client.post(
            f"{BASE}/me/responses", headers=headers,
            json={"question_id": "q-motivacion_ens", "answer_value": "licitacion_publica"},
        )
        progress_1 = r1.json()["progress_percentage"]

        r2 = await async_client.post(
            f"{BASE}/me/responses", headers=headers,
            json={"question_id": "q-motivacion_ens", "answer_value": "decision_estrategica"},
        )
        assert r2.status_code == 200
        assert r2.json()["progress_percentage"] == progress_1  # no increment

    @pytest.mark.asyncio
    async def test_save_invalid_select_value(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        headers, _ = await _consume_and_get_auth(async_client, create_resp)

        r = await async_client.post(
            f"{BASE}/me/responses", headers=headers,
            json={"question_id": "q-motivacion_ens", "answer_value": "VALOR_INEXISTENTE"},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_save_unknown_question_id(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        headers, _ = await _consume_and_get_auth(async_client, create_resp)

        r = await async_client.post(
            f"{BASE}/me/responses", headers=headers,
            json={"question_id": "q-fake-999", "answer_value": "x"},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_boolean_validation_rejects_string(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        headers, _ = await _consume_and_get_auth(async_client, create_resp)

        r = await async_client.post(
            f"{BASE}/me/responses", headers=headers,
            json={"question_id": "q-presupuesto_aprobado", "answer_value": "yes"},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_text_min_length_validation(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        headers, _ = await _consume_and_get_auth(async_client, create_resp)

        r = await async_client.post(
            f"{BASE}/me/responses", headers=headers,
            json={"question_id": "q-sponsor_ejecutivo", "answer_value": "x"},
        )
        assert r.status_code == 422


# ================================================================
# NEXT QUESTION TESTS
# ================================================================

class TestNextQuestion:

    @pytest.mark.asyncio
    async def test_returns_first_question(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        headers, _ = await _consume_and_get_auth(async_client, create_resp)

        r = await async_client.get(f"{BASE}/me/next-question", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["done"] is False
        assert body["question"] is not None
        assert body["question"]["id"] == "q-motivacion_ens"

    @pytest.mark.asyncio
    async def test_advances_after_save(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        headers, _ = await _consume_and_get_auth(async_client, create_resp)

        await async_client.post(
            f"{BASE}/me/responses", headers=headers,
            json={"question_id": "q-motivacion_ens", "answer_value": "licitacion_publica"},
        )
        r = await async_client.get(f"{BASE}/me/next-question", headers=headers)
        assert r.json()["question"]["id"] != "q-motivacion_ens"


# ================================================================
# BRANCHING TESTS
# ================================================================

class TestBranching:

    @pytest.mark.asyncio
    async def test_skip_if_applies(self, async_client, db):
        """When siem_activo=False, pentest_ultimo is skipped (skip_if configured)."""
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid, role="ti_cto")
        headers, _ = await _consume_and_get_auth(async_client, create_resp)

        # Answer siem_activo = False
        await async_client.post(
            f"{BASE}/me/responses", headers=headers,
            json={"question_id": "q-siem_activo", "answer_value": False},
        )

        # Verify pentest_ultimo is not in the effective sequence
        from backend.app.motors.m16_onboarding.catalog_loader import get_template_by_id
        from backend.app.motors.m16_onboarding.client_service import (
            _effective_question_sequence, _load_answers_map,
        )
        sid = uuid.UUID(create_resp["session_id"])
        answers = await _load_answers_map(db, sid)
        template = get_template_by_id("onb-servicios_profesionales-ti_cto-v1")
        effective = _effective_question_sequence(template, answers)
        assert "q-pentest_ultimo" not in [q.id for q in effective]

    @pytest.mark.asyncio
    async def test_skip_if_does_not_apply_when_true(self, async_client, db):
        """When siem_activo=True, pentest_ultimo is NOT skipped."""
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid, role="ti_cto")
        headers, _ = await _consume_and_get_auth(async_client, create_resp)

        await async_client.post(
            f"{BASE}/me/responses", headers=headers,
            json={"question_id": "q-siem_activo", "answer_value": True},
        )

        from backend.app.motors.m16_onboarding.catalog_loader import get_template_by_id
        from backend.app.motors.m16_onboarding.client_service import (
            _effective_question_sequence, _load_answers_map,
        )
        sid = uuid.UUID(create_resp["session_id"])
        answers = await _load_answers_map(db, sid)
        template = get_template_by_id("onb-servicios_profesionales-ti_cto-v1")
        effective = _effective_question_sequence(template, answers)
        assert "q-pentest_ultimo" in [q.id for q in effective]


# ================================================================
# SUBMIT TESTS
# ================================================================

class TestSubmit:

    @pytest.mark.asyncio
    async def test_submit_without_required_fails(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        headers, _ = await _consume_and_get_auth(async_client, create_resp)

        r = await async_client.post(
            f"{BASE}/me/submit", headers=headers,
            json={"allow_partial": False},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_allow_partial_completes(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        headers, _ = await _consume_and_get_auth(async_client, create_resp)

        r = await async_client.post(
            f"{BASE}/me/submit", headers=headers,
            json={"allow_partial": True},
        )
        assert r.status_code == 200
        assert r.json()["state"] == "completed"

    @pytest.mark.asyncio
    async def test_submit_idempotent(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        headers, _ = await _consume_and_get_auth(async_client, create_resp)

        await async_client.post(f"{BASE}/me/submit", headers=headers, json={"allow_partial": True})
        r2 = await async_client.post(f"{BASE}/me/submit", headers=headers, json={"allow_partial": True})
        assert r2.status_code == 200
        assert r2.json()["state"] == "completed"


# ================================================================
# AUTH TESTS
# ================================================================

class TestAuth:

    @pytest.mark.asyncio
    async def test_missing_headers_422(self, async_client):
        r = await async_client.get(f"{BASE}/me/next-question")
        assert r.status_code == 422  # FastAPI missing header

    @pytest.mark.asyncio
    async def test_wrong_secret_401(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        headers, body = await _consume_and_get_auth(async_client, create_resp)

        r = await async_client.get(
            f"{BASE}/me/next-question",
            headers={
                "X-Onboarding-Session-Id": body["session_id"],
                "X-Onboarding-Session-Secret": "wrong_secret_12345678901234567890",
            },
        )
        assert r.status_code == 401


# ================================================================
# PROGRESS TESTS
# ================================================================

class TestProgress:

    @pytest.mark.asyncio
    async def test_progress_endpoint(self, async_client, db):
        pid = await _seed_project(db)
        create_resp = await _create_session_con_enlace(db, pid)
        headers, _ = await _consume_and_get_auth(async_client, create_resp)

        r = await async_client.get(f"{BASE}/me/progress", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert "progress_percentage" in body
        assert body["total_questions"] > 0
