"""Tests M06 PolicySignoffService · SAN-E v3.MB-6 atom 1.

10 tests cubren:
  Tier resolution:
    1. test_get_expected_codes_basica_returns_10
    2. test_get_expected_codes_media_returns_18
    3. test_get_expected_codes_alta_returns_25
    4. test_invalid_tier_raises
  Listing + summary:
    5. test_list_policies_empty_project_returns_all_pending_creation
    6. test_list_policies_with_docs_returns_review_state
    7. test_summary_counters_correct
  Review action:
    8. test_review_policy_revisada_ok_persists
    9. test_review_policy_invalid_action_raises
  Bulk signoff:
    10. test_bulk_hash_deterministic_changes_when_review_changes
    11. test_mark_bulk_signed_links_all_documents
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m06_document_factory.policy_signoff_service import (
    InvalidReviewActionError,
    InvalidTierError,
    POLICIES_ALTA,
    POLICIES_BASICA,
    POLICIES_MEDIA,
    PolicySignoffService,
)
from backend.tests.conftest import setup_test_project


async def _set_project_tier(db: AsyncSession, project_id: str, tier: str) -> None:
    await db.execute(
        sa_text("UPDATE projects SET categoria_objetivo = :t WHERE id = :p"),
        {"t": tier, "p": project_id},
    )
    await db.flush()


async def _insert_doc(
    db: AsyncSession, project_id: str, template_codigo: str,
) -> uuid.UUID:
    doc_id = uuid.uuid4()
    await db.execute(
        sa_text(
            "INSERT INTO documents "
            "(id, project_id, nombre, template_codigo, estado, created_at) "
            "VALUES (:i, :p, :n, :t, 'draft', now())"
        ),
        {
            "i": str(doc_id),
            "p": project_id,
            "n": f"Doc {template_codigo}",
            "t": template_codigo,
        },
    )
    await db.flush()
    return doc_id


async def _create_user_id(db: AsyncSession, client_id: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    await db.execute(
        sa_text(
            "INSERT INTO client_users (id, client_id, email, password_hash, created_at) "
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


# ════════════════════════════════════════════════════════════════════
# Tier resolution
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_expected_codes_basica_returns_10(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    await _set_project_tier(db, project_id, "BASICA")
    svc = PolicySignoffService(db)

    tier, codes = await svc.get_expected_policy_codes(uuid.UUID(project_id))

    assert tier == "BASICA"
    assert len(codes) == 10
    assert codes == POLICIES_BASICA


@pytest.mark.asyncio
async def test_get_expected_codes_media_returns_18(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    await _set_project_tier(db, project_id, "MEDIA")
    svc = PolicySignoffService(db)

    tier, codes = await svc.get_expected_policy_codes(uuid.UUID(project_id))

    assert tier == "MEDIA"
    assert len(codes) == 18
    assert codes == POLICIES_MEDIA


@pytest.mark.asyncio
async def test_get_expected_codes_alta_returns_25(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    await _set_project_tier(db, project_id, "ALTA")
    svc = PolicySignoffService(db)

    tier, codes = await svc.get_expected_policy_codes(uuid.UUID(project_id))

    assert tier == "ALTA"
    assert len(codes) == 25
    assert codes == POLICIES_ALTA


@pytest.mark.asyncio
async def test_invalid_tier_raises(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    await _set_project_tier(db, project_id, "BOGUS_TIER")
    svc = PolicySignoffService(db)

    with pytest.raises(InvalidTierError):
        await svc.get_expected_policy_codes(uuid.UUID(project_id))


# ════════════════════════════════════════════════════════════════════
# Listing + summary
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_policies_empty_project_returns_all_pending_creation(
    db: AsyncSession,
):
    _, project_id = await setup_test_project(db)
    await _set_project_tier(db, project_id, "BASICA")
    svc = PolicySignoffService(db)

    items = await svc.list_policies_for_client(uuid.UUID(project_id))

    assert len(items) == 10
    assert all(i.document_id is None for i in items)
    assert all(i.client_review_status is None for i in items)
    assert items[0].template_codigo == "E-100"
    assert items[0].level == 1
    assert items[0].family == "fundamental"


@pytest.mark.asyncio
async def test_list_policies_with_docs_returns_review_state(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    await _set_project_tier(db, project_id, "BASICA")
    await _insert_doc(db, project_id, "E-100")
    await _insert_doc(db, project_id, "E-101")
    svc = PolicySignoffService(db)

    items = await svc.list_policies_for_client(uuid.UUID(project_id))

    assert len(items) == 10
    psi = next(i for i in items if i.template_codigo == "E-100")
    assert psi.document_id is not None
    assert psi.estado == "draft"
    assert psi.client_review_status is None  # not reviewed yet


@pytest.mark.asyncio
async def test_summary_counters_correct(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    await _set_project_tier(db, project_id, "BASICA")
    user_id = await _create_user_id(db, client_id)
    doc_e100 = await _insert_doc(db, project_id, "E-100")
    doc_e101 = await _insert_doc(db, project_id, "E-101")
    svc = PolicySignoffService(db)

    await svc.review_policy(doc_e100, "revisada_ok", None, user_id)
    await svc.review_policy(doc_e101, "con_pregunta", "Necesito aclaración", user_id)

    summary = await svc.get_summary(uuid.UUID(project_id))

    assert summary.tier == "BASICA"
    assert summary.expected_count == 10
    assert summary.generated_count == 2
    assert summary.revisada_ok_count == 1
    assert summary.with_questions_count == 1
    assert summary.ready_for_bulk_sign is False  # not all reviewed_ok


# ════════════════════════════════════════════════════════════════════
# Review action
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_review_policy_revisada_ok_persists(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    doc_id = await _insert_doc(db, project_id, "E-100")
    svc = PolicySignoffService(db)

    doc = await svc.review_policy(doc_id, "revisada_ok", None, user_id)

    assert doc.client_review_status == "revisada_ok"
    assert doc.client_reviewed_at is not None
    assert doc.client_reviewed_by_user_id == user_id


@pytest.mark.asyncio
async def test_review_policy_invalid_action_raises(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    doc_id = await _insert_doc(db, project_id, "E-100")
    svc = PolicySignoffService(db)

    with pytest.raises(InvalidReviewActionError):
        await svc.review_policy(doc_id, "approved", None, user_id)


@pytest.mark.asyncio
async def test_review_policy_con_pregunta_requires_note(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    doc_id = await _insert_doc(db, project_id, "E-100")
    svc = PolicySignoffService(db)

    with pytest.raises(InvalidReviewActionError):
        await svc.review_policy(doc_id, "con_pregunta", None, user_id)
    with pytest.raises(InvalidReviewActionError):
        await svc.review_policy(doc_id, "con_pregunta", "  ", user_id)


# ════════════════════════════════════════════════════════════════════
# Bulk signoff
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_bulk_hash_deterministic_changes_when_review_changes(
    db: AsyncSession,
):
    client_id, project_id = await setup_test_project(db)
    await _set_project_tier(db, project_id, "BASICA")
    user_id = await _create_user_id(db, client_id)
    doc_e100 = await _insert_doc(db, project_id, "E-100")
    svc = PolicySignoffService(db)

    hash1, _ = await svc.compute_bulk_document_hash(uuid.UUID(project_id))
    assert len(hash1) == 64

    hash2, _ = await svc.compute_bulk_document_hash(uuid.UUID(project_id))
    assert hash1 == hash2  # deterministic

    await svc.review_policy(doc_e100, "revisada_ok", None, user_id)

    hash3, _ = await svc.compute_bulk_document_hash(uuid.UUID(project_id))
    assert hash1 != hash3  # changes when review state changes


@pytest.mark.asyncio
async def test_mark_bulk_signed_links_all_documents(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    await _set_project_tier(db, project_id, "BASICA")
    doc_e100 = await _insert_doc(db, project_id, "E-100")
    doc_e101 = await _insert_doc(db, project_id, "E-101")
    svc = PolicySignoffService(db)
    intent_id = uuid.uuid4()

    count = await svc.mark_bulk_signed(uuid.UUID(project_id), intent_id)

    assert count == 2
    from backend.app.models.documents import Document
    d1 = await db.get(Document, doc_e100)
    d2 = await db.get(Document, doc_e101)
    assert d1.client_signing_intent_id == intent_id
    assert d2.client_signing_intent_id == intent_id
