"""Tests SAN-D MB-19.11 · Migration data script magic-links → client_tasks.

Cubre:
- Migration converte ONBOARDING_INICIAL → ClientTask portal con template
  template_prefix (migrated_onboarding_inicial_*).
- Migration converte APORTE_EVIDENCIA → ClientTask portal con
  expected_evidence_type/count populated.
- Idempotente: re-run skip rows ya en migration_log (UNIQUE magic_link_id).
- pending_review si no ClientUser yet (lead phase pre-onboarding).
- Dry-run NO escribe BD (rollback).
- YAML mappings valid (load + estructura).

Refs: ADR-042 · MB-19.11 backend/scripts/migrate_magic_links_to_tasks.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select, text

from backend.app.models.operations import MagicLink
from backend.app.motors.m12_magic_link.models_migration_log import (
    MagicLinkMigrationLog,
)
from backend.app.motors.m21_portal_cliente.models_tasks import ClientTask
from backend.scripts.migrate_magic_links_to_tasks import (
    load_migration_mappings,
    run_migration,
)
from backend.tests.conftest import _admin_setup


# ====================== YAML mappings ======================

def test_load_migration_mappings_valid_structure():
    """YAML mappings cargan + estructura completa per purpose."""
    mappings = load_migration_mappings()

    # Solo 2 purposes deprecated soft (ADR-042)
    assert "ONBOARDING_INICIAL" in mappings
    assert "APORTE_EVIDENCIA" in mappings
    assert len(mappings) == 2

    # Estructura per mapping
    for purpose_key, mapping in mappings.items():
        assert "title" in mapping
        assert "description" in mapping
        assert "cta_label" in mapping
        assert "cta_url_template" in mapping
        assert "template_prefix" in mapping
        assert "phase" in mapping
        assert "priority" in mapping
        assert "metadata_extras" in mapping


def test_yaml_mappings_aporte_evidencia_has_evidence_fields():
    """APORTE_EVIDENCIA YAML mapping configura evidence type/count."""
    mappings = load_migration_mappings()
    aporte = mappings["APORTE_EVIDENCIA"]
    assert aporte["expected_evidence_type"] == "documento"
    assert aporte["expected_evidence_count"] == 1


# ====================== Helpers ======================

async def _setup_full_environment(db, *, with_client_user=True):
    """Crea Client + Project + ClientUser opcional para tests integration."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    client_user_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, contacto_email, "
            "created_at) "
            "VALUES (:id, 'Mig Co', :cif, 'mig@migco.es', now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, "
            "categoria_objetivo, fase, lifecycle_state, created_at) "
            "VALUES (:id, :cid, 'Mig Project', 'MEDIA', "
            "'implantacion', 'ACTIVE', now())"
        ), {"id": str(project_id), "cid": str(client_id)})

        if with_client_user:
            await db.execute(text(
                "INSERT INTO client_users (id, client_id, email, "
                "full_name, password_hash, must_change_password, "
                "created_at) "
                "VALUES (:id, :cid, :email, 'Mig User', "
                "'hash_fake', FALSE, now())"
            ), {
                "id": str(client_user_id),
                "cid": str(client_id),
                "email": f"miguser-{uuid.uuid4().hex[:6]}@mig.es",
            })

    await db.flush()
    return client_id, project_id, (client_user_id if with_client_user else None)


async def _create_active_magic_link(
    db,
    *,
    project_id,
    purpose_value,
    recipient_email="recipient@test.es",
):
    """Crea MagicLink activo (no consumido · no revocado · no expirado)."""
    ml_id = uuid.uuid4()
    expira_at = datetime.now(timezone.utc) + timedelta(days=7)

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO magic_links (id, project_id, tipo_operacion, "
            "token_hash, expira_at, max_usos, usos, revocado, "
            "recipient_email, created_at) "
            "VALUES (:id, :pid, :purpose, :hash, :exp, 3, 0, FALSE, "
            ":email, now())"
        ), {
            "id": str(ml_id),
            "pid": str(project_id),
            "purpose": purpose_value,
            "hash": f"fake_hash_{uuid.uuid4().hex[:16]}",
            "exp": expira_at,
            "email": recipient_email,
        })
    await db.flush()
    return ml_id


# ====================== Migration core ======================

