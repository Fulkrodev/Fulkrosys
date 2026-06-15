"""P7-F1 · workflow_gates huérfanos cableados en sus motores.

Pasada 7 §2.2 detectó 4 de 6 gates definidos pero SIN call site. Los gates en
sí ya se testean en ``test_workflow_gates.py`` (raise cuando falta el
prerequisito). Aquí verificamos el WIRING: que los métodos de servicio invocan
realmente el gate (raise antes de mutar estado) y que ``enforce_gates=False``
lo desactiva.

Batch 2 cubre H3 (M05 obligaciones ← MAGERIT) + H4 (M09 audit-prep ← evidencia).
Cada test reactiva ``FULKRO_SKIP_WORKFLOW_GATES=0`` vía monkeypatch (mismo
patrón que test_workflow_gates.py).

Fuente: docs/audits/EJECUTABLE_8_PASADA_7_COHERENCE_SYSTEMIC.md §2.2 + P7-F1.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.workflow_gates import WorkflowGateError


@pytest.fixture
def gates_enforced(monkeypatch):
    monkeypatch.setenv("FULKRO_SKIP_WORKFLOW_GATES", "0")
    yield


# ════════════════════════════════════════════════════════════════════
# H3 · M05 obligaciones gateado por require_magerit_analysis
# ════════════════════════════════════════════════════════════════════


def _project_context(project_id: uuid.UUID):
    from backend.app.motors.m05_obligations.instantiation_types import (
        ClientContext,
        ProjectContext,
    )

    return ProjectContext(
        project_id=project_id,
        nombre_proyecto="Proyecto Test",
        categoria_ens="MEDIA",
        cliente=ClientContext(razon_social="ACME SL"),
    )


@pytest.mark.asyncio
async def test_instantiate_obligations_gated_on_magerit(
    db: AsyncSession, gates_enforced,
) -> None:
    """Sin análisis MAGERIT para el proyecto → el servicio M05 levanta el
    gate antes de instanciar obligaciones."""
    from backend.app.motors.m05_obligations.instantiation_service import (
        instantiate_obligations_for_multiple_gaps,
    )

    with pytest.raises(WorkflowGateError) as ei:
        await instantiate_obligations_for_multiple_gaps(
            db, gaps=[], project_context=_project_context(uuid.uuid4()),
        )
    assert ei.value.gate == "magerit_analysis"


@pytest.mark.asyncio
async def test_instantiate_obligations_bypass_when_enforce_gates_false(
    db: AsyncSession, gates_enforced,
) -> None:
    """enforce_gates=False salta el gate incluso sin MAGERIT (gaps vacíos →
    no toca tablas ausentes → retorna [])."""
    from backend.app.motors.m05_obligations.instantiation_service import (
        instantiate_obligations_for_multiple_gaps,
    )

    outcomes = await instantiate_obligations_for_multiple_gaps(
        db, gaps=[], project_context=_project_context(uuid.uuid4()),
        enforce_gates=False,
    )
    assert outcomes == []


# ════════════════════════════════════════════════════════════════════
# H4 · M09 audit-prep gateado por require_some_evidence
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_run_full_checklist_gated_on_evidence(
    db: AsyncSession, gates_enforced,
) -> None:
    """Sin evidencia subida → el orquestador M09 levanta el gate antes de
    crear el run de preparación."""
    from backend.app.motors.m09_audit_prep import checklist_service

    with pytest.raises(WorkflowGateError) as ei:
        await checklist_service.run_full_checklist(
            db, uuid.uuid4(), "MEDIA",
        )
    assert ei.value.gate == "require_some_evidence"


# ════════════════════════════════════════════════════════════════════
# H5 · M25 lifecycle transition → CERTIFIED gateado por audit-prep completo
# ════════════════════════════════════════════════════════════════════


async def _project_active(db: AsyncSession) -> uuid.UUID:
    """Crea proyecto + tenant context y lo avanza hasta ACTIVE (transiciones
    intermedias NO son CERTIFIED → el gate H5 no dispara)."""
    from backend.app.database import set_tenant_context
    from backend.app.motors.m25_lifecycle.lifecycle_service import LifecycleService
    from backend.tests.conftest import setup_test_project

    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    pid = uuid.UUID(project_id)
    svc = LifecycleService()
    for state in ("NEGOTIATING", "SIGNED", "ACTIVE"):
        await svc.transition(db, pid, to_state=state)
    return pid


@pytest.mark.asyncio
async def test_transition_to_certified_gated_on_audit_prep(
    db: AsyncSession, gates_enforced,
) -> None:
    """ACTIVE → CERTIFIED sin dossier M9 completo → el servicio levanta el gate."""
    from backend.app.motors.m25_lifecycle.lifecycle_service import LifecycleService

    pid = await _project_active(db)
    with pytest.raises(WorkflowGateError) as ei:
        await LifecycleService().transition(db, pid, to_state="CERTIFIED")
    assert ei.value.gate == "complete_audit_prep"


@pytest.mark.asyncio
async def test_transition_to_certified_bypass_enforce_gates_false(
    db: AsyncSession, gates_enforced,
) -> None:
    """enforce_gates=False permite CERTIFIED sin dossier (escape hatch)."""
    from backend.app.motors.m25_lifecycle.lifecycle_service import LifecycleService

    pid = await _project_active(db)
    event = await LifecycleService().transition(
        db, pid, to_state="CERTIFIED", enforce_gates=False,
    )
    assert event.state == "CERTIFIED"


@pytest.mark.asyncio
async def test_transition_to_ended_churn_not_gated(
    db: AsyncSession, gates_enforced,
) -> None:
    """ACTIVE → ENDED_CHURN (abandono) NO exige dossier · sólo CERTIFIED se gatea."""
    from backend.app.motors.m25_lifecycle.lifecycle_service import LifecycleService

    pid = await _project_active(db)
    event = await LifecycleService().transition(db, pid, to_state="ENDED_CHURN")
    assert event.state == "ENDED_CHURN"


# ════════════════════════════════════════════════════════════════════
# H6 · M08 create_run external gateado por autorización pentest cliente
# ════════════════════════════════════════════════════════════════════


async def _project_with_tenant(db: AsyncSession) -> uuid.UUID:
    from backend.app.database import set_tenant_context
    from backend.tests.conftest import setup_test_project

    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    return uuid.UUID(project_id)


@pytest.mark.asyncio
async def test_create_run_external_gated_on_pentest_auth(
    db: AsyncSession, gates_enforced,
) -> None:
    """Run mode='external_handoff' sin autorización cliente (magic-link) → gate H6.

    Nota: antes este test usaba mode="external", un valor que NO existe en
    VALID_MODES (internal|external_handoff|external_ingest_pdf|external_ingest_form);
    el gate de servicio comparaba con ese literal muerto, así que NUNCA se disparaba
    para los runs externos reales. Ahora valida el modo real que toca infra.
    """
    from backend.app.motors.m08_verification.service import VerificationService

    pid = await _project_with_tenant(db)
    with pytest.raises(WorkflowGateError) as ei:
        await VerificationService(db).create_run(
            pid, "BASICO", mode="external_handoff")
    assert ei.value.gate == "pentest_authorisation"


@pytest.mark.asyncio
async def test_create_run_internal_not_gated(
    db: AsyncSession, gates_enforced,
) -> None:
    """Run mode='internal' (self-scan Fulkro) NO requiere autorización · ADR-014."""
    from backend.app.motors.m08_verification.service import VerificationService

    pid = await _project_with_tenant(db)
    run = await VerificationService(db).create_run(pid, "BASICO", mode="internal")
    assert run.mode == "internal"
