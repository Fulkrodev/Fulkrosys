"""Batch B diagnóstico previo · fix F-18 RLS account-less (commit 2).

PRUEBA DEL CIEGO PRE-FIX corriendo como el ROL DE PRODUCCIÓN (fulkro_app,
NOSUPERUSER) SIN contexto tenant — NO como superusuario (que daría el falso
verde que ya descubrimos: el fixture deja app.current_project_id seteado del
setup).

Contraste:
- Camino /consume y camino /me/*: SIN setear contexto, las lecturas RLS de
  magic_links / onboarding_sessions son CIEGAS (0 filas → raise). Es el
  comportamiento que tendría un lead real en prod sin el fix.
- CON el fix (endpoints resuelven project_id vía SECURITY DEFINER y setean
  contexto antes de la lectura), el flujo completo consume → consent → 17
  respuestas → submit pasa.

Requiere la migración precliente_rls_f18_001 aplicada (get_onboarding_session_owner
+ get_magic_link_project_by_token).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select, text

from backend.app.models.onboarding import OnboardingResponse, OnboardingSession
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m16_onboarding.client_service import (
    OnboardingAuthError,
    OnboardingClientError,
    OnboardingGoneError,
    authenticate_client_session,
    consume_magic_link_and_start,
)
from backend.app.motors.m16_onboarding.enums import Role, Sector
from backend.app.motors.m16_onboarding.service import create_session
from backend.tests.conftest import setup_test_project

BLIND_ERRORS = (OnboardingAuthError, OnboardingClientError, OnboardingGoneError)


async def _assert_prod_role_no_context(db):
    """Guard ANTI-falso-verde: confirma que corremos como rol NO-superusuario y
    SIN contexto tenant (réplica fiel de la request fresca del lead en prod)."""
    row = (await db.execute(text(
        "SELECT current_setting('is_superuser') AS su, "
        "       (current_project_id() IS NULL) AS noctx, "
        "       current_user AS usr"
    ))).first()
    assert row.su == "off", f"el test debe correr NO-superusuario · current_user={row.usr}"
    assert row.noctx is True, "el contexto tenant debe estar LIMPIO (prod fresh request)"


async def _clear_tenant_context(db):
    await db.execute(text(
        "SELECT set_config('app.current_project_id', '', true), "
        "       set_config('app.current_client_id', '', true)"
    ))


async def _new_precliente_session(db):
    """Crea proyecto + sesión precliente (purpose) · contexto seteado por el
    setup (como cuando Marcos la crea). Devuelve (session_id, token)."""
    _, project_id_str = await setup_test_project(db)
    result = await create_session(
        db, project_id=uuid.UUID(project_id_str),
        sector=Sector.PRECLIENTE, role=Role.SPONSOR,
        interlocutor_email="lead@example.com", interlocutor_name="Lead Frío",
        ttl_hours=14 * 24, language="es", metadata_extra=None,
        purpose=MagicLinkPurpose.DIAGNOSTICO_PRECLIENTE,
    )
    token = result["magic_link_url"].split("token=")[1]
    return result["session_id"], token


# ───────────────────────── CIEGO PRE-FIX (rol prod) ─────────────────────────

@pytest.mark.asyncio
async def test_consume_path_blind_without_context_as_fulkro_app(db):
    """Camino /consume SIN fix: con contexto limpio (fulkro_app) la lectura RLS
    de magic_links es ciega → consume falla. Esto es lo que le pasaría al lead
    real en prod sin el resolver SECURITY DEFINER."""
    _sid, token = await _new_precliente_session(db)

    await _clear_tenant_context(db)
    await _assert_prod_role_no_context(db)

    with pytest.raises(BLIND_ERRORS):
        await consume_magic_link_and_start(db, token, None)


@pytest.mark.asyncio
async def test_me_path_blind_without_context_as_fulkro_app(db):
    """Camino /me/* SIN fix: authenticate_client_session lee onboarding_sessions
    por id; con contexto limpio (fulkro_app) la lectura RLS es ciega → 'Session
    no existe'. El secret se emite ANTES (consume con contexto, como en setup)."""
    sid, token = await _new_precliente_session(db)
    consume = await consume_magic_link_and_start(db, token, None)  # ctx del setup
    secret = consume["session_secret"]

    await _clear_tenant_context(db)
    await _assert_prod_role_no_context(db)

    with pytest.raises(BLIND_ERRORS):
        await authenticate_client_session(db, sid, secret)


# ───────────────────────── CON FIX · flujo completo ─────────────────────────

def _answer_for(question: dict):
    t = question["type"]
    if t == "single_select":
        return question["options"][0]["value"]
    if t == "multi_select":
        return [question["options"][0]["value"]]
    if t == "number":
        return 10
    if t == "boolean":
        return True
    if t == "email":
        return "lead@example.com"
    if t == "url":
        return "https://example.com"
    if t == "date":
        return "2026-01-01"
    # text / long_text · respeta max_length de la validación.
    base = "Respuesta de prueba del lead"
    max_len = (question.get("validation") or {}).get("max_length")
    return base[:max_len] if max_len else base


@pytest.mark.asyncio
async def test_full_flow_passes_with_fix_as_fulkro_app(async_client, db):
    """CON el fix · flujo end-to-end del lead real (fulkro_app, contexto limpio):
    /consume (resuelve por token) → /me/consent → responder las 17 → /me/submit.
    Cubre los DOS caminos del fix (token-hash + session_id)."""
    sid, token = await _new_precliente_session(db)

    # Réplica de la request fresca del lead: rol prod, sin contexto.
    await _clear_tenant_context(db)
    await _assert_prod_role_no_context(db)

    # 1) /consume — el fix resuelve project_id por token_hash y setea contexto.
    r = await async_client.post("/api/v1/onboarding/consume", json={"token": token})
    assert r.status_code == 200, r.text
    secret = r.json()["session_secret"]
    assert r.json()["total_questions"] == 17
    headers = {
        "X-Onboarding-Session-Id": str(sid),
        "X-Onboarding-Session-Secret": secret,
    }

    # 2) gate Art.13: sin consentimiento, /me/next-question da 403.
    pre = await async_client.get("/api/v1/onboarding/me/next-question", headers=headers)
    assert pre.status_code == 403, pre.text

    # 3) consentimiento.
    c = await async_client.post(
        "/api/v1/onboarding/me/consent", json={"consented": True}, headers=headers,
    )
    assert c.status_code == 200, c.text

    # 4) responder hasta done (el fix de /me/* resuelve por session_id).
    answered = 0
    for _ in range(30):  # tope de seguridad
        nq = await async_client.get(
            "/api/v1/onboarding/me/next-question", headers=headers,
        )
        assert nq.status_code == 200, nq.text
        body = nq.json()
        if body["done"]:
            break
        q = body["question"]
        sub = await async_client.post(
            "/api/v1/onboarding/me/responses",
            json={"question_id": q["id"], "answer_value": _answer_for(q)},
            headers=headers,
        )
        assert sub.status_code == 200, sub.text
        answered += 1
    assert answered == 17, f"esperaba responder 17 · respondidas {answered}"

    # 5) submit final → completed.
    fin = await async_client.post(
        "/api/v1/onboarding/me/submit", json={"allow_partial": False}, headers=headers,
    )
    assert fin.status_code == 200, fin.text
    assert fin.json()["state"] == "completed"

    # 6) persistencia real: 17 filas OnboardingResponse para la sesión.
    n = (await db.execute(
        select(func.count()).select_from(OnboardingResponse).where(
            OnboardingResponse.session_id == sid
        )
    )).scalar()
    assert n == 17, f"esperaba 17 respuestas persistidas · hay {n}"
