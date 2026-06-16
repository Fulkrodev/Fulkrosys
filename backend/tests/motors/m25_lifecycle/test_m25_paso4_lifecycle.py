"""Tests M25 Paso 4 — cierre honesto sin retainer + backups + reactivacion.

Cubre:
- mark_certified + idempotencia
- offer_retainer con TTL 30d + bloqueo si no certificado
- handle_retainer_decision (accept / decline / thinking) + integracion M23
- start_grace_period sets fields + estado ENDED_CHURN
- process_grace_period_checkpoints: hitos 150/180/210/240 idempotentes
- generate_project_backup_zip: contenido, firma Ed25519, magic link
- delete_project_data: soft delete proyecto + hard delete personal data
- reactivate_project dentro/fuera de ventana de 60d
- process_backup_expirations: elimina backups expirados
- Enum MagicLinkPurpose: 3 nuevos con TTL correcto
- Celery beat schedule: 2 tasks registradas
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.core.celery_app import get_beat_schedule
from backend.app.database import set_tenant_context
from backend.app.models.core import Client, Project
from backend.app.models.lifecycle import (
    ProjectArchivedBackup,
)
from backend.app.motors.m12_magic_link.purposes import (
    MagicLinkPurpose, get_config,
)
from backend.app.motors.m25_lifecycle.backup_builder import (
    build_and_sign_backup_zip,
    verify_backup_signature,
)
from backend.app.motors.m25_lifecycle.lifecycle_paso4 import (
    BACKUP_DOWNLOAD_TTL_DAYS,
    GRACE_PERIOD_DAYS_DEFAULT,
    LifecyclePaso4Error,
    LifecyclePaso4Service,
    get_archived_backup,
    process_backup_expirations,
    process_grace_period_checkpoints,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ══════════════════════════════════════════════════════════════════════
# Helpers de setup
# ══════════════════════════════════════════════════════════════════════


async def _setup_project_with_tenant(db, *, certified: bool = False):
    client_id, project_id = await setup_test_project(db)
    cid = uuid.UUID(client_id)
    pid = uuid.UUID(project_id)
    if certified:
        async with _admin_setup(db):
            await db.execute(sa_text(
                "UPDATE projects SET certified_at = CURRENT_DATE, "
                "lifecycle_state = 'CERTIFIED' WHERE id = :pid"
            ), {"pid": project_id})
            await db.execute(sa_text(
                "UPDATE clients SET contacto_email = 'rseg@test.es' "
                "WHERE id = :cid"
            ), {"cid": client_id})
    await set_tenant_context(db, client_id=cid, project_id=pid)
    return cid, pid


async def _set_admin_role(db):
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))


# ══════════════════════════════════════════════════════════════════════
# MagicLinkPurpose — 3 nuevos
# ══════════════════════════════════════════════════════════════════════


class TestMagicLinkPurposesPaso4:
    def test_three_new_purposes_registered(self):
        assert MagicLinkPurpose.OFERTA_RETAINER.value == "oferta_retainer"
        assert MagicLinkPurpose.DESCARGA_BACKUP_ARCHIVO.value == "descarga_backup_archivo"
        assert MagicLinkPurpose.RECONSIDERACION_RETAINER.value == "reconsideracion_retainer"

    def test_oferta_retainer_ttl_30_days(self):
        cfg = get_config(MagicLinkPurpose.OFERTA_RETAINER)
        assert cfg["ttl_hours"] == 30 * 24

    def test_descarga_backup_ttl_60_days(self):
        cfg = get_config(MagicLinkPurpose.DESCARGA_BACKUP_ARCHIVO)
        assert cfg["ttl_hours"] == 60 * 24
        assert cfg["requires_otp"] is True
        assert cfg["max_uses"] >= 3  # re-descargas permitidas

    def test_reconsideracion_ttl_60_days(self):
        cfg = get_config(MagicLinkPurpose.RECONSIDERACION_RETAINER)
        assert cfg["ttl_hours"] == 60 * 24


# ══════════════════════════════════════════════════════════════════════
# Certificacion
# ══════════════════════════════════════════════════════════════════════


class TestMarkCertified:
    @pytest.mark.asyncio
    async def test_mark_certified_sets_fields_and_state(self, db):
        _, project_id = await _setup_project_with_tenant(db)
        svc = LifecyclePaso4Service()
        event = await svc.mark_certified(db, project_id)
        assert event.event_type == "certified"

        project = (await db.execute(
            select(Project).where(Project.id == project_id),
        )).scalar_one()
        assert project.certified_at == date.today()
        assert project.lifecycle_state == "CERTIFIED"

    @pytest.mark.asyncio
    async def test_mark_certified_idempotent_raises(self, db):
        _, project_id = await _setup_project_with_tenant(db)
        svc = LifecyclePaso4Service()
        await svc.mark_certified(db, project_id)
        with pytest.raises(LifecyclePaso4Error, match="ya certificado"):
            await svc.mark_certified(db, project_id)


# ══════════════════════════════════════════════════════════════════════
# Oferta retainer + decision
# ══════════════════════════════════════════════════════════════════════


class TestOfferRetainer:
    @pytest.mark.asyncio
    async def test_offer_retainer_generates_notification_and_event(self, db):
        """Post-MB-4.bis3 (ADR-020 v3): offer_retainer emite notification
        in-portal · NO magic_link · target_url /client-portal/retainer."""
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        result = await svc.offer_retainer(
            db, project_id,
            recipient_email="rseg@test.es",
            base_url="https://portal.test",
        )
        # Post-bis3: magic_link_id None · notification_id puede ser None
        # si no hay ClientUser activo · result.url apunta a portal
        assert result["magic_link_id"] is None
        assert result["url"] == "/client-portal/retainer"
        # Evento registrado
        events = await svc.get_lifecycle_events(db, project_id)
        kinds = {e.event_type for e in events}
        assert "retainer_offered" in kinds

    @pytest.mark.asyncio
    async def test_offer_retainer_requires_certified(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=False)
        svc = LifecyclePaso4Service()
        with pytest.raises(LifecyclePaso4Error, match="aun no certificado"):
            await svc.offer_retainer(
                db, project_id, recipient_email="rseg@test.es",
            )


class TestRetainerDecision:
    @pytest.mark.asyncio
    async def test_decision_accept_invokes_m23_create_retainer(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        result = await svc.handle_retainer_decision(
            db, project_id,
            decision="accept", tier="R_STD", precio_mensual=200.0,
        )
        assert result["decision"] == "accept"
        assert result["tier"] == "R_STD"

        from backend.app.models.retainer import RetainerContract
        row = (await db.execute(
            select(RetainerContract).where(
                RetainerContract.project_id == project_id,
            )
        )).scalar_one()
        assert row.perfil == "R_STD"

    @pytest.mark.asyncio
    async def test_decision_decline_starts_grace_period(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        await svc.handle_retainer_decision(
            db, project_id, decision="decline",
        )
        project = (await db.execute(
            select(Project).where(Project.id == project_id),
        )).scalar_one()
        assert project.lifecycle_state == "ENDED_CHURN"
        assert project.grace_period_started_at is not None
        assert project.grace_period_ends_at is not None
        # 240 dias de grace por defecto
        duration = project.grace_period_ends_at - project.grace_period_started_at
        assert abs(duration.days - GRACE_PERIOD_DAYS_DEFAULT) <= 1

    @pytest.mark.asyncio
    async def test_decision_thinking_starts_grace_period(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        result = await svc.handle_retainer_decision(
            db, project_id, decision="thinking",
        )
        assert result["decision"] == "thinking"
        assert "grace_period_event_id" in result

    @pytest.mark.asyncio
    async def test_decision_invalid_raises(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        with pytest.raises(LifecyclePaso4Error, match="decision invalida"):
            await svc.handle_retainer_decision(
                db, project_id, decision="maybe",
            )

    @pytest.mark.asyncio
    async def test_decision_accept_without_tier_raises(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        with pytest.raises(LifecyclePaso4Error, match="tier valido"):
            await svc.handle_retainer_decision(
                db, project_id, decision="accept",
            )


# ══════════════════════════════════════════════════════════════════════
# Grace period + checkpoints
# ══════════════════════════════════════════════════════════════════════


class TestGracePeriodCheckpoints:
    @pytest.mark.asyncio
    async def test_start_grace_period_sets_fields(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        event = await svc.start_grace_period(db, project_id, days=240)
        assert event.event_type == "grace_period_started"
        assert event.grace_period_days == 240

    @pytest.mark.asyncio
    async def test_day_150_sends_warning_to_marcos(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        started = datetime.now(timezone.utc) - timedelta(days=160)
        await svc.start_grace_period(
            db, project_id, started_at=started,
        )
        result = await process_grace_period_checkpoints(db)
        assert str(project_id) in result["warning_marcos_sent"]

        events = await svc.get_lifecycle_events(db, project_id)
        assert any(e.event_type == "warning_sent" for e in events)

    @pytest.mark.asyncio
    async def test_day_180_sends_reconsideration_to_client(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        started = datetime.now(timezone.utc) - timedelta(days=185)
        await svc.start_grace_period(
            db, project_id, started_at=started,
        )
        result = await process_grace_period_checkpoints(db)
        assert str(project_id) in result["reconsideration_client_sent"]

    @pytest.mark.asyncio
    async def test_day_210_generates_backup_zip_with_magic_link(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        started = datetime.now(timezone.utc) - timedelta(days=215)
        await svc.start_grace_period(
            db, project_id, started_at=started,
        )
        result = await process_grace_period_checkpoints(db)
        assert str(project_id) in result["backup_generated"]

        # Verificar que se creo un archived_backup
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            rows = (await db.execute(
                select(ProjectArchivedBackup).where(
                    ProjectArchivedBackup.project_id == project_id,
                )
            )).scalars().all()
            assert len(rows) == 1
            backup = rows[0]
            assert backup.expires_at > datetime.now(timezone.utc)
            assert len(backup.sha256_hash) == 64
            assert backup.ed25519_signature
        finally:
            await db.execute(sa_text("RESET ROLE"))

    @pytest.mark.asyncio
    async def test_day_240_deletes_project_data(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        started = datetime.now(timezone.utc) - timedelta(days=245)
        await svc.start_grace_period(
            db, project_id, started_at=started,
        )
        # Backup tiene que existir previo al delete en el mismo run
        result = await process_grace_period_checkpoints(db)
        # Re-run para disparar delete (idempotencia tras backup)
        result2 = await process_grace_period_checkpoints(db)

        # Al menos uno de los dos runs debe haber borrado
        deleted_any = (
            str(project_id) in result["data_deleted"]
            or str(project_id) in result2["data_deleted"]
        )
        assert deleted_any

        project = (await db.execute(
            select(Project).where(Project.id == project_id),
        )).scalar_one()
        assert project.lifecycle_state == "PURGED"
        assert project.deleted_at is not None

    @pytest.mark.asyncio
    async def test_checkpoints_idempotent_no_duplicates(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        started = datetime.now(timezone.utc) - timedelta(days=160)
        await svc.start_grace_period(db, project_id, started_at=started)

        # Dos runs consecutivos
        await process_grace_period_checkpoints(db)
        await process_grace_period_checkpoints(db)

        events = await svc.get_lifecycle_events(db, project_id)
        warning_count = sum(1 for e in events if e.event_type == "warning_sent")
        assert warning_count == 1  # solo UNA vez


# ══════════════════════════════════════════════════════════════════════
# Backup ZIP contenido + firma
# ══════════════════════════════════════════════════════════════════════


class TestBackupZipAndSignature:
    @pytest.mark.asyncio
    async def test_zip_contains_expected_sections(self, db):
        client_id, project_id = await _setup_project_with_tenant(
            db, certified=True,
        )
        # Insertar factura, documento, evidencia de prueba
        async with _admin_setup(db):
            await db.execute(sa_text(
                "INSERT INTO invoices (id, client_id, project_id, "
                "numero_correlativo, tipo, total, fecha_emision, created_at) "
                "VALUES (gen_random_uuid(), :cid, :pid, '2026-001', "
                "'service', 1000, CURRENT_DATE, now())"
            ), {"cid": str(client_id), "pid": str(project_id)})

        client = (await db.execute(
            select(Client).where(Client.id == client_id),
        )).scalar_one()
        project = (await db.execute(
            select(Project).where(Project.id == project_id),
        )).scalar_one()

        result = await build_and_sign_backup_zip(db, project, client)
        assert result["sha256"]
        assert result["signature"]
        assert result["public_key_pem"].startswith("-----BEGIN PUBLIC KEY-----")
        # Unzip en memoria y verificar paths
        import io, zipfile
        zf = zipfile.ZipFile(io.BytesIO(result["zip_bytes"]))
        names = zf.namelist()
        assert "README_LEGAL.md" in names
        assert "manifest.json" in names
        assert any(n.startswith("facturas/") for n in names)

    @pytest.mark.asyncio
    async def test_ed25519_signature_verifiable_externally(self, db):
        client_id, project_id = await _setup_project_with_tenant(
            db, certified=True,
        )
        client = (await db.execute(
            select(Client).where(Client.id == client_id),
        )).scalar_one()
        project = (await db.execute(
            select(Project).where(Project.id == project_id),
        )).scalar_one()
        result = await build_and_sign_backup_zip(db, project, client)

        # Extraer manifest del ZIP
        import io, json, zipfile
        zf = zipfile.ZipFile(io.BytesIO(result["zip_bytes"]))
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert verify_backup_signature(manifest) is True

        # Tampering detection: cambiar signed_digest deberia fallar
        tampered = dict(manifest)
        tampered["signed_digest_sha256"] = "00" * 32
        assert verify_backup_signature(tampered) is False

    @pytest.mark.asyncio
    async def test_sha256_hash_matches_zip_bytes(self, db):
        client_id, project_id = await _setup_project_with_tenant(
            db, certified=True,
        )
        client = (await db.execute(
            select(Client).where(Client.id == client_id),
        )).scalar_one()
        project = (await db.execute(
            select(Project).where(Project.id == project_id),
        )).scalar_one()
        result = await build_and_sign_backup_zip(db, project, client)
        import hashlib
        assert hashlib.sha256(result["zip_bytes"]).hexdigest() == result["sha256"]

    @pytest.mark.asyncio
    async def test_backup_generate_creates_archived_row_with_60d_ttl(self, db):
        client_id, project_id = await _setup_project_with_tenant(
            db, certified=True,
        )
        svc = LifecyclePaso4Service()
        backup = await svc.generate_project_backup_zip(
            db, project_id,
            recipient_email="rseg@test.es",
            send_magic_link=True,
        )
        assert backup.zip_size_bytes > 0
        assert backup.expires_at > datetime.now(timezone.utc)
        ttl_days = (backup.expires_at - backup.generated_at).days
        assert BACKUP_DOWNLOAD_TTL_DAYS - 1 <= ttl_days <= BACKUP_DOWNLOAD_TTL_DAYS


# ══════════════════════════════════════════════════════════════════════
# Delete + GDPR
# ══════════════════════════════════════════════════════════════════════


class TestDeleteProjectData:
    @pytest.mark.asyncio
    async def test_delete_before_grace_end_rejected(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        await svc.start_grace_period(db, project_id, days=240)
        with pytest.raises(LifecyclePaso4Error, match="aun no finalizado"):
            await svc.delete_project_data(db, project_id)

    @pytest.mark.asyncio
    async def test_delete_after_grace_end_succeeds(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        started = datetime.now(timezone.utc) - timedelta(days=250)
        await svc.start_grace_period(db, project_id, started_at=started)

        event = await svc.delete_project_data(db, project_id)
        assert event.event_type == "data_deleted"
        project = (await db.execute(
            select(Project).where(Project.id == project_id),
        )).scalar_one()
        assert project.lifecycle_state == "PURGED"
        assert project.deleted_at is not None

    @pytest.mark.asyncio
    async def test_delete_retains_audit_log_and_backups(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        started = datetime.now(timezone.utc) - timedelta(days=215)
        await svc.start_grace_period(db, project_id, started_at=started)
        backup = await svc.generate_project_backup_zip(
            db, project_id, recipient_email="rseg@test.es",
        )
        backup_id = backup.id

        # Fuerza delete (segundo gate: confirm_project_name exacto)
        await svc.delete_project_data(
            db, project_id, force=True, confirm_project_name="Test Project",
        )

        # Backup sigue existiendo
        retained = await get_archived_backup(db, backup_id)
        assert retained is not None
        assert retained.deleted_at is None

        # Eventos se retienen
        events = await svc.get_lifecycle_events(db, project_id)
        assert any(e.event_type == "backup_generated" for e in events)
        assert any(e.event_type == "data_deleted" for e in events)

    @pytest.mark.asyncio
    async def test_delete_wipes_personal_data_gdpr(self, db):
        client_id, project_id = await _setup_project_with_tenant(
            db, certified=True,
        )
        async with _admin_setup(db):
            await db.execute(sa_text(
                "INSERT INTO documents (id, project_id, tipo, nombre, "
                "full_text_content, storage_path, content_hash, created_at) "
                "VALUES (gen_random_uuid(), :pid, 'pol', 'Test Doc', "
                "'personal data here', 'minio://docs/xyz', 'hashhash', now())"
            ), {"pid": str(project_id)})

        svc = LifecyclePaso4Service()
        await svc.delete_project_data(
            db, project_id, force=True, confirm_project_name="Test Project",
        )

        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            row = (await db.execute(sa_text(
                "SELECT full_text_content, storage_path, content_hash "
                "FROM documents WHERE project_id = :pid"
            ), {"pid": str(project_id)})).first()
            assert row.full_text_content is None
            assert row.storage_path is None
            assert row.content_hash is None
        finally:
            await db.execute(sa_text("RESET ROLE"))

    @pytest.mark.asyncio
    async def test_force_delete_requires_confirm_project_name(self, db):
        """Segundo gate destructivo: force=True sin confirm_project_name
        correcto debe rechazarse (WAVE C1 · §4.1/339)."""
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()

        # 1) force sin confirm -> rechazado
        with pytest.raises(LifecyclePaso4Error, match="confirm_project_name"):
            await svc.delete_project_data(db, project_id, force=True)

        # 2) force con nombre erróneo -> rechazado
        with pytest.raises(LifecyclePaso4Error, match="confirm_project_name"):
            await svc.delete_project_data(
                db, project_id, force=True,
                confirm_project_name="Nombre Incorrecto",
            )

        # Proyecto intacto (no borrado)
        project = (await db.execute(
            select(Project).where(Project.id == project_id),
        )).scalar_one()
        assert project.deleted_at is None
        assert project.lifecycle_state != "PURGED"

        # 3) force con nombre exacto -> procede
        event = await svc.delete_project_data(
            db, project_id, force=True, confirm_project_name="Test Project",
        )
        assert event.event_type == "data_deleted"


# ══════════════════════════════════════════════════════════════════════
# Reactivation
# ══════════════════════════════════════════════════════════════════════


class TestReactivation:
    @pytest.mark.asyncio
    async def test_reactivation_within_60d_restores_project(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        backup = await svc.generate_project_backup_zip(
            db, project_id, recipient_email="rseg@test.es",
        )
        result = await svc.reactivate_project(
            db, archived_backup_id=backup.id,
            new_project_name="Proyecto Reactivado Test",
        )
        assert "new_project_id" in result
        new_project = (await db.execute(sa_text(
            "SELECT nombre, lifecycle_state, deleted_at FROM projects "
            "WHERE id = :pid"
        ), {"pid": result["new_project_id"]})).first()
        assert new_project.nombre == "Proyecto Reactivado Test"
        assert new_project.lifecycle_state == "ACTIVE"

    @pytest.mark.asyncio
    async def test_reactivation_after_backup_expires_fails(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        backup = await svc.generate_project_backup_zip(
            db, project_id, recipient_email="rseg@test.es",
        )
        # Forzar expiracion
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            await db.execute(sa_text(
                "UPDATE project_archived_backups "
                "SET expires_at = now() - interval '1 day' "
                "WHERE id = :bid"
            ), {"bid": str(backup.id)})
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))
        # Invalidar cache ORM para que el service lea datos frescos
        await db.refresh(backup)

        with pytest.raises(LifecyclePaso4Error, match="expiro"):
            await svc.reactivate_project(db, archived_backup_id=backup.id)

    @pytest.mark.asyncio
    async def test_reactivation_after_backup_deleted_fails(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        backup = await svc.generate_project_backup_zip(
            db, project_id, recipient_email="rseg@test.es",
        )
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            await db.execute(sa_text(
                "UPDATE project_archived_backups SET deleted_at = now() "
                "WHERE id = :bid"
            ), {"bid": str(backup.id)})
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))
        await db.refresh(backup)

        with pytest.raises(LifecyclePaso4Error, match="eliminado"):
            await svc.reactivate_project(db, archived_backup_id=backup.id)


# ══════════════════════════════════════════════════════════════════════
# Backup expirations (Celery task)
# ══════════════════════════════════════════════════════════════════════


class TestBackupExpirations:
    @pytest.mark.asyncio
    async def test_expire_old_backups_marks_deleted(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        backup = await svc.generate_project_backup_zip(
            db, project_id, recipient_email="rseg@test.es",
        )
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            await db.execute(sa_text(
                "UPDATE project_archived_backups "
                "SET expires_at = now() - interval '1 hour' "
                "WHERE id = :bid"
            ), {"bid": str(backup.id)})
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))
        await db.refresh(backup)

        result = await process_backup_expirations(db)
        assert str(backup.id) in result["deleted_ids"]

        await db.refresh(backup)
        retained = await get_archived_backup(db, backup.id)
        assert retained.deleted_at is not None


# ══════════════════════════════════════════════════════════════════════
# Lifecycle events trail + beat schedule
# ══════════════════════════════════════════════════════════════════════


class TestEventsAndScheduler:
    @pytest.mark.asyncio
    async def test_lifecycle_events_complete_trail(self, db):
        _, project_id = await _setup_project_with_tenant(db)
        svc = LifecyclePaso4Service()
        await svc.mark_certified(db, project_id)
        await svc.offer_retainer(
            db, project_id, recipient_email="rseg@test.es",
        )
        await svc.handle_retainer_decision(
            db, project_id, decision="decline",
        )
        events = await svc.get_lifecycle_events(db, project_id)
        kinds = [e.event_type for e in events]
        assert kinds == [
            "certified", "retainer_offered",
            "retainer_declined", "grace_period_started",
        ]

    def test_celery_beat_has_paso4_tasks(self):
        schedule = get_beat_schedule()
        assert "lifecycle-grace-period-check" in schedule
        assert "lifecycle-backup-expiration-check" in schedule

    @pytest.mark.asyncio
    async def test_marcos_can_force_backup_anytime(self, db):
        _, project_id = await _setup_project_with_tenant(db, certified=True)
        svc = LifecyclePaso4Service()
        # Sin grace period iniciado: Marcos puede generar
        backup = await svc.generate_project_backup_zip(
            db, project_id, send_magic_link=False,
        )
        assert backup is not None
