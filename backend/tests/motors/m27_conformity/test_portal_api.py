"""Tests portal API cliente conformidad ENS (SAN-E v3.MB-5.6.C).

Cubre 5 endpoints + ConformityReadinessService + tier-aware flow:
- GET  /portal/conformidad/projects/{id}/declaration
- GET  /portal/conformidad/projects/{id}/readiness
- POST /portal/conformidad/projects/{id}/mark-reviewed
- GET  /portal/conformidad/projects/{id}/document-hash
- GET  /portal/conformidad/projects/{id}/post-signature

Escenario X audit-driven: BasicDeclarationRow tier-aware
- BASICA → declaration_type='initial'
- MEDIA/ALTA → declaration_type='commitment_pre_certification'
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text as sa_text

from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.tests.conftest import _admin_setup, setup_test_project


pytestmark = pytest.mark.asyncio


# ====================================================================
# Helpers
# ====================================================================


async def _setup_client_user(db, client_id: str) -> ClientUser:
    user_id = uuid.uuid4()
    email = f"portal-conformidad-{user_id.hex[:8]}@example.com"
    async with _admin_setup(db):
        await db.execute(sa_text("""
            INSERT INTO client_users
                (id, client_id, email, password_hash, must_change_password, created_at)
            VALUES (:id, :cid, :email, 'fake_hash', false, now())
        """), {"id": str(user_id), "cid": client_id, "email": email})
    return ClientUser(
        id=user_id,
        client_id=uuid.UUID(client_id),
        email=email,
        password_hash="fake_hash",
        must_change_password=False,
    )


async def _set_project_tier(db, project_id: str, tier: str) -> None:
    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "UPDATE projects SET categoria_objetivo = :tier WHERE id = :pid"
            ),
            {"tier": tier, "pid": project_id},
        )


async def _seed_declaration_draft(
    db,
    project_id: str,
    tier: str,
    *,
    signed: bool = False,
) -> str:
    """Pre-create BasicDeclarationRow draft tier-aware."""
    decl_id = uuid.uuid4()
    decl_type = "initial" if tier == "BASICA" else "commitment_pre_certification"
    signed_at = datetime.now(UTC) if signed else None
    signed_hash = "a" * 64 if signed else None
    status = "signed" if signed else "pending_client_signature"

    async with _admin_setup(db):
        await db.execute(sa_text("""
            INSERT INTO basic_declarations
                (id, project_id, declaration_type, responsible_person_name,
                 responsible_person_email, status, signed_at, signed_hash, created_at)
            VALUES (:id, :pid, :dtype, 'Marcos Mata', 'marcos@fulkro.es', :status,
                    :signed_at, :signed_hash, now())
        """), {
            "id": str(decl_id),
            "pid": project_id,
            "dtype": decl_type,
            "status": status,
            "signed_at": signed_at,
            "signed_hash": signed_hash,
        })
    return str(decl_id)


async def _seed_signing_event(
    db,
    project_id: str,
    signable_type: str,
) -> None:
    """Insert a signing_intent + signing_event 'signature_generated' for chain validation."""
    intent_id = uuid.uuid4()
    event_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(sa_text("""
            INSERT INTO signing_intents
                (id, project_id, signable_type, document_hash_sha256, status,
                 requires_step_up_otp, expires_at, created_by_user_id, created_at, updated_at)
            VALUES (:id, :pid, :stype, :hash, 'signed', true,
                    now() + interval '1 day', :uid, now(), now())
        """), {
            "id": str(intent_id),
            "pid": project_id,
            "stype": signable_type,
            "hash": "b" * 64,
            "uid": str(uuid.uuid4()),
        })
        await db.execute(sa_text("""
            INSERT INTO signing_events
                (id, project_id, signing_intent_id, event_type, actor_type,
                 event_hash_sha256, created_at)
            VALUES (:id, :pid, :iid, 'signature_generated', 'client_user',
                    :hash, now())
        """), {
            "id": str(event_id),
            "pid": project_id,
            "iid": str(intent_id),
            "hash": "c" * 64,
        })


async def _seed_evidence(db, project_id: str, count: int) -> None:
    async with _admin_setup(db):
        for i in range(count):
            await db.execute(sa_text("""
                INSERT INTO evidence
                    (id, project_id, tipo, vigente, created_at)
                VALUES (:id, :pid, 'document', true, now())
            """), {"id": str(uuid.uuid4()), "pid": project_id})


async def _seed_bulk_policies_signed(db, project_id: str, count: int) -> None:
    """SAN-E v3.MB-6 atom 1 · seed N policies bulk-signed (Q1.C híbrida).

    Inserta 1 signing_intent policy_approval status='signed' + N documents
    linkados via client_signing_intent_id. Replica el estado post firma bulk.
    """
    intent_id = uuid.uuid4()
    event_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(sa_text("""
            INSERT INTO signing_intents
                (id, project_id, signable_type, document_hash_sha256, status,
                 requires_step_up_otp, expires_at, created_by_user_id, created_at, updated_at)
            VALUES (:id, :pid, 'policy_approval', :hash, 'signed', false,
                    now() + interval '1 day', :uid, now(), now())
        """), {
            "id": str(intent_id),
            "pid": project_id,
            "hash": "d" * 64,
            "uid": str(uuid.uuid4()),
        })
        await db.execute(sa_text("""
            INSERT INTO signing_events
                (id, project_id, signing_intent_id, event_type, actor_type,
                 event_hash_sha256, created_at)
            VALUES (:id, :pid, :iid, 'signature_generated', 'client_user',
                    :hash, now())
        """), {
            "id": str(event_id),
            "pid": project_id,
            "iid": str(intent_id),
            "hash": "e" * 64,
        })
        codes = [f"E-1{i:02d}" for i in range(count)]
        for code in codes:
            await db.execute(sa_text("""
                INSERT INTO documents
                    (id, project_id, nombre, template_codigo, estado,
                     client_signing_intent_id, created_at)
                VALUES (:id, :pid, :n, :tc, 'approved', :iid, now())
            """), {
                "id": str(uuid.uuid4()),
                "pid": project_id,
                "n": f"Doc {code}",
                "tc": code,
                "iid": str(intent_id),
            })


async def _override_auth(async_client, user: ClientUser) -> None:
    from backend.app.main import app
    app.dependency_overrides[get_current_client_user] = lambda: user


def _clear_overrides() -> None:
    from backend.app.main import app
    if get_current_client_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_client_user]


async def _get_client_id(db, project_id: str) -> str:
    res = await db.execute(
        sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id},
    )
    return str(res.scalar())


# ====================================================================
# Tests · GET /declaration
# ====================================================================


async def test_declaration_returns_full_detail_basica(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _set_project_tier(db, project_id, "BASICA")
    await _seed_declaration_draft(db, project_id, "BASICA")

    await _override_auth(async_client, user)
    try:
        r = await async_client.get(
            f"/api/v1/portal/conformidad/projects/{project_id}/declaration",
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["declaration_type"] == "initial"
        assert body["tier"] == "BASICA"
        assert "E-041" in body["workflow_label"]
        assert "distintivo" in body["next_step_post_signature"].lower()
        assert body["responsible_person_name"] == "Marcos Mata"
        assert body["status"] == "pending_client_signature"
        assert body["signed_at"] is None
        assert body["client_reviewed_at"] is None
    finally:
        _clear_overrides()


async def test_declaration_404_no_draft(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)

    await _override_auth(async_client, user)
    try:
        r = await async_client.get(
            f"/api/v1/portal/conformidad/projects/{project_id}/declaration",
        )
        assert r.status_code == 404
    finally:
        _clear_overrides()


async def test_declaration_media_returns_commitment_type(db, async_client):
    """Tier-aware: project MEDIA → declaration_type='commitment_pre_certification'."""
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _set_project_tier(db, project_id, "MEDIA")
    await _seed_declaration_draft(db, project_id, "MEDIA")

    await _override_auth(async_client, user)
    try:
        r = await async_client.get(
            f"/api/v1/portal/conformidad/projects/{project_id}/declaration",
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["declaration_type"] == "commitment_pre_certification"
        assert body["tier"] == "MEDIA"
        assert "compromiso" in body["workflow_label"].lower()
        assert "auditor" in body["next_step_post_signature"].lower()
    finally:
        _clear_overrides()


# ====================================================================
# Tests · GET /readiness
# ====================================================================


async def test_readiness_complete_returns_ready_true(db, async_client):
    """All chain firmas + evidence enough → ready_for_conformity_sign=true."""
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _set_project_tier(db, project_id, "BASICA")

    # Seed chain firmas previas (Q4.A: DdA → MAGERIT → Policies → Pentest → Conformidad)
    await _seed_signing_event(db, project_id, "dda")
    await _seed_signing_event(db, project_id, "magerit_validation")
    await _seed_bulk_policies_signed(db, project_id, 10)  # BASICA min Q2.b
    await _seed_signing_event(db, project_id, "pentest_authorization")
    await _seed_evidence(db, project_id, 25)  # BASICA min

    await _override_auth(async_client, user)
    try:
        r = await async_client.get(
            f"/api/v1/portal/conformidad/projects/{project_id}/readiness",
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ready_for_conformity_sign"] is True
        assert body["blockers"] == []
        assert body["dda_signed_at"] is not None
        assert body["magerit_signed_at"] is not None
        assert body["pentest_signed_at"] is not None
        assert body["evidence_count"] >= 25
        # BASICA ahora incluye policies item (Q2.b MB-6 atom 1) · 5 items total
        assert len(body["items"]) == 5
        assert body["policies_signed_count"] >= 10
    finally:
        _clear_overrides()


async def test_readiness_missing_dda_returns_blocker(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _set_project_tier(db, project_id, "BASICA")

    # Skip DdA · seed only MAGERIT + Pentest
    await _seed_signing_event(db, project_id, "magerit_validation")
    await _seed_signing_event(db, project_id, "pentest_authorization")
    await _seed_evidence(db, project_id, 25)

    await _override_auth(async_client, user)
    try:
        r = await async_client.get(
            f"/api/v1/portal/conformidad/projects/{project_id}/readiness",
        )
        assert r.status_code == 200
        body = r.json()
        assert body["ready_for_conformity_sign"] is False
        assert any("DdA" in b for b in body["blockers"])
    finally:
        _clear_overrides()


async def test_readiness_alta_requires_more_evidence_and_policies(db, async_client):
    """ALTA tier requires 73 evidencias + 8 politicas firmadas."""
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _set_project_tier(db, project_id, "ALTA")

    # Chain firmas + 30 evidencias (< 73 ALTA min) + 0 politicas (< 8 ALTA min)
    await _seed_signing_event(db, project_id, "dda")
    await _seed_signing_event(db, project_id, "magerit_validation")
    await _seed_signing_event(db, project_id, "pentest_authorization")
    await _seed_evidence(db, project_id, 30)

    await _override_auth(async_client, user)
    try:
        r = await async_client.get(
            f"/api/v1/portal/conformidad/projects/{project_id}/readiness",
        )
        assert r.status_code == 200
        body = r.json()
        assert body["ready_for_conformity_sign"] is False
        assert any("Evidencias" in b for b in body["blockers"])
        assert any("Politicas" in b for b in body["blockers"])
        assert len(body["items"]) == 5  # ALTA adds policies item
    finally:
        _clear_overrides()


# ====================================================================
# Tests · POST /mark-reviewed
# ====================================================================


async def test_mark_reviewed_persists_state(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _set_project_tier(db, project_id, "BASICA")
    await _seed_declaration_draft(db, project_id, "BASICA")

    await _override_auth(async_client, user)
    try:
        r = await async_client.post(
            f"/api/v1/portal/conformidad/projects/{project_id}/mark-reviewed",
            json={"concerns_note": "Quiero confirmar fechas con Marcos antes"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["client_reviewed_at"] is not None
        assert body["client_reviewed_by_user_id"] == str(user.id)
        assert body["client_concerns_note"] == (
            "Quiero confirmar fechas con Marcos antes"
        )
    finally:
        _clear_overrides()


async def test_mark_reviewed_409_si_ya_firmada(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _set_project_tier(db, project_id, "BASICA")
    await _seed_declaration_draft(db, project_id, "BASICA", signed=True)

    await _override_auth(async_client, user)
    try:
        r = await async_client.post(
            f"/api/v1/portal/conformidad/projects/{project_id}/mark-reviewed",
            json={},
        )
        assert r.status_code == 409
        assert "firmada" in r.json()["detail"].lower()
    finally:
        _clear_overrides()


# ====================================================================
# Tests · GET /document-hash
# ====================================================================


async def test_document_hash_deterministic_includes_readiness(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _set_project_tier(db, project_id, "BASICA")
    await _seed_declaration_draft(db, project_id, "BASICA")
    await _seed_signing_event(db, project_id, "dda")

    await _override_auth(async_client, user)
    try:
        r1 = await async_client.get(
            f"/api/v1/portal/conformidad/projects/{project_id}/document-hash",
        )
        r2 = await async_client.get(
            f"/api/v1/portal/conformidad/projects/{project_id}/document-hash",
        )
        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200
        b1, b2 = r1.json(), r2.json()
        assert b1["document_hash_sha256"] == b2["document_hash_sha256"]
        assert len(b1["document_hash_sha256"]) == 64
        # NOT ready · cliente NO reviewed + chain incomplete
        assert b1["ready_for_signing"] is False
    finally:
        _clear_overrides()


# ====================================================================
# Tests · GET /post-signature
# ====================================================================


async def test_post_signature_basica_returns_distintivo_metadata(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _set_project_tier(db, project_id, "BASICA")
    await _seed_declaration_draft(db, project_id, "BASICA", signed=True)

    await _override_auth(async_client, user)
    try:
        r = await async_client.get(
            f"/api/v1/portal/conformidad/projects/{project_id}/post-signature",
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["declaration_type"] == "initial"
        assert "badge.svg" in body["distintivo_svg_url"]
        assert "cert-id" in body["cert_id_url"]
        assert "BASICA" in body["summary"]
    finally:
        _clear_overrides()


async def test_post_signature_media_returns_commitment_summary(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _set_project_tier(db, project_id, "MEDIA")
    await _seed_declaration_draft(db, project_id, "MEDIA", signed=True)

    await _override_auth(async_client, user)
    try:
        r = await async_client.get(
            f"/api/v1/portal/conformidad/projects/{project_id}/post-signature",
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["declaration_type"] == "commitment_pre_certification"
        assert body["next_step_eta_days_min"] == 30
        assert body["next_step_eta_days_max"] == 60
        assert "auditor" in body["next_step_summary"].lower()
        # NO distintivo en MEDIA flow
        assert "distintivo_svg_url" not in body
    finally:
        _clear_overrides()