@pytest.mark.asyncio
async def test_migrate_aporte_evidencia_creates_client_task(db):
    """APORTE_EVIDENCIA magic-link activo + ClientUser → ClientTask creado."""
    client_id, project_id, client_user_id = await _setup_full_environment(db)
    ml_id = await _create_active_magic_link(
        db,
        project_id=project_id,
        purpose_value="aporte_evidencia",
        recipient_email="evidencia@mig.es",
    )

    stats = await run_migration(db, dry_run=False)

    assert stats["converted_count"] == 1
    assert stats["pending_review_count"] == 0
    assert stats["errors"] == 0

    # ClientTask creado
    tasks = (await db.scalars(
        select(ClientTask).where(ClientTask.project_id == project_id),
    )).all()
    assert len(tasks) == 1
    task = tasks[0]
    assert task.template_id.startswith("migrated_aporte_evidencia_")
    assert task.phase == "implantacion"
    assert task.title == "Sube las evidencias pendientes"
    assert task.expected_evidence_type == "documento"
    assert task.expected_evidence_count == 1
    assert task.client_user_id == client_user_id
    assert task.cta_url == "/client-portal/evidencias"
    assert task.metadata_jsonb["migrated_from_magic_link"] == str(ml_id)
    assert task.metadata_jsonb["original_purpose"] == "aporte_evidencia"

    # MagicLink revocado
    ml = await db.get(MagicLink, ml_id)
    assert ml.revocado is True
    assert ml.revoked_at is not None

    # Audit log row creado
    log = (await db.scalars(
        select(MagicLinkMigrationLog).where(
            MagicLinkMigrationLog.magic_link_id == ml_id,
        ),
    )).first()
    assert log is not None
    assert log.migration_action == "converted_to_task"
    assert log.original_purpose == "aporte_evidencia"
    assert log.target_task_id == task.id


@pytest.mark.asyncio
async def test_migrate_onboarding_inicial_creates_client_task(db):
    """ONBOARDING_INICIAL magic-link activo + ClientUser → ClientTask creado."""
    client_id, project_id, client_user_id = await _setup_full_environment(db)
    ml_id = await _create_active_magic_link(
        db,
        project_id=project_id,
        purpose_value="onboarding_inicial",
        recipient_email="onboarding@mig.es",
    )

    stats = await run_migration(db, dry_run=False)
    assert stats["converted_count"] == 1

    tasks = (await db.scalars(
        select(ClientTask).where(ClientTask.project_id == project_id),
    )).all()
    assert len(tasks) == 1
    task = tasks[0]
    assert task.template_id.startswith("migrated_onboarding_inicial_")
    # ONBOARDING_INICIAL phase=onboarding (YAML default · pero project.fase
    # actual ACTIVE='implantacion' override · matches mb-19.11 strategy)
    assert task.phase == "implantacion"
    assert task.title == "Completa tu acceso al portal cliente"
    assert task.cta_url == "/client-portal/login"


@pytest.mark.asyncio
async def test_migrate_idempotent_no_duplicate_tasks_or_logs(db):
    """Re-run script · idempotente · NO duplica tasks ni logs.

    Note: post-revoke ML queda fuera del query (filtra revocado=False) ·
    re-run no entra al loop · idempotencia garantizada por:
    1. UNIQUE magic_link_id en magic_link_migration_log (DB constraint)
    2. ML revocado=True post-procesamiento filtrado out
    """
    client_id, project_id, _ = await _setup_full_environment(db)
    ml_id = await _create_active_magic_link(
        db,
        project_id=project_id,
        purpose_value="aporte_evidencia",
    )

    stats1 = await run_migration(db, dry_run=False)
    assert stats1["converted_count"] == 1

    # Count tasks + logs post run1
    tasks_count_1 = (await db.scalars(
        select(ClientTask).where(ClientTask.project_id == project_id),
    )).all()
    logs_count_1 = (await db.scalars(
        select(MagicLinkMigrationLog).where(
            MagicLinkMigrationLog.magic_link_id == ml_id,
        ),
    )).all()
    assert len(tasks_count_1) == 1
    assert len(logs_count_1) == 1

    # Second run · ML revocado · query no lo retorna · 0 conversions
    stats2 = await run_migration(db, dry_run=False)
    assert stats2["converted_count"] == 0

    # Counts no cambian (idempotente verificado)
    tasks_count_2 = (await db.scalars(
        select(ClientTask).where(ClientTask.project_id == project_id),
    )).all()
    logs_count_2 = (await db.scalars(
        select(MagicLinkMigrationLog).where(
            MagicLinkMigrationLog.magic_link_id == ml_id,
        ),
    )).all()
    assert len(tasks_count_2) == 1
    assert len(logs_count_2) == 1


