"""Tests M24 expiration policy (Sesion 9 Paso 3.1).

Cubre:
- set_expiration explicito (datetime) y via review_period_months.
- apply_default_expiration por clasificacion heuristica.
- list_expiring_soon (proximos N dias).
- list_expired (ya caducados).
- auto_deprecate_expired (cron candidate).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.database import set_tenant_context
from backend.app.motors.m24_idms.idms_service import (
    DEFAULT_REVIEW_PERIOD_MONTHS,
    IDMSError,
    IDMSService,
    STATUS_APPROVED,
    STATUS_ARCHIVED,
    STATUS_DEPRECATED,
    STATUS_REVIEW,
)
from backend.tests.conftest import setup_test_project


async def _setup_project(db) -> tuple[str, str]:
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    return client_id, project_id


async def _create_doc(db, project_id: str, name: str, clasif_hint: str = "x") -> uuid.UUID:
    svc = IDMSService()
    r = await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre=name, contenido=f"body-{name}".encode(),
    )
    return r["document"].id


# ─────────── Defaults por clasificacion ───────────


def test_default_review_period_politica_12m():
    assert DEFAULT_REVIEW_PERIOD_MONTHS["politica"] == 12


def test_default_review_period_procedimiento_24m():
    assert DEFAULT_REVIEW_PERIOD_MONTHS["procedimiento"] == 24


def test_default_review_period_evidencia_none():
    # Evidencia NO tiene default (no caduca)
    assert "evidencia" not in DEFAULT_REVIEW_PERIOD_MONTHS


# ─────────── set_expiration ───────────


@pytest.mark.asyncio
async def test_set_expiration_explicit_datetime(db):
    _, project_id = await _setup_project(db)
    doc_id = await _create_doc(db, project_id, "politica_seguridad.pdf")
    svc = IDMSService()

    expires = datetime.now(timezone.utc) + timedelta(days=180)
    doc = await svc.set_expiration(db, doc_id, expires_at=expires)
    assert doc.expires_at is not None
    # Tolerancia 5 seg por redondeo timezone
    assert abs((doc.expires_at - expires).total_seconds()) < 5


@pytest.mark.asyncio
async def test_set_expiration_via_review_period_months(db):
    _, project_id = await _setup_project(db)
    doc_id = await _create_doc(db, project_id, "politica_seguridad.pdf")
    svc = IDMSService()

    before = datetime.now(timezone.utc)
    doc = await svc.set_expiration(db, doc_id, review_period_months=6)
    # 6 meses = ~180 dias desde now()
    expected_min = before + timedelta(days=179)
    expected_max = before + timedelta(days=181)
    assert doc.expires_at is not None
    assert expected_min <= doc.expires_at <= expected_max
    assert doc.review_period_months == 6


@pytest.mark.asyncio
async def test_set_expiration_negative_months_raises(db):
    _, project_id = await _setup_project(db)
    doc_id = await _create_doc(db, project_id, "politica.pdf")
    svc = IDMSService()
    with pytest.raises(IDMSError, match="review_period_months"):
        await svc.set_expiration(db, doc_id, review_period_months=-1)


# ─────────── apply_default_expiration ───────────


@pytest.mark.asyncio
async def test_apply_default_expiration_politica_sets_12m(db):
    _, project_id = await _setup_project(db)
    doc_id = await _create_doc(db, project_id, "politica_accesos.pdf")
    svc = IDMSService()

    doc = await svc.apply_default_expiration(db, doc_id)
    # intake auto-classifies "politica" -> 12m default
    assert doc.review_period_months == 12
    assert doc.expires_at is not None


@pytest.mark.asyncio
async def test_apply_default_expiration_evidencia_noop(db):
    _, project_id = await _setup_project(db)
    doc_id = await _create_doc(db, project_id, "evidencia_captura.png")
    svc = IDMSService()

    doc = await svc.apply_default_expiration(db, doc_id)
    # evidencia no tiene default -> review_period_months queda None
    assert doc.review_period_months is None
    assert doc.expires_at is None


# ─────────── list_expiring_soon + list_expired ───────────


@pytest.mark.asyncio
async def test_list_expiring_soon_30_days(db):
    _, project_id = await _setup_project(db)
    doc_near_id = await _create_doc(db, project_id, "politica_near.pdf")
    doc_far_id = await _create_doc(db, project_id, "politica_far.pdf")
    svc = IDMSService()

    now = datetime.now(timezone.utc)
    await svc.set_expiration(db, doc_near_id, expires_at=now + timedelta(days=15))
    await svc.set_expiration(db, doc_far_id, expires_at=now + timedelta(days=90))

    expiring = await svc.list_expiring_soon(
        db, uuid.UUID(project_id), days_ahead=30,
    )
    ids = [d.id for d in expiring]
    assert doc_near_id in ids
    assert doc_far_id not in ids


@pytest.mark.asyncio
async def test_list_expired(db):
    _, project_id = await _setup_project(db)
    doc_past_id = await _create_doc(db, project_id, "politica_caducada.pdf")
    doc_future_id = await _create_doc(db, project_id, "politica_viva.pdf")
    svc = IDMSService()

    now = datetime.now(timezone.utc)
    await svc.set_expiration(db, doc_past_id, expires_at=now - timedelta(days=10))
    await svc.set_expiration(db, doc_future_id, expires_at=now + timedelta(days=90))

    expired = await svc.list_expired(db, uuid.UUID(project_id))
    ids = [d.id for d in expired]
    assert doc_past_id in ids
    assert doc_future_id not in ids


@pytest.mark.asyncio
async def test_list_expiring_excludes_archived(db):
    """Documentos ya archived/deprecated NO aparecen en alertas."""
    _, project_id = await _setup_project(db)
    doc_id = await _create_doc(db, project_id, "politica_archivada.pdf")
    svc = IDMSService()

    # Archivar el documento (desde draft directo via transicion).
    from backend.app.motors.m24_idms.idms_service import STATUS_ARCHIVED
    await svc._transition_status(db, doc_id, STATUS_ARCHIVED)

    # Ponerle fecha pasada (ya caducado en teoria)
    now = datetime.now(timezone.utc)
    await svc.set_expiration(db, doc_id, expires_at=now - timedelta(days=5))

    expired = await svc.list_expired(db, uuid.UUID(project_id))
    ids = [d.id for d in expired]
    assert doc_id not in ids  # excluido por estar archived


# ─────────── auto_deprecate_expired ───────────


@pytest.mark.asyncio
async def test_auto_deprecate_expired_approved_goes_to_deprecated(db):
    _, project_id = await _setup_project(db)
    doc_id = await _create_doc(db, project_id, "politica_to_expire.pdf")
    svc = IDMSService()

    # Workflow: draft -> review -> approved
    await svc.submit_for_review(db, doc_id)
    from backend.app.models.auth import User
    from backend.tests.conftest import _admin_setup
    async with _admin_setup(db):
        user = User(
            email=f"u-{uuid.uuid4().hex[:8]}@test.es",
            display_name="U", password_hash="h",
        )
        db.add(user)
        await db.flush()
    await svc.approve_document(db, doc_id, user.id)

    # Poner fecha pasada
    now = datetime.now(timezone.utc)
    await svc.set_expiration(db, doc_id, expires_at=now - timedelta(days=2))

    # Auto-deprecate
    deprecated = await svc.auto_deprecate_expired(db, uuid.UUID(project_id))
    assert len(deprecated) == 1
    assert deprecated[0].id == doc_id
    assert deprecated[0].estado == STATUS_DEPRECATED


@pytest.mark.asyncio
async def test_auto_deprecate_expired_draft_goes_to_archived(db):
    """Un doc expired que NO fue approved se archiva (no deprecated)."""
    _, project_id = await _setup_project(db)
    doc_id = await _create_doc(db, project_id, "politica_draft_expire.pdf")
    svc = IDMSService()

    # Sin aprobar: estado legacy None -> se normaliza a draft
    now = datetime.now(timezone.utc)
    await svc.set_expiration(db, doc_id, expires_at=now - timedelta(days=2))

    deprecated = await svc.auto_deprecate_expired(db, uuid.UUID(project_id))
    assert len(deprecated) == 1
    assert deprecated[0].estado == STATUS_ARCHIVED  # no approved -> archived
