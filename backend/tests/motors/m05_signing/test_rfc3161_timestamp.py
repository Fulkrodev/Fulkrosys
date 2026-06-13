"""Tests sellado de tiempo RFC 3161 · feat/fulkro-100 Ola D.

Cliente (sin red · asn1crypto) + API admin (auth/404/happy-path degradado).
NO golpea una TSA real en CI (FULKRO_TIMESTAMP_ENABLED apagado por defecto).
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from backend.app.core.timestamping import (
    build_timestamp_request,
    request_timestamp,
    verify_timestamp,
)


# ════════════════════════════════════════════════════════════════════
# Cliente RFC 3161 (puro · sin red)
# ════════════════════════════════════════════════════════════════════


def test_build_request_contains_digest():
    """El TimeStampReq DER lleva el digest SHA-256 en el message imprint."""
    from asn1crypto import tsp

    digest = hashlib.sha256(b"artefacto").digest()
    der = build_timestamp_request(digest, nonce=12345)
    parsed = tsp.TimeStampReq.load(der)
    assert parsed["message_imprint"]["hashed_message"].native == digest
    assert parsed["nonce"].native == 12345


@pytest.mark.asyncio
async def test_request_timestamp_disabled_by_default():
    """Sin FULKRO_TIMESTAMP_ENABLED → status 'disabled' (honesto · sin red)."""
    digest_hex = hashlib.sha256(b"x").hexdigest()
    result = await request_timestamp(digest_hex)
    assert result.status == "disabled"
    assert result.token_der is None


def test_verify_garbage_token_false():
    """verify_timestamp con token basura → False (degradación · no lanza)."""
    assert verify_timestamp(b"not-a-valid-der-token", "aa" * 32) is False


# ════════════════════════════════════════════════════════════════════
# API admin
# ════════════════════════════════════════════════════════════════════

pytestmark = pytest.mark.real_auth

_BASE = "/api/v1/admin/signing/events"


async def _login_owner(async_client) -> str:
    res = await async_client.post("/api/v1/_dev/login-as-marcos")
    assert res.status_code == 200, res.text
    return async_client.cookies.get("fulkro_csrf") or ""


async def _make_signing_event(db, project_id: str) -> str:
    """Crea un signing_intent + signing_event mínimos · devuelve event_id."""
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": project_id},
    )
    intent_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())
    expires = (datetime.now(timezone.utc) + timedelta(days=1))
    await db.execute(
        text(
            "INSERT INTO signing_intents "
            "(id, project_id, signable_type, document_hash_sha256, "
            "expires_at, created_by_user_id) "
            "VALUES (:id, :pid, 'dda', :h, :exp, :uid)"
        ),
        {
            "id": intent_id, "pid": project_id, "h": "a" * 64,
            "exp": expires, "uid": str(uuid.uuid4()),
        },
    )
    await db.execute(
        text(
            "INSERT INTO signing_events "
            "(id, project_id, signing_intent_id, event_type, actor_type, "
            "event_hash_sha256) VALUES (:id, :pid, :iid, "
            "'signature_generated', 'admin', :h)"
        ),
        {"id": event_id, "pid": project_id, "iid": intent_id, "h": "b" * 64},
    )
    await db.commit()
    return event_id


@pytest.mark.asyncio
async def test_timestamp_requires_owner(async_client):
    res = await async_client.post(f"{_BASE}/{uuid.uuid4()}/timestamp")
    assert res.status_code in (401, 403), res.text


@pytest.mark.asyncio
async def test_timestamp_nonexistent_event_404(async_client):
    csrf = await _login_owner(async_client)
    res = await async_client.post(
        f"{_BASE}/{uuid.uuid4()}/timestamp",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 404, res.text


@pytest.mark.asyncio
async def test_timestamp_event_records_disabled_status(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    event_id = await _make_signing_event(db, project_id)
    csrf = await _login_owner(async_client)

    res = await async_client.post(
        f"{_BASE}/{event_id}/timestamp", headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "disabled"  # TSA off en CI · honesto
    assert data["artifact_type"] == "signing_event"
    assert data["artifact_hash"] == "b" * 64
    assert data["has_token"] is False

    # GET devuelve el último sello.
    got = await async_client.get(f"{_BASE}/{event_id}/timestamp")
    assert got.status_code == 200, got.text
    assert got.json()["id"] == data["id"]
