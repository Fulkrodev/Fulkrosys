"""Tests M25 mark_audit_passed · Sesión 3B-2B.6 Cluster 1 Phase 2.

Verifica:
1. mark_audit_passed con result='passed' AND cascade_certify=True →
   audit columns set + auto-cascade mark_certified → lifecycle_state CERTIFIED
2. mark_audit_passed con result='observed' → audit columns set · NO cascade
3. mark_audit_passed result='failed' · NO cascade · audit columns reflect failed
4. Idempotency · re-mark raises LifecyclePaso4Error
5. result inválido raises LifecyclePaso4Error
6. CHECK constraint DB rejects invalid result direct UPDATE attempt
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.database import set_tenant_context
from backend.app.models.core import Project
from backend.app.motors.m25_lifecycle.lifecycle_paso4 import (
    LifecyclePaso4Error,
    LifecyclePaso4Service,
)
from backend.tests.conftest import setup_test_project


pytestmark = pytest.mark.asyncio


async def _setup_project(db) -> uuid.UUID:
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id))
    return uuid.UUID(project_id)


async def test_mark_audit_passed_with_cascade_certifies_project(db):
    """result='passed' + cascade_certify=True · audit set + auto-certified."""
    project_id = await _setup_project(db)
    svc = LifecyclePaso4Service()

    result = await svc.mark_audit_passed(
        db, project_id,
        result="passed",
        audit_report_ref="E-702-ENAC-001",
        cascade_certify=True,
    )

    assert result["result"] == "passed"
    assert result["audit_report_ref"] == "E-702-ENAC-001"
    assert "certified_event_id" in result
    assert result["lifecycle_state"] == "CERTIFIED"

    project = (await db.execute(
        select(Project).where(Project.id == project_id),
    )).scalar_one()
    assert project.audit_result == "passed"
    assert project.audit_passed_at is not None
    assert project.audit_report_ref == "E-702-ENAC-001"
    assert project.certified_at == date.today()
    assert project.lifecycle_state == "CERTIFIED"


async def test_mark_audit_passed_observed_no_cascade(db):
    """result='observed' · audit columns set · NO cascade certified."""
    project_id = await _setup_project(db)
    svc = LifecyclePaso4Service()

    result = await svc.mark_audit_passed(
        db, project_id,
        result="observed",
        cascade_certify=True,
    )

    assert result["result"] == "observed"
    assert "certified_event_id" not in result, "observed result NO debe cascadar"

    project = (await db.execute(
        select(Project).where(Project.id == project_id),
    )).scalar_one()
    assert project.audit_result == "observed"
    assert project.certified_at is None
    assert project.lifecycle_state == "DRAFT"


async def test_mark_audit_passed_failed_records_correctly(db):
    """result='failed' · columns reflect failure · NO certified."""
    project_id = await _setup_project(db)
    svc = LifecyclePaso4Service()

    result = await svc.mark_audit_passed(
        db, project_id,
        result="failed",
        audit_report_ref="E-702-NEG-001",
        cascade_certify=True,
    )

    assert result["result"] == "failed"
    assert "certified_event_id" not in result

    project = (await db.execute(
        select(Project).where(Project.id == project_id),
    )).scalar_one()
    assert project.audit_result == "failed"
    assert project.audit_report_ref == "E-702-NEG-001"
    assert project.certified_at is None


async def test_mark_audit_passed_idempotency_raises(db):
    """Re-mark con audit ya registrado raises LifecyclePaso4Error."""
    project_id = await _setup_project(db)
    svc = LifecyclePaso4Service()

    await svc.mark_audit_passed(db, project_id, result="observed")

    with pytest.raises(LifecyclePaso4Error, match="audit result registrado"):
        await svc.mark_audit_passed(db, project_id, result="passed")


async def test_mark_audit_passed_invalid_result_raises(db):
    """result fuera enum allowed → LifecyclePaso4Error."""
    project_id = await _setup_project(db)
    svc = LifecyclePaso4Service()

    with pytest.raises(LifecyclePaso4Error, match="result inválido"):
        await svc.mark_audit_passed(db, project_id, result="not-valid")


async def test_passed_with_cascade_retainer_offer_emits_notification(db):
    """Cluster 1 Phase 3 · result=passed + cascade_certify + cascade_retainer_offer
    todos True · backend auto-emite retainer offer notification post cert."""
    from sqlalchemy import select, text as sa_text
    from backend.tests.conftest import _admin_setup

    project_id = await _setup_project(db)
    project = (await db.execute(
        select(Project).where(Project.id == project_id),
    )).scalar_one()

    # Seed ClientUser para que offer_retainer pueda derivar recipient_email
    from backend.app.auth.crypto import hash_password
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO client_users (id, client_id, email, password_hash, "
            "full_name, must_change_password, created_at) "
            "VALUES (gen_random_uuid(), :cid, :email, :pwh, 'Cliente Test', "
            "false, now())"
        ), {
            "cid": str(project.client_id),
            "email": "cliente-test@example.com",
            "pwh": hash_password("Test1234!"),
        })

    svc = LifecyclePaso4Service()
    result = await svc.mark_audit_passed(
        db, project_id,
        result="passed",
        cascade_certify=True,
        cascade_retainer_offer=True,
    )

    assert result["result"] == "passed"
    assert "certified_event_id" in result
    # Retainer offer cascaded successfully · notification_id present
    assert "retainer_offer_notification_id" in result, (
        "expected retainer offer cascade · got: " + str(result)
    )
    assert result.get("retainer_offer_url") == "/client-portal/retainer"


async def test_passed_without_client_user_skips_retainer_offer(db):
    """cascade_retainer_offer=True · NO ClientUser registrado · skip graceful (NO bloquea cert)."""
    project_id = await _setup_project(db)
    svc = LifecyclePaso4Service()

    result = await svc.mark_audit_passed(
        db, project_id,
        result="passed",
        cascade_certify=True,
        cascade_retainer_offer=True,
    )

    assert result["result"] == "passed"
    assert "certified_event_id" in result, "cert debe haber funcionado"
    # Retainer offer skipped graceful · NO crash
    assert "retainer_offer_skipped_reason" in result
    assert "ClientUser" in result["retainer_offer_skipped_reason"]


async def test_passed_cascade_retainer_disabled(db):
    """cascade_retainer_offer=False · cert sí pero NO retainer offer."""
    project_id = await _setup_project(db)
    svc = LifecyclePaso4Service()

    result = await svc.mark_audit_passed(
        db, project_id,
        result="passed",
        cascade_certify=True,
        cascade_retainer_offer=False,
    )

    assert result["result"] == "passed"
    assert "certified_event_id" in result
    assert "retainer_offer_notification_id" not in result
    assert "retainer_offer_skipped_reason" not in result


async def test_db_check_constraint_rejects_invalid_result(db):
    """DB CHECK constraint defence-in-depth · invalid value rejected at DB layer.

    Uses SAVEPOINT para evitar abortar la transacción outer (db fixture
    rolls back ANYWAY al final del test · but con SAVEPOINT podemos atrapar
    el error sin matar el cleanup RESET ROLE).
    """
    project_id = await _setup_project(db)
    from sqlalchemy.exc import IntegrityError

    # Probe constraint via SAVEPOINT · catch failure sin abortar outer tx
    try:
        async with db.begin_nested() as savepoint:
            await db.execute(sa_text(
                "UPDATE projects SET audit_result = 'invalid_value_xx' "
                "WHERE id = :pid"
            ), {"pid": str(project_id)})
            await db.flush()
        # Si llega aquí · CHECK constraint NO está activo · fail
        pytest.fail("CHECK constraint debe rechazar 'invalid_value_xx'")
    except IntegrityError as exc:
        # Expected · validation succeeded
        assert "projects_audit_result_check" in str(exc) or "check constraint" in str(exc).lower()
