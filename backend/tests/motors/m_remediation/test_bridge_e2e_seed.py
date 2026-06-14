"""FASE 7 · Seed E2E del flujo pentest/diagnóstico → remediación → dossier.

Prueba con seeds (sin cloud real · FakeWriter) la cadena completa que pidió el
cliente para MEDIA y ALTA:
  CloudGap (hallazgo) → propose_remediations_for_project (puente · job PROPUESTO)
  → approve_and_execute_job (1 clic · autoriza si GUARDED + ejecuta ciclo seguro)
  → _collect_remediations (la remediación queda documentada para el dossier 14).
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
    CloudGap,
)
from backend.app.motors.m_remediation.bridge import (
    propose_remediations_for_project,
)
from backend.app.motors.m_remediation.models import RemediationJobStatus
from backend.app.motors.m_remediation.service import RemediationService
from backend.app.motors.m_remediation.writers import WriterError
from backend.app.motors.m09_audit_prep.dossier_generator import (
    _collect_remediations,
)
from backend.tests.conftest import _admin_setup, setup_test_project


class _FakeWriter:
    def __init__(self, assertion_key: str) -> None:
        self.assertion_key = assertion_key
        self._compliant = False
        self.calls: list[str] = []

    async def read_state(self, action_type, target_ref, params) -> dict[str, Any]:
        self.calls.append("read")
        return {self.assertion_key: self._compliant, "target": target_ref}

    async def apply(self, action_type, target_ref, params) -> dict[str, Any]:
        self.calls.append("apply")
        self._compliant = True
        return {"applied": True}

    async def rollback(self, action_type, target_ref, state_before) -> dict[str, Any]:
        self.calls.append("rollback")
        if False:  # nunca falla en este seed
            raise WriterError("x")
        return {"rolled_back": True}


@pytest.fixture(autouse=True)
def _global_on(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FULKRO_REMEDIATION_ENABLED", "true")


async def _connector(db: AsyncSession, project_uuid: uuid.UUID) -> CloudConnector:
    async with _admin_setup(db):
        c = CloudConnector(
            project_id=project_uuid,
            provider=CloudConnectorProvider.AWS.value,
            status=CloudConnectorStatus.CONNECTED.value,
            remediation_enabled=True,
            auto_remediation_policy="full",
        )
        db.add(c)
        await db.flush()
    return c


async def _seed_gap(
    db: AsyncSession,
    project_uuid: uuid.UUID,
    connector_id: uuid.UUID,
    *,
    ens_measure_code: str = "mp.si.2",
    resource_type: str = "storage_bucket",
) -> CloudGap:
    async with _admin_setup(db):
        gap = CloudGap(
            project_id=project_uuid,
            connector_id=connector_id,
            gap_type="configuration",
            severity="high",
            ens_measure_code=ens_measure_code,
            title="Bucket sin cifrado en reposo",
            suggested_action="Activar cifrado",
            raw_evidence={
                "resource_type": resource_type,
                "resource_external_id": "arn:aws:s3:::demo-bucket",
            },
        )
        db.add(gap)
        await db.flush()
    return gap


@pytest.mark.asyncio
async def test_e2e_gap_to_remediation_to_dossier_media(db: AsyncSession) -> None:
    """MEDIA · SAFE_AUTO vía puente: gap → propuesta → aprobar+ejecutar → dossier."""
    cid, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _connector(db, project_uuid)
    await _seed_gap(db, project_uuid, connector.id)

    await db.execute(
        text("SELECT set_config('app.current_project_id', :p, true)"), {"p": pid},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :c, true)"), {"c": cid},
    )

    # 1. Puente: el hallazgo cloud se convierte en un job PROPUESTO (no ejecuta).
    result = await propose_remediations_for_project(
        db, project_uuid, client_id=uuid.UUID(cid),
    )
    assert len(result["created"]) == 1, result
    created = result["created"][0]
    assert created["action_type"] == "enable_bucket_encryption"
    assert created["tier"] == "safe_auto"
    assert created["status"] == RemediationJobStatus.QUEUED.value
    job_id = uuid.UUID(created["job_id"])

    # 2. Idempotente: re-proponer NO duplica.
    again = await propose_remediations_for_project(db, project_uuid)
    assert len(again["created"]) == 0

    # 3. Aprobar+ejecutar con un clic (SAFE_AUTO · ciclo seguro con FakeWriter).
    svc = RemediationService(db)
    job = await svc.approve_and_execute_job(
        job_id, user_id=None, writer=_FakeWriter("encryption_enabled"),
    )
    assert job.status == RemediationJobStatus.SUCCEEDED.value

    # 4. La remediación queda documentada para el dossier (carpeta 14).
    remediations, md = await _collect_remediations(db, project_uuid)
    assert any(
        r["action_type"] == "enable_bucket_encryption"
        and r["estado"] == "succeeded"
        for r in remediations
    ), remediations
    assert "Informe de Remediaciones" in md


@pytest.mark.asyncio
async def test_e2e_guarded_one_click_authorize_and_execute(db: AsyncSession) -> None:
    """ALTA · GUARDED: un solo clic autoriza y ejecuta (proponer→aprobar→ejecutar)."""
    cid, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _connector(db, project_uuid)
    await db.execute(
        text("SELECT set_config('app.current_project_id', :p, true)"), {"p": pid},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :c, true)"), {"c": cid},
    )

    svc = RemediationService(db)
    # Acción GUARDED (rotar clave de acceso · op.acc.5) → requiere autorización.
    job = await svc.create_job(
        project_id=project_uuid,
        action_type="rotate_access_key",
        source_kind="cloud_gap",
        connector_id=connector.id,
        target_ref="iam-user-demo",
        client_id=uuid.UUID(cid),
    )
    assert job.status == RemediationJobStatus.AWAITING_AUTHORIZATION.value
    assert job.tier == "guarded"

    # Un clic: approve_and_execute autoriza Y ejecuta.
    job = await svc.approve_and_execute_job(
        job.id, user_id=None, writer=_FakeWriter("key_age_ok"),
    )
    assert job.status == RemediationJobStatus.SUCCEEDED.value
    assert job.authorized_at is not None
