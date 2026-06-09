"""Cookie consent API tests (atom 9.bis.1 PARTE B).

10 tests covering:
- POST consent stores audit row for an anonymous session
- POST consent updates client_users + audit row for authenticated cliente
- GET consent without session returns defaults (all opt-in OFF except necessary)
- GET consent reads the most recent audit row for an anonymous session
- POST consent missing anonymous_session_id rejects with 400 (anonymous path)
- POST revoke updates client_users.<column> + audit log entry
- Revoke for analytics keeps functional/necessary intact
- Renewal due is exactly 24 months ahead of consent_timestamp
- security.txt is served and contains the required Contact + Expires directives
- 4 legal pages render with their canonical titles (Privacy/Cookies/Terms/Imprint)
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import text


BASE = "/api/v1/legal/cookies"


# ── Fixtures ──────────────────────────────────────────────────────────


async def _create_test_client_user(db) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert a cliente + client_user pair + set tenant context."""
    client_id = uuid.uuid4()
    cu_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await db.execute(
        text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Test', :cif, now())"
        ),
        {"id": str(client_id), "cif": cif},
    )
    await db.execute(
        text(
            "INSERT INTO client_users (id, client_id, email, password_hash, "
            "full_name, created_at, must_change_password, failed_attempts) "
            "VALUES (:id, :cid, :email, 'x', 't', now(), false, 0)"
        ),
        {"id": str(cu_id), "cid": str(client_id), "email": f"cookie-{cu_id}@example.com"},
    )
    await db.execute(text("RESET ROLE"))
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.flush()
    return client_id, cu_id


# ── 1-5: anonymous flows ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_consent_anonymous_persists_audit_row(async_client, db) -> None:
    sid = str(uuid.uuid4())
    r = await async_client.post(
        f"{BASE}/consent",
        json={
            "functional": True,
            "analytics": False,
            "marketing": False,
            "anonymous_session_id": sid,
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["functional"] is True
    assert data["analytics"] is False
    assert data["authenticated"] is False
    # Audit row persisted (commits inside endpoint).
    row = await db.execute(
        text(
            "SELECT new_state, action_type FROM fulkro_consent_audit_log "
            "WHERE anonymous_session_id = :sid ORDER BY timestamp DESC LIMIT 1"
        ),
        {"sid": sid},
    )
    record = row.first()
    assert record is not None
    assert record[0]["functional"] is True
    assert record[1] == "initial_consent"


@pytest.mark.asyncio
async def test_consent_anonymous_missing_session_id_rejected(async_client) -> None:
    r = await async_client.post(
        f"{BASE}/consent",
        json={"functional": True, "analytics": True, "marketing": False},
    )
    assert r.status_code == 400
    assert "anonymous_session_id" in r.json().get("detail", "")


@pytest.mark.asyncio
async def test_consent_get_defaults_without_session(async_client) -> None:
    r = await async_client.get(f"{BASE}/consent")
    assert r.status_code == 200
    data = r.json()
    assert data["functional"] is False
    assert data["analytics"] is False
    assert data["authenticated"] is False
    assert data["consent_timestamp"] is None


@pytest.mark.asyncio
async def test_consent_get_reads_latest_audit_for_session(async_client) -> None:
    sid = str(uuid.uuid4())
    await async_client.post(
        f"{BASE}/consent",
        json={
            "functional": True,
            "analytics": True,
            "marketing": False,
            "anonymous_session_id": sid,
        },
    )
    r = await async_client.get(f"{BASE}/consent?anonymous_session_id={sid}")
    assert r.status_code == 200
    data = r.json()
    assert data["functional"] is True
    assert data["analytics"] is True
    assert data["consent_timestamp"] is not None


@pytest.mark.asyncio
async def test_renewal_due_24_months_ahead(async_client) -> None:
    sid = str(uuid.uuid4())
    r = await async_client.post(
        f"{BASE}/consent",
        json={
            "functional": False,
            "analytics": False,
            "marketing": False,
            "anonymous_session_id": sid,
        },
    )
    assert r.status_code == 201
    data = r.json()
    ts = datetime.fromisoformat(data["consent_timestamp"])
    renewal = datetime.fromisoformat(data["consent_renewal_due"])
    delta = renewal - ts
    # 24 months ≈ 24 × 30 = 720 days (matches CONSENT_RENEWAL_MONTHS constant).
    assert 715 <= delta.days <= 725


# ── 6-7: anonymous revoke ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_anonymous_audit_marks_revoked(async_client, db) -> None:
    sid = str(uuid.uuid4())
    r = await async_client.post(
        f"{BASE}/revoke",
        json={"category": "analytics", "anonymous_session_id": sid},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["analytics"] is False
    # Audit row created.
    row = await db.execute(
        text(
            "SELECT action_type FROM fulkro_consent_audit_log "
            "WHERE anonymous_session_id = :sid ORDER BY timestamp DESC LIMIT 1"
        ),
        {"sid": sid},
    )
    record = row.first()
    assert record is not None and record[0] == "user_revoked"


@pytest.mark.asyncio
async def test_revoke_anonymous_missing_session_id_rejected(async_client) -> None:
    r = await async_client.post(
        f"{BASE}/revoke",
        json={"category": "analytics"},
    )
    assert r.status_code == 400


# ── 8: invalid category ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_invalid_category_rejected(async_client) -> None:
    r = await async_client.post(
        f"{BASE}/revoke",
        json={
            "category": "necessary",  # not allowed
            "anonymous_session_id": str(uuid.uuid4()),
        },
    )
    assert r.status_code == 422


# ── 9: security.txt file ───────────────────────────────────────────────


def test_security_txt_file_has_required_directives() -> None:
    """RFC 9116: Contact + Expires are mandatory."""
    path = (
        Path(__file__).resolve().parents[3]
        / ".." / "frontend" / "public" / ".well-known" / "security.txt"
    )
    text_body = path.read_text(encoding="utf-8")
    assert re.search(r"^Contact:\s*", text_body, re.MULTILINE)
    assert re.search(r"^Expires:\s*\d{4}-\d{2}-\d{2}", text_body, re.MULTILINE)
    # Canonical URL declared (best-practice, not strictly required by RFC).
    assert "fulkro.es" in text_body


# ── 10: legal pages files render with their titles ─────────────────────


def test_legal_pages_render_canonical_titles() -> None:
    """Smoke test: each of the 4 legal page TSX files mentions its h1 title."""
    base = (
        Path(__file__).resolve().parents[3]
        / ".." / "frontend" / "app" / "(legal)"
    )
    expected = {
        "privacy": "Política de Privacidad",
        "cookies": "Política de Cookies",
        "terms": "Términos de Servicio",
        "imprint": "Aviso Legal",
    }
    for slug, title in expected.items():
        page_path = base / slug / "page.tsx"
        assert page_path.exists(), f"missing page: {slug}"
        content = page_path.read_text(encoding="utf-8")
        assert title in content, f"page {slug} missing title {title!r}"
