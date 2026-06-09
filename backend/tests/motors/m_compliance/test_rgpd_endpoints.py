"""RGPD cliente endpoints + services tests (atom 9.bis.2).

8 tests covering:
- Access ZIP aggregates cross-motor data (profile + projects + docs + chat)
- Access ZIP excludes admin-only sensitive fields (no password_hash etc.)
- Erasure request creates a pending row + is idempotent
- Erasure approved tombstones client_users in place
- Erasure preserves the audit_log (ENS retention obligation)
- Erasure rejected (audit retention) sets the right status + reason
- Portability JSON-LD shape (`@context`, `@type`, fulkro extensions)
- Portability ISO 8601 timestamps where present
"""
from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from backend.app.models.compliance_breach_erasure import (
    ERASURE_COMPLETED,
    ERASURE_PENDING,
    ERASURE_REJECTED_AUDIT,
)
from backend.app.motors.m_compliance.rgpd_services import (
    RGPDAccessService,
    RGPDErasureService,
    RGPDPortabilityService,
)


async def _create_test_client_user(db) -> tuple[uuid.UUID, uuid.UUID]:
    """Create cliente + client_user (superuser INSERT + RLS context for SUT)."""
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
            "full_name, dni, created_at, must_change_password, failed_attempts) "
            "VALUES (:id, :cid, :email, 'x', 'Test User', '11111111H', now(), "
            "false, 0)"
        ),
        {
            "id": str(cu_id),
            "cid": str(client_id),
            "email": f"test-{cu_id}@example.com",
        },
    )
    await db.execute(text("RESET ROLE"))
    # SUT runs as fulkro_app: install the tenant context the API endpoint
    # would set after require_client_user (mirror production flow).
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.flush()
    return client_id, cu_id


@pytest.mark.asyncio
async def test_access_zip_aggregates_cross_motor_data(db) -> None:
    client_id, cu_id = await _create_test_client_user(db)
    buf = await RGPDAccessService(db).build_zip(cu_id)
    assert isinstance(buf, io.BytesIO)
    with zipfile.ZipFile(buf, "r") as zf:
        names = set(zf.namelist())
    expected = {
        "README.md",
        "perfil/profile.json",
        "proyectos/projects.json",
        "documentos/documents.json",
        "comunicaciones/chat_messages.json",
        "comunicaciones/whatsapp.json",
        "firmas/signing_intents.json",
        "auditoria/audit_log.json",
        "metadata.json",
    }
    assert expected.issubset(names)


@pytest.mark.asyncio
async def test_access_zip_excludes_password_hash(db) -> None:
    client_id, cu_id = await _create_test_client_user(db)
    buf = await RGPDAccessService(db).build_zip(cu_id)
    with zipfile.ZipFile(buf, "r") as zf:
        profile_blob = zf.read("perfil/profile.json").decode("utf-8")
    profile = json.loads(profile_blob)
    # Sensitive fields must NEVER leak via the export.
    assert "password_hash" not in profile
    assert "failed_attempts" not in profile
    assert profile.get("email", "").startswith("test-")


@pytest.mark.asyncio
async def test_erasure_request_creates_pending_and_is_idempotent(db) -> None:
    client_id, cu_id = await _create_test_client_user(db)
    svc = RGPDErasureService(db)
    first = await svc.request_erasure(
        cu_id, tenant_client_id=client_id, reason="me marcho"
    )
    assert first.status == ERASURE_PENDING
    # Second call returns the same pending request (no duplicate row).
    second = await svc.request_erasure(
        cu_id, tenant_client_id=client_id, reason="duplicate call"
    )
    assert second.id == first.id