@pytest.mark.asyncio
async def test_migrate_pending_review_if_no_client_user(db):
    """Sin ClientUser · log pending_review · NO crea task."""
    client_id, project_id, _ = await _setup_full_environment(
        db, with_client_user=False,
    )
    ml_id = await _create_active_magic_link(
        db,
        project_id=project_id,
        purpose_value="aporte_evidencia",
    )

    stats = await run_migration(db, dry_run=False)

    assert stats["converted_count"] == 0
    assert stats["pending_review_count"] == 1

    # NO ClientTask creado
    tasks = (await db.scalars(
        select(ClientTask).where(ClientTask.project_id == project_id),
    )).all()
    assert len(tasks) == 0

    # Migration log con action=pending_review
    log = (await db.scalars(
        select(MagicLinkMigrationLog).where(
            MagicLinkMigrationLog.magic_link_id == ml_id,
        ),
    )).first()
    assert log is not None
    assert log.migration_action == "pending_review"
    assert log.target_task_id is None
    assert "No ClientUser" in (log.notes or "")


@pytest.mark.asyncio
async def test_migrate_skips_legitimate_purposes(db):
    """Magic-link con purpose legítimo (FIRMA_DOCUMENTO) NO procesado."""
    client_id, project_id, _ = await _setup_full_environment(db)
    ml_id = await _create_active_magic_link(
        db,
        project_id=project_id,
        purpose_value="firma_documento",  # NO en deprecated_soft
    )

    stats = await run_migration(db, dry_run=False)

    # NO procesa magic-links legítimos
    assert stats["converted_count"] == 0
    assert stats["pending_review_count"] == 0

    # Magic-link sigue activo
    ml = await db.get(MagicLink, ml_id)
    assert ml.revocado is False

    # Sin migration log row
    log = (await db.scalars(
        select(MagicLinkMigrationLog).where(
            MagicLinkMigrationLog.magic_link_id == ml_id,
        ),
    )).first()
    assert log is None


@pytest.mark.asyncio
async def test_migrate_dry_run_no_writes(db):
    """Dry-run identifica candidatos pero NO escribe BD."""
    client_id, project_id, _ = await _setup_full_environment(db)
    ml_id = await _create_active_magic_link(
        db,
        project_id=project_id,
        purpose_value="aporte_evidencia",
    )

    stats = await run_migration(db, dry_run=True)

    # Stats reportan converted=1 pero NO escribió
    assert stats["dry_run"] is True
    assert stats["converted_count"] == 1

    # NO ClientTask en BD
    tasks = (await db.scalars(
        select(ClientTask).where(ClientTask.project_id == project_id),
    )).all()
    assert len(tasks) == 0

    # MagicLink NO revocado
    ml = await db.get(MagicLink, ml_id)
    assert ml.revocado is False

    # Sin migration_log row
    log = (await db.scalars(
        select(MagicLinkMigrationLog).where(
            MagicLinkMigrationLog.magic_link_id == ml_id,
        ),
    )).first()
    assert log is None


@pytest.mark.asyncio
async def test_migrate_skips_revoked_or_expired(db):
    """Magic-links ya revocados/expirados NO procesados."""
    client_id, project_id, _ = await _setup_full_environment(db)

    # Crear magic-link revocado
    ml_revoked_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO magic_links (id, project_id, tipo_operacion, "
            "token_hash, expira_at, max_usos, usos, revocado, revoked_at, "
            "recipient_email, created_at) "
            "VALUES (:id, :pid, 'aporte_evidencia', :hash, "
            ":exp, 1, 0, TRUE, now(), 'rev@test.es', now())"
        ), {
            "id": str(ml_revoked_id),
            "pid": str(project_id),
            "hash": f"hash_rev_{uuid.uuid4().hex[:8]}",
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
        })

    # Crear magic-link expirado
    ml_expired_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO magic_links (id, project_id, tipo_operacion, "
            "token_hash, expira_at, max_usos, usos, revocado, "
            "recipient_email, created_at) "
            "VALUES (:id, :pid, 'aporte_evidencia', :hash, :exp, "
            "1, 0, FALSE, 'exp@test.es', now())"
        ), {
            "id": str(ml_expired_id),
            "pid": str(project_id),
            "hash": f"hash_exp_{uuid.uuid4().hex[:8]}",
            "exp": datetime.now(timezone.utc) - timedelta(days=1),
        })

    stats = await run_migration(db, dry_run=False)
    assert stats["converted_count"] == 0  # ambos filtrados out
