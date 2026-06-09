"""Tests AuditLogService hash chain (ADR-038 SAN-D MB-14.1)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from backend.app.models.client_portal import ClientUserAudit
from backend.app.motors.m21_portal_cliente.audit_log_service import (
    AuditLogService,
)
from backend.tests.conftest import _admin_setup


async def _setup_project_and_client_user(db):
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    client_user_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'Test', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )
        await db.execute(
            text(
                "INSERT INTO client_users (id, client_id, email, "
                "password_hash, created_at) "
                "VALUES (:id, :cid, :email, 'hash', now())"
            ),
            {
                "id": str(client_user_id),
                "cid": str(client_id),
                "email": f"u{client_user_id.hex[:6]}@t.es",
            },
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.flush()
    return project_id, client_user_id, client_id


@pytest.mark.asyncio
async def test_log_action_creates_first_chain_entry(db):
    project_id, client_user_id, client_id = await _setup_project_and_client_user(db)

    service = AuditLogService(db)
    audit = await service.log_action(
        project_id=project_id,
        client_user_id=client_user_id,
        action_type="LOGIN",
        action_data={"login_method": "email_password"},
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        client_id=client_id,
    )

    assert audit.chain_index == 0
    assert audit.prev_hash is None
    assert audit.current_hash is not None
    assert len(audit.current_hash) == 64
    assert audit.action_type == "LOGIN"


@pytest.mark.asyncio
async def test_chain_index_increments_per_project(db):
    project_id, client_user_id, _ = await _setup_project_and_client_user(db)

    service = AuditLogService(db)
    a1 = await service.log_action(
        project_id, client_user_id, "LOGIN", {"a": 1},
    )
    a2 = await service.log_action(
        project_id, client_user_id, "VIEW_DASHBOARD", {"b": 2},
    )
    a3 = await service.log_action(
        project_id, client_user_id, "VIEW_TASKS", {"c": 3},
    )

    assert (a1.chain_index, a2.chain_index, a3.chain_index) == (0, 1, 2)
    assert a2.prev_hash == a1.current_hash
    assert a3.prev_hash == a2.current_hash


@pytest.mark.asyncio
async def test_chain_integrity_valid_returns_true(db):
    project_id, client_user_id, _ = await _setup_project_and_client_user(db)

    service = AuditLogService(db)
    await service.log_action(project_id, client_user_id, "LOGIN", {"x": 1})
    await service.log_action(project_id, client_user_id, "VIEW_TASKS", {"y": 2})
    await service.log_action(project_id, client_user_id, "LOGOUT", {})

    is_valid, broken_at = await service.verify_chain_integrity(project_id)
    assert is_valid is True
    assert broken_at is None


@pytest.mark.asyncio
async def test_chain_integrity_detects_tampering(db):
    project_id, client_user_id, _ = await _setup_project_and_client_user(db)

    service = AuditLogService(db)
    await service.log_action(project_id, client_user_id, "LOGIN", {"x": 1})
    await service.log_action(project_id, client_user_id, "VIEW_TASKS", {"y": 2})

    # Tamper: modify metadata_jsonb of chain_index=1 (sin actualizar hash)
    await db.execute(
        text(
            "UPDATE client_user_audit SET metadata_jsonb = :new "
            "WHERE project_id = :pid AND chain_index = 1"
        ),
        {"new": '{"y": 999}', "pid": str(project_id)},
    )
    await db.flush()

    is_valid, broken_at = await service.verify_chain_integrity(project_id)
    assert is_valid is False
    assert broken_at == 1


@pytest.mark.asyncio
async def test_list_actions_filters(db):
    project_id, client_user_id, _ = await _setup_project_and_client_user(db)

    service = AuditLogService(db)
    await service.log_action(project_id, client_user_id, "LOGIN", {})
    await service.log_action(project_id, client_user_id, "VIEW_TASKS", {})
    await service.log_action(project_id, client_user_id, "LOGOUT", {})

    all_actions = await service.list_actions(project_id)
    assert len(all_actions) == 3

    only_login = await service.list_actions(project_id, action_type="LOGIN")
    assert len(only_login) == 1
    assert only_login[0].action_type == "LOGIN"


@pytest.mark.asyncio
async def test_export_chain_includes_metadata(db):
    project_id, client_user_id, _ = await _setup_project_and_client_user(db)

    service = AuditLogService(db)
    await service.log_action(
        project_id, client_user_id, "LOGIN",
        {"login_method": "email"},
        ip_address="10.0.0.1",
    )

    export = await service.export_chain(project_id)
    assert export["project_id"] == str(project_id)
    assert export["chain_integrity"]["valid"] is True
    assert len(export["records"]) == 1
    record = export["records"][0]
    assert record["chain_index"] == 0
    assert record["action_type"] == "LOGIN"
    assert record["ip_address"] == "10.0.0.1"


@pytest.mark.asyncio
async def test_pre_mb14_rows_ignored_in_chain_verification(db):
    """Rows pre-MB-14 con chain_index NULL · ignoradas en chain check
    (DEC-MB14-1 backward compat)."""
    project_id, client_user_id, client_id = await _setup_project_and_client_user(db)

    # Insert row pre-MB-14 (chain_index NULL · sin hash)
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO client_user_audit "
                "(id, client_user_id, client_id, action, action_type, "
                "metadata_jsonb, created_at) "
                "VALUES (gen_random_uuid(), :cuid, :cid, 'login_success', "
                "NULL, '{}'::jsonb, now())"
            ),
            {"cuid": str(client_user_id), "cid": str(client_id)},
        )
    await db.flush()

    # Service log_action con hash chain (debe ignorar pre-MB-14 row)
    service = AuditLogService(db)
    a1 = await service.log_action(
        project_id, client_user_id, "LOGIN", {"x": 1},
    )

    # Chain verification opera solo sobre chain_index NOT NULL · 1 record
    is_valid, broken_at = await service.verify_chain_integrity(project_id)
    assert is_valid is True
    assert broken_at is None
    assert a1.chain_index == 0  # First MB-14 chain entry
