"""Tests M05 signing history service · SAN-E v3.MB-6 atom 0.2.

4 tests cubren:
  1. test_history_empty_project_returns_empty_list
  2. test_history_with_pending_intent_no_signed_at
  3. test_history_with_signed_intent_returns_signed_at_and_chain_position
  4. test_history_multiple_signed_intents_chain_position_ordered
"""
from __future__ import annotations

import hashlib
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m05_signing.service import SigningService
from backend.tests.conftest import setup_test_project


def _doc_hash(content: str = "test-doc") -> str:
    return hashlib.sha256(content.encode()).hexdigest()


async def _create_user_id(db: AsyncSession, client_id: str) -> uuid.UUID:
    from sqlalchemy import text as sa_text
    user_id = uuid.uuid4()
    await db.execute(
        sa_text(
            "INSERT INTO client_users "
            "(id, client_id, email, password_hash, created_at) "
            "VALUES (:uid, :cid, :email, 'x', now())"
        ),
        {
            "uid": str(user_id),
            "cid": client_id,
            "email": f"u{user_id.hex[:6]}@test.es",
        },
    )
    await db.flush()
    return user_id


@pytest.mark.asyncio
async def test_history_empty_project_returns_empty_list(db: AsyncSession):
    """Project sin intents → history vacío."""
    _, project_id = await setup_test_project(db)
    svc = SigningService(db)

    history = await svc.get_signing_history(uuid.UUID(project_id))

    assert history == []


@pytest.mark.asyncio
async def test_history_with_pending_intent_no_signed_at(db: AsyncSession):
    """Intent pending → signed_at=None · chain_position=None."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="acta_comite",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )

    history = await svc.get_signing_history(uuid.UUID(project_id))

    assert len(history) == 1
    item = history[0]
    assert item["signed_at"] is None
    assert item["signature_event_id"] is None
    assert item["chain_position"] is None
    assert item["intent"].signable_type == "acta_comite"


@pytest.mark.asyncio
async def test_history_with_signed_intent_returns_signed_at_and_chain_position(
    db: AsyncSession,
):
    """Intent signed → signed_at populated · chain_position=1."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="acta_comite",
        document_hash_sha256=_doc_hash("contenido-1"),
        created_by_user_id=user_id,
    )
    await svc.sign(intent_id=intent.id, user_id=user_id)
    await db.flush()

    history = await svc.get_signing_history(uuid.UUID(project_id))

    assert len(history) == 1
    item = history[0]
    assert item["signed_at"] is not None
    assert item["signature_event_id"] is not None
    assert item["chain_position"] == 1
    assert item["event_hash_sha256"] is not None
    assert len(item["event_hash_sha256"]) == 64


@pytest.mark.asyncio
async def test_history_multiple_signed_intents_chain_position_ordered(
    db: AsyncSession,
):
    """3 signed intents → chain_position 1,2,3 en orden cronológico."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent1 = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="acta_comite",
        document_hash_sha256=_doc_hash("doc-1"),
        created_by_user_id=user_id,
    )
    await svc.sign(intent_id=intent1.id, user_id=user_id)

    intent2 = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="policy_approval",
        document_hash_sha256=_doc_hash("doc-2"),
        created_by_user_id=user_id,
    )
    await svc.sign(intent_id=intent2.id, user_id=user_id)

    intent3 = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="retainer_offer",
        document_hash_sha256=_doc_hash("doc-3"),
        created_by_user_id=user_id,
    )
    await svc.sign(intent_id=intent3.id, user_id=user_id)
    await db.flush()

    history = await svc.get_signing_history(uuid.UUID(project_id))

    assert len(history) == 3
    positions = [item["chain_position"] for item in history]
    assert positions == [1, 2, 3]
    types = [item["intent"].signable_type for item in history]
    assert types == ["acta_comite", "policy_approval", "retainer_offer"]
