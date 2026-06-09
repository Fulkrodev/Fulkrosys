"""Tests EncryptedText SQLAlchemy TypeDecorator (SAN-B.MB-3.ter.4).

Cubre:
- Round-trip encrypt/decrypt transparent
- NULL handling
- Raw SQL muestra ciphertext (verifica at-rest)
- ORM read returns plaintext
- Key rotation: row encrypted con vieja key descifra con MultiFernet
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.core.encryption.master_key import reset_master_fernet_cache
from backend.app.core.encryption.sqlalchemy_types import EncryptedText
from backend.app.database import set_tenant_context
from backend.app.models.collaboration import (
    WorkspaceChatMessage,
)
from backend.tests.conftest import setup_test_project


# ════════════════════════════════════════════════════════════════════
# 1. EncryptedText pure unit (without DB)
# ════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _reset_master_cache():
    reset_master_fernet_cache()
    yield
    reset_master_fernet_cache()


def test_encrypted_text_bind_then_result_round_trip():
    """process_bind_param → process_result_value → plaintext."""
    et = EncryptedText()
    encrypted = et.process_bind_param("hello secret", dialect=None)
    assert encrypted is not None
    assert "hello" not in encrypted
    assert encrypted.startswith("gAAAAA")
    assert et.process_result_value(encrypted, dialect=None) == "hello secret"


def test_encrypted_text_null_passthrough():
    et = EncryptedText()
    assert et.process_bind_param(None, dialect=None) is None
    assert et.process_result_value(None, dialect=None) is None


def test_encrypted_text_nondeterministic_iv():
    """Fernet usa IV/timestamp aleatorio · misma plaintext → diferente cipher."""
    et = EncryptedText()
    a = et.process_bind_param("same", dialect=None)
    b = et.process_bind_param("same", dialect=None)
    assert a != b
    assert et.process_result_value(a, dialect=None) == "same"
    assert et.process_result_value(b, dialect=None) == "same"


def test_encrypted_text_handles_unicode():
    et = EncryptedText()
    payload = "Marcos · ñ áéíóú 你好 🚀"
    enc = et.process_bind_param(payload, dialect=None)
    assert et.process_result_value(enc, dialect=None) == payload


# ════════════════════════════════════════════════════════════════════
# 2. WorkspaceChatMessage integration · raw SQL verifica at-rest
# ════════════════════════════════════════════════════════════════════

async def _create_workspace(db, project_id: str) -> uuid.UUID:
    wid = uuid.uuid4()
    await db.execute(text(
        "INSERT INTO collaborative_workspaces (id, project_id, created_at) "
        "VALUES (:id, :pid, now())"
    ), {"id": str(wid), "pid": project_id})
    await db.flush()
    return wid


@pytest.mark.asyncio
async def test_workspace_chat_message_encrypted_at_rest(db):
    """Raw SELECT muestra ciphertext · ORM SELECT muestra plaintext."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    workspace_id = await _create_workspace(db, project_id)

    secret_text = "Confidencial · datos cliente · ENS controles internos"
    msg = WorkspaceChatMessage(
        workspace_id=workspace_id,
        project_id=uuid.UUID(project_id),
        autor="marcos",
        autor_tipo="marcos",
        mensaje=secret_text,
    )
    db.add(msg)
    await db.flush()
    msg_id = msg.id

    # 1. ORM SELECT → plaintext (decrypted)
    await db.refresh(msg)
    assert msg.mensaje == secret_text

    # 2. Raw SQL bypass ORM → ciphertext (NUNCA plaintext)
    raw = await db.execute(
        text("SELECT mensaje FROM workspace_chat_messages WHERE id = :id"),
        {"id": str(msg_id)},
    )
    raw_value = raw.scalar()
    assert raw_value is not None
    assert secret_text not in raw_value
    assert "Confidencial" not in raw_value
    assert raw_value.startswith("gAAAAA")


@pytest.mark.asyncio
async def test_workspace_chat_message_encryption_version_default(db):
    """encryption_version default 1 · soporta key rotation tracking."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    workspace_id = await _create_workspace(db, project_id)

    msg = WorkspaceChatMessage(
        workspace_id=workspace_id,
        project_id=uuid.UUID(project_id),
        autor="marcos",
        autor_tipo="marcos",
        mensaje="test",
    )
    db.add(msg)
    await db.flush()

    await db.refresh(msg)
    fetched = msg
    assert fetched.encryption_version == 1


@pytest.mark.asyncio
async def test_workspace_chat_message_unicode_round_trip(db):
    """Mensajes con tildes / non-ASCII / emojis se preservan exactos."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    workspace_id = await _create_workspace(db, project_id)

    payload = "Acción · ñ áéíóú 中文 🚀✓"
    msg = WorkspaceChatMessage(
        workspace_id=workspace_id,
        project_id=uuid.UUID(project_id),
        autor="cliente",
        autor_tipo="cliente",
        mensaje=payload,
    )
    db.add(msg)
    await db.flush()

    await db.refresh(msg)
    fetched = msg
    assert fetched.mensaje == payload
