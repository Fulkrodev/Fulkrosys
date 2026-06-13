"""Tests del motor de remediación (DB + FakeWriter) · m_remediation (ADR-055).

Cubre el ciclo seguro completo sin tocar cloud real:
  - SAFE_AUTO full cycle → SUCCEEDED (apply + verify + snapshot + audit)
  - idempotente (ya cumple) → SKIPPED_COMPLIANT (no aplica)
  - verify falla → ROLLED_BACK · apply lanza → ROLLED_BACK · rollback lanza → FAILED
  - GUARDED requiere autorización previa
  - BLOCKED nunca ejecuta
  - kill-switch global/conector · writer no configurado · blast-radius · dry-run
  - audit_log R6 emitido · idempotencia sobre estados terminales
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_cloud_connectors.models import (
    CloudConnector,
    CloudConnectorProvider,
    CloudConnectorStatus,
)
from backend.app.motors.m_remediation.models import RemediationJobStatus
from backend.app.motors.m_remediation.service import (
    AuthorizationRequiredError,
    RemediationDisabledError,
    RemediationService,
)
from backend.app.motors.m_remediation.writers import WriterError
from backend.tests.conftest import _admin_setup, setup_test_project


# ─────────────────────────────────────────────────────────────────────────
# FakeWriter · simula el sistema real (sin cloud)


class FakeWriter:
    """Writer de test · configurable para forzar cada rama del ciclo."""

    def __init__(
        self,
        *,
        provider: str = "aws",
        assertion_key: str = "encryption_enabled",
        initial_compliant: bool = False,
        apply_makes_compliant: bool = True,
        raise_on_apply: bool = False,
        raise_on_rollback: bool = False,
    ) -> None:
        self.provider = provider
        self.assertion_key = assertion_key
        self._compliant = initial_compliant
        self.apply_makes_compliant = apply_makes_compliant
        self.raise_on_apply = raise_on_apply
        self.raise_on_rollback = raise_on_rollback
        self.calls: list[str] = []

    async def read_state(
        self, action_type: str, target_ref: str | None, params: dict[str, Any] | None,
    ) -> dict[str, Any]:
        self.calls.append("read")
        return {self.assertion_key: self._compliant, "target": target_ref}

    async def apply(
        self, action_type: str, target_ref: str | None, params: dict[str, Any] | None,
    ) -> dict[str, Any]:
        self.calls.append("apply")
        if self.raise_on_apply:
            raise WriterError("boom apply")
        if self.apply_makes_compliant:
            self._compliant = True
        return {"applied": True}

    async def rollback(
        self, action_type: str, target_ref: str | None, state_before: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append("rollback")
        if self.raise_on_rollback:
            raise WriterError("boom rollback")
        self._compliant = bool(state_before.get(self.assertion_key, False))
        return {"rolled_back": True}


# ─────────────────────────────────────────────────────────────────────────
# Helpers


async def _create_connector(
    db: AsyncSession,
    project_uuid: uuid.UUID,
    *,
    remediation_enabled: bool = True,
    policy: str = "full",
) -> CloudConnector:
    async with _admin_setup(db):
        connector = CloudConnector(
            project_id=project_uuid,
            provider=CloudConnectorProvider.AWS.value,
            status=CloudConnectorStatus.CONNECTED.value,
            remediation_enabled=remediation_enabled,
            auto_remediation_policy=policy,
        )
        db.add(connector)
        await db.flush()
    return connector


async def _audit_count(db: AsyncSession, job_id: uuid.UUID) -> int:
    row = await db.execute(
        text(
            "SELECT count(*) FROM audit_log WHERE tabla='remediation_jobs' "
            "AND registro_id = :rid"
        ),
        {"rid": str(job_id)},
    )
    return int(row.scalar() or 0)


@pytest.fixture(autouse=True)
def _global_on(monkeypatch: pytest.MonkeyPatch):
    """Por defecto el kill-switch global está ON en estos tests (salvo override)."""
    monkeypatch.setenv("FULKRO_REMEDIATION_ENABLED", "true")


# ─────────────────────────────────────────────────────────────────────────
# SAFE_AUTO


@pytest.mark.asyncio
async def test_safe_auto_full_cycle_success(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid)
    svc = RemediationService(db)

    job = await svc.create_job(
        project_id=project_uuid,
        action_type="enable_bucket_encryption",
        source_kind="cloud_gap",
        connector_id=connector.id,
        target_ref="arn:aws:s3:::demo",
    )
    assert job.status == RemediationJobStatus.QUEUED.value
    assert job.tier == "safe_auto"

    writer = FakeWriter(assertion_key="encryption_enabled", initial_compliant=False)
    job = await svc.execute_job(job.id, writer=writer)

    assert job.status == RemediationJobStatus.SUCCEEDED.value
    assert job.result["verified"] is True
    assert writer.calls == ["read", "apply", "read"]  # preflight, apply, verify
    assert job.started_at is not None and job.finished_at is not None
    assert await _audit_count(db, job.id) >= 4  # created+preflight+...+succeeded


@pytest.mark.asyncio
async def test_idempotent_skip_when_already_compliant(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid)
    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="enable_bucket_encryption",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="arn:demo",
    )
    writer = FakeWriter(assertion_key="encryption_enabled", initial_compliant=True)
    job = await svc.execute_job(job.id, writer=writer)

    assert job.status == RemediationJobStatus.SKIPPED_COMPLIANT.value
    assert "apply" not in writer.calls  # no aplicó nada (idempotente)
    assert job.result["idempotent"] is True


@pytest.mark.asyncio
async def test_verify_fail_triggers_rollback(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid)
    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="enable_bucket_encryption",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="arn:demo",
    )
    # apply NO deja el recurso conforme → verify falla → rollback.
    writer = FakeWriter(
        assertion_key="encryption_enabled",
        initial_compliant=False,
        apply_makes_compliant=False,
    )
    job = await svc.execute_job(job.id, writer=writer)

    assert job.status == RemediationJobStatus.ROLLED_BACK.value
    assert "rollback" in writer.calls
    assert job.result["rolled_back"] is True


@pytest.mark.asyncio
async def test_apply_error_triggers_rollback(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid)
    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="enable_bucket_encryption",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="arn:demo",
    )
    writer = FakeWriter(assertion_key="encryption_enabled", raise_on_apply=True)
    job = await svc.execute_job(job.id, writer=writer)

    assert job.status == RemediationJobStatus.ROLLED_BACK.value
    assert "rollback" in writer.calls
    assert "Apply falló" in (job.error_message or "")


@pytest.mark.asyncio
async def test_rollback_error_results_failed(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid)
    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="enable_bucket_encryption",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="arn:demo",
    )
    writer = FakeWriter(
        assertion_key="encryption_enabled",
        raise_on_apply=True,
        raise_on_rollback=True,
    )
    job = await svc.execute_job(job.id, writer=writer)

    assert job.status == RemediationJobStatus.FAILED.value
    assert "rollback falló" in (job.error_message or "")


# ─────────────────────────────────────────────────────────────────────────
# GUARDED


@pytest.mark.asyncio
async def test_guarded_requires_authorization(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid, policy="full")
    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="require_mfa_enforce",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="tenant-1",
    )
    assert job.status == RemediationJobStatus.AWAITING_AUTHORIZATION.value
    assert job.tier == "guarded"

    writer = FakeWriter(provider="microsoft_365", assertion_key="mfa_enforced")
    with pytest.raises(AuthorizationRequiredError):
        await svc.execute_job(job.id, writer=writer)

    # Autorizar previamente → ahora ejecuta.
    job = await svc.authorize_job(job.id, user_id=uuid.uuid4())
    assert job.status == RemediationJobStatus.QUEUED.value
    assert job.authorized_at is not None

    job = await svc.execute_job(job.id, writer=writer)
    assert job.status == RemediationJobStatus.SUCCEEDED.value


# ─────────────────────────────────────────────────────────────────────────
# BLOCKED


@pytest.mark.asyncio
async def test_blocked_never_executes(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid)
    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="delete_public_resource",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="arn:demo",
    )
    assert job.status == RemediationJobStatus.BLOCKED.value

    writer = FakeWriter(assertion_key="resource_absent")
    job = await svc.execute_job(job.id, writer=writer)
    assert job.status == RemediationJobStatus.BLOCKED.value
    assert writer.calls == []  # jamás tocó el recurso


# ─────────────────────────────────────────────────────────────────────────
# Kill-switch


@pytest.mark.asyncio
async def test_killswitch_global_off_blocks_execution(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FULKRO_REMEDIATION_ENABLED", raising=False)
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid)
    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="enable_bucket_encryption",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="arn:demo",
    )
    writer = FakeWriter(assertion_key="encryption_enabled")
    with pytest.raises(RemediationDisabledError):
        await svc.execute_job(job.id, writer=writer)
    assert writer.calls == []


@pytest.mark.asyncio
async def test_connector_disabled_blocks(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid, remediation_enabled=False)
    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="enable_bucket_encryption",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="arn:demo",
    )
    writer = FakeWriter(assertion_key="encryption_enabled")
    with pytest.raises(RemediationDisabledError):
        await svc.execute_job(job.id, writer=writer)


# ─────────────────────────────────────────────────────────────────────────
# Writer no configurado · blast-radius · dry-run · idempotencia terminal


@pytest.mark.asyncio
async def test_writer_not_configured_fails(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid)
    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="enable_bucket_encryption",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="arn:demo",
    )
    # Sin writer override y sin registro real → FAILED explícito (default seguro).
    job = await svc.execute_job(job.id)
    assert job.status == RemediationJobStatus.FAILED.value
    assert "writer" in (job.error_message or "").lower()


@pytest.mark.asyncio
async def test_blast_radius_guard(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid)
    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="enable_bucket_encryption",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="arn:demo",
        params={"affected_count": 5},  # > blast_radius_max=1
    )
    writer = FakeWriter(assertion_key="encryption_enabled")
    job = await svc.execute_job(job.id, writer=writer)
    assert job.status == RemediationJobStatus.FAILED.value
    assert "blast radius" in (job.error_message or "").lower()
    assert writer.calls == []  # ni preflight


@pytest.mark.asyncio
async def test_dry_run_no_apply(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid)
    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="enable_bucket_encryption",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="arn:demo",
        dry_run=True,
    )
    writer = FakeWriter(assertion_key="encryption_enabled", initial_compliant=False)
    job = await svc.execute_job(job.id, writer=writer)
    assert job.status == RemediationJobStatus.SUCCEEDED.value
    assert job.result["dry_run"] is True
    assert "apply" not in writer.calls  # ensayo · no aplica


@pytest.mark.asyncio
async def test_execute_idempotent_on_terminal(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid)
    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="enable_bucket_encryption",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="arn:demo",
    )
    writer = FakeWriter(assertion_key="encryption_enabled")
    job = await svc.execute_job(job.id, writer=writer)
    assert job.status == RemediationJobStatus.SUCCEEDED.value
    calls_after_first = list(writer.calls)
    # Re-ejecutar un job terminal NO repite el ciclo.
    job = await svc.execute_job(job.id, writer=writer)
    assert job.status == RemediationJobStatus.SUCCEEDED.value
    assert writer.calls == calls_after_first