@pytest.mark.asyncio
async def test_erasure_approved_tombstones_client_user(db) -> None:
    client_id, cu_id = await _create_test_client_user(db)
    svc = RGPDErasureService(db)
    req = await svc.request_erasure(cu_id, tenant_client_id=client_id)
    completed = await svc.approve_and_anonymise(
        req.id, processed_by="marcos@fulkro.es"
    )
    assert completed.status == ERASURE_COMPLETED
    # Verify the underlying client_users row is anonymised.
    row = await db.execute(
        text(
            "SELECT email, full_name, dni FROM client_users WHERE id = :id"
        ),
        {"id": str(cu_id)},
    )
    record = row.first()
    assert record[0].startswith("anonymised_")
    assert record[0].endswith("@removed.fulkro.local")
    assert "Eliminado por solicitud" in record[1]
    assert record[2] is None


@pytest.mark.asyncio
async def test_erasure_preserves_audit_logs(db) -> None:
    """ENS RD 311/2022 art. 24.1: audit log must NOT be deleted."""
    client_id, cu_id = await _create_test_client_user(db)
    # Insert a representative audit_log row (as superuser to bypass triggers).
    # audit_log schema · tabla / registro_id / accion / usuario.
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await db.execute(
        text(
            "INSERT INTO audit_log (tabla, registro_id, accion, usuario) "
            "VALUES ('client_users', :uid, 'login', :uid_text)"
        ),
        {"uid": str(cu_id), "uid_text": str(cu_id)},
    )
    await db.execute(text("RESET ROLE"))
    await db.flush()

    svc = RGPDErasureService(db)
    req = await svc.request_erasure(cu_id, tenant_client_id=client_id)
    await svc.approve_and_anonymise(req.id, processed_by="marcos@fulkro.es")

    # Audit row still present.
    row = await db.execute(
        text("SELECT COUNT(*) FROM audit_log WHERE registro_id = :uid"),
        {"uid": str(cu_id)},
    )
    assert row.scalar() >= 1


@pytest.mark.asyncio
async def test_erasure_rejected_audit_retention(db) -> None:
    client_id, cu_id = await _create_test_client_user(db)
    svc = RGPDErasureService(db)
    req = await svc.request_erasure(cu_id, tenant_client_id=client_id)
    rejected = await svc.reject_audit_retention(
        req.id,
        processed_by="marcos@fulkro.es",
        rejection_reason="Datos sujetos a investigación pendiente.",
    )
    assert rejected.status == ERASURE_REJECTED_AUDIT
    assert "investigación" in (rejected.rejection_reason or "")
    # Test default rejection reason when omitted.
    req2 = await svc.request_erasure(
        cu_id, tenant_client_id=client_id, reason="duplicate-pending-cleanup"
    )
    # First request still rejected, so request_erasure returns a *new* row.
    rejected2 = await svc.reject_audit_retention(
        req2.id, processed_by="marcos@fulkro.es"
    )
    assert "RD 311/2022" in (rejected2.rejection_reason or "")


@pytest.mark.asyncio
async def test_portability_json_ld_shape(db) -> None:
    client_id, cu_id = await _create_test_client_user(db)
    payload = await RGPDPortabilityService(db).build_payload(cu_id)
    # JSON-LD contract.
    assert "@context" in payload
    assert payload["@type"] == "schema:Person"
    assert payload["@context"]["schema"] == "https://schema.org/"
    assert "fulkro" in payload["@context"]
    # Identifier matches the client_user_id we passed.
    assert payload["schema:identifier"] == str(cu_id)
    assert payload["schema:email"].startswith("test-")
    # Future-compat: consents list present even if empty (atom 9.bis.1 fills).
    assert isinstance(payload["fulkro:consents"], list)


@pytest.mark.asyncio
async def test_portability_iso_timestamps(db) -> None:
    client_id, cu_id = await _create_test_client_user(db)
    payload = await RGPDPortabilityService(db).build_payload(cu_id)
    # generated_at must parse as ISO 8601 UTC.
    generated = datetime.fromisoformat(payload["fulkro:generated_at"])
    assert generated.tzinfo is not None
