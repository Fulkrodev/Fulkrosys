"""Sesión 3B-2B.8 Phase 1D · workflow_state_scanner pure functional tests.

Cubre:
  - Fresh project → current_phase=pre_venta · admin/cliente actions correctos
  - Phase derived via cascade fallback when persisted fase desactualizada
  - role_filter=cliente devuelve solo cliente actions
  - Phase progress orden canonical · before completed · current in_progress · after not_started
  - top_action_for_role respect priority urgent > normal > low
  - Blockers detected DdA pendiente firma cliente
  - Pure functional · sin side effects (no INSERT post-call)
  - ALTA category triggers pentest blocker
  - to_dict JSON-serializable
  - last_updated_at populated ISO format
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.workflow_phase import WorkflowPhase
from backend.app.motors.m11_copiloto.workflow_state_scanner import (
    ActionHint,
    WorkflowScannerOptions,
    WorkflowState,
    _detect_blockers,
    compute_workflow_state,
    top_action_for_role,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _set_project_phase(
    db: AsyncSession, project_uuid: uuid.UUID, phase: WorkflowPhase,
) -> None:
    """Update projects.fase bypassing tg_projects_phase_changed trigger.

    Pre-existing bug: trigger emits event_type='phase_changed' que NO está
    en ck_project_lifecycle_events_event_type allowed values (13 valores ·
    NO incluye 'phase_changed'). En producción funciona via otro path · en
    tests bypass via session_replication_role='replica' (superuser scope).
    """
    async with _admin_setup(db):
        await db.execute(text("SET LOCAL session_replication_role = 'replica'"))
        await db.execute(
            text("UPDATE projects SET fase = :p WHERE id = :pid"),
            {"p": phase.value, "pid": str(project_uuid)},
        )
        await db.execute(text("SET LOCAL session_replication_role = 'origin'"))


async def _set_project_categoria(
    db: AsyncSession, project_uuid: uuid.UUID, categoria: str,
) -> None:
    async with _admin_setup(db):
        await db.execute(
            text(
                "UPDATE projects SET categoria_objetivo = :c WHERE id = :pid"
            ),
            {"c": categoria, "pid": str(project_uuid)},
        )


# ════════════════════════════════════════════════════════════════════
# Phase 1 · current_phase + actions per fase
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fresh_project_pre_venta_admin_action_contract(
    db: AsyncSession,
) -> None:
    """Fresh project default pre_venta · Batch 2: gobierno FASE 0 precede.

    CAMBIO Batch 2 (Opción A · cablear FASE 0 gobierno): antes el top admin
    en PRE_VENTA era la genérica 'prepare_contract' (m14) y se asumía
    len(next_admin_actions)==1. Ahora, con gobierno inyectado en fases
    tempranas mientras fase0_completa=False, un proyecto fresco SIN docs de
    gobierno tiene como siguiente paso el kickoff de gobierno (m17 · urgent),
    que PRECEDE a la genérica. 'prepare_contract' NO se borra: queda como
    acción secundaria. Cliente sigue sin acciones (gobierno solo admin).
    """
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    state = await compute_workflow_state(db, project_uuid)

    assert state.current_phase == WorkflowPhase.PRE_VENTA.value
    # Gobierno FASE 0 precede (prepend urgent · m17).
    assert state.next_admin_actions[0].motor == "m17"
    assert state.next_admin_actions[0].action == "fase0_kickoff"
    assert state.next_admin_actions[0].priority == "urgent"
    # La genérica de fase queda como secundaria (NO se borra).
    assert any(
        a.motor == "m14" and a.action == "prepare_contract"
        for a in state.next_admin_actions
    )
    # Gobierno es solo admin · cliente sin acciones.
    assert state.next_cliente_actions == []


@pytest.mark.asyncio
async def test_implantacion_phase_cliente_sign_dda_urgent(
    db: AsyncSession,
) -> None:
    """Fase IMPLANTACION · cliente action sign_dda urgent."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _set_project_phase(db, project_uuid, WorkflowPhase.IMPLANTACION)

    state = await compute_workflow_state(db, project_uuid)

    assert state.current_phase == WorkflowPhase.IMPLANTACION.value
    cliente = state.next_cliente_actions
    assert any(a.action == "sign_dda" and a.priority == "urgent" for a in cliente)


@pytest.mark.asyncio
async def test_retainer_cierre_phase_cliente_friendly_message(
    db: AsyncSession,
) -> None:
    """Fase RETAINER_CIERRE · cliente recibe congrats tone R29 sostained."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _set_project_phase(db, project_uuid, WorkflowPhase.RETAINER_CIERRE)

    state = await compute_workflow_state(db, project_uuid)

    cliente = state.next_cliente_actions
    assert len(cliente) == 1
    assert "Felicidades" in cliente[0].description_cliente
    # R29 sostained · NO presión coercitiva
    assert "urgente" not in cliente[0].description_cliente.lower()


# ════════════════════════════════════════════════════════════════════
# Phase 2 · role_filter + phase_progress + URL interpolation
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_role_filter_cliente_excludes_admin_actions(
    db: AsyncSession,
) -> None:
    """role_filter=cliente devuelve next_admin_actions=[] · cliente actions populated."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _set_project_phase(db, project_uuid, WorkflowPhase.ADECUACION)

    state = await compute_workflow_state(
        db, project_uuid,
        options=WorkflowScannerOptions(role_filter="cliente"),
    )

    assert state.next_admin_actions == []
    assert len(state.next_cliente_actions) >= 1


@pytest.mark.asyncio
async def test_phase_progress_canonical_order(
    db: AsyncSession,
) -> None:
    """phase_progress respect WorkflowPhase.ordered() · before completed · current in_progress."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _set_project_phase(db, project_uuid, WorkflowPhase.IMPLANTACION)

    state = await compute_workflow_state(db, project_uuid)

    ordered = WorkflowPhase.ordered()
    assert len(state.phase_progress) == len(ordered)
    for i, pp in enumerate(state.phase_progress):
        assert pp.phase == ordered[i].value
        if ordered[i] == WorkflowPhase.IMPLANTACION:
            assert pp.status == "in_progress"
            assert pp.completion_percentage == 50
        elif i < ordered.index(WorkflowPhase.IMPLANTACION):
            assert pp.status == "completed"
            assert pp.completion_percentage == 100
        else:
            assert pp.status == "not_started"
            assert pp.completion_percentage == 0


@pytest.mark.asyncio
async def test_url_interpolation_project_id_substituted(
    db: AsyncSession,
) -> None:
    """target_url placeholder {project_id} sustituido empíricamente."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _set_project_phase(db, project_uuid, WorkflowPhase.ADECUACION)

    state = await compute_workflow_state(db, project_uuid)

    for action in state.next_admin_actions:
        assert "{project_id}" not in action.target_url
        if "/admin/projects/" in action.target_url:
            assert project_id_str in action.target_url


# ════════════════════════════════════════════════════════════════════
# Phase 3 · top_action_for_role helper + priority sorting
# ════════════════════════════════════════════════════════════════════


def test_top_action_for_role_picks_urgent_over_normal():
    """top_action_for_role respect priority urgent > normal > low."""
    state = WorkflowState(
        project_id=str(uuid.uuid4()),
        current_phase="adecuacion",
        phase_progress=[],
        next_admin_actions=[],
        next_cliente_actions=[
            ActionHint(
                motor="m01", action="review", description_cliente="x",
                description_admin="", priority="normal", target_url="/x",
            ),
            ActionHint(
                motor="m03", action="sign", description_cliente="y",
                description_admin="", priority="urgent", target_url="/y",
            ),
            ActionHint(
                motor="m07", action="upload", description_cliente="z",
                description_admin="", priority="low", target_url="/z",
            ),
        ],
        blockers=[],
        last_updated_at="2026-05-26T15:00:00Z",
    )

    top = top_action_for_role(state, "cliente")
    assert top is not None
    assert top.priority == "urgent"
    assert top.action == "sign"


def test_top_action_for_role_none_when_no_actions():
    state = WorkflowState(
        project_id=str(uuid.uuid4()),
        current_phase="conformidad",
        phase_progress=[],
        next_admin_actions=[],
        next_cliente_actions=[],
        blockers=[],
        last_updated_at="2026-05-26T15:00:00Z",
    )
    assert top_action_for_role(state, "cliente") is None
    assert top_action_for_role(state, "admin") is None


# ════════════════════════════════════════════════════════════════════
# Phase 4 · blockers detection
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_conformidad_blocker_external_auditor(
    db: AsyncSession,
) -> None:
    """Fase CONFORMIDAD siempre emit blocker external_auditor."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _set_project_phase(db, project_uuid, WorkflowPhase.CONFORMIDAD)

    state = await compute_workflow_state(db, project_uuid)

    assert any(b.waiting_on == "external_auditor" for b in state.blockers)


@pytest.mark.asyncio
async def test_alta_category_implantacion_pentest_blocker(
    db: AsyncSession,
) -> None:
    """ALTA + IMPLANTACION sin pentest_authorizations → blocker cliente."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _set_project_categoria(db, project_uuid, "alta")
    await _set_project_phase(db, project_uuid, WorkflowPhase.IMPLANTACION)

    state = await compute_workflow_state(db, project_uuid)

    pentest_blockers = [b for b in state.blockers if b.motor == "m08"]
    assert len(pentest_blockers) == 1
    assert pentest_blockers[0].waiting_on == "cliente"


# ════════════════════════════════════════════════════════════════════
# Phase 5 · pure functional + JSON-serializable
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pure_functional_no_side_effects(
    db: AsyncSession,
) -> None:
    """compute_workflow_state NO INSERT/UPDATE pre/post call."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        pre_audit = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM audit_log "
                    "WHERE project_id = :pid"
                ),
                {"pid": str(project_uuid)},
            )
        ).scalar()

    await compute_workflow_state(db, project_uuid)
    await compute_workflow_state(db, project_uuid)  # idempotente

    async with _admin_setup(db):
        post_audit = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM audit_log "
                    "WHERE project_id = :pid"
                ),
                {"pid": str(project_uuid)},
            )
        ).scalar()

    assert pre_audit == post_audit  # 0 audit_log INSERT post-call


@pytest.mark.asyncio
async def test_to_dict_json_serializable(
    db: AsyncSession,
) -> None:
    """asdict() output JSON-serializable cross consumer."""
    import json as _json

    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    state = await compute_workflow_state(db, project_uuid)
    serialized = _json.dumps(state.to_dict())
    parsed = _json.loads(serialized)

    assert parsed["project_id"] == project_id_str
    assert parsed["current_phase"] == WorkflowPhase.PRE_VENTA.value
    assert "next_admin_actions" in parsed
    assert "phase_progress" in parsed
    assert parsed["last_updated_at"].endswith("Z")


# ════════════════════════════════════════════════════════════════════
# Phase 6 · FASE 0 gobierno cableado al scanner (Batch 2 · Opción A)
# ════════════════════════════════════════════════════════════════════


async def _seed_governance_docs(
    db: AsyncSession, project_uuid: uuid.UUID, ecodes: list[str],
) -> None:
    """Siembra docs de gobierno (template_codigo) para mover fase0_completa.

    BASICA → 4 pasos: kickoff(any gov doc) · alcance(E-155) · roles(E-002) ·
    plan(E-150). Con los 3 ecodes presentes → fase0_completa=True.
    """
    async with _admin_setup(db):
        for ecode in ecodes:
            await db.execute(
                text(
                    "INSERT INTO documents "
                    "(id, project_id, nombre, template_codigo, "
                    " created_at, updated_at) "
                    "VALUES (gen_random_uuid(), :pid, :nombre, :ecode, "
                    " now(), now())"
                ),
                {"pid": str(project_uuid), "nombre": f"Doc {ecode}",
                 "ecode": ecode},
            )


@pytest.mark.asyncio
async def test_governance_complete_falls_back_to_generic(
    db: AsyncSession,
) -> None:
    """Gobierno completo (BASICA · E-155+E-002+E-150) → top = genérica.

    Con fase0_completa=True NO se inyecta gobierno; el top admin vuelve a ser
    la acción genérica de fase ('prepare_contract' en PRE_VENTA). Prueba la
    no-regresión del comportamiento previo cuando el gobierno ya está cerrado.
    """
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _seed_governance_docs(db, project_uuid, ["E-155", "E-002", "E-150"])

    state = await compute_workflow_state(db, project_uuid)

    assert state.current_phase == WorkflowPhase.PRE_VENTA.value
    assert not any(
        a.action.startswith("fase0_") for a in state.next_admin_actions
    )
    assert state.next_admin_actions[0].action == "prepare_contract"


@pytest.mark.asyncio
async def test_governance_solo_admin_cliente_never_sees_it(
    db: AsyncSession,
) -> None:
    """Gobierno es solo admin · role cliente NUNCA lo dispara/recibe.

    Guard de visibilidad (decisión Marcos): el cliente sigue viendo solo
    resultados (su guía), NUNCA el progreso de gobierno.
    """
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    state = await compute_workflow_state(
        db, project_uuid,
        options=WorkflowScannerOptions(role_filter="cliente"),
    )

    assert state.next_admin_actions == []
    assert all(a.motor != "m17" for a in state.next_cliente_actions)
    assert all(
        not a.action.startswith("fase0_") for a in state.next_cliente_actions
    )


@pytest.mark.asyncio
async def test_late_phase_no_governance_injection(
    db: AsyncSession,
) -> None:
    """Fase tardía (IMPLANTACION ∉ _FASE0_PHASES) → sin inyección de gobierno.

    El gobierno solo está vivo PRE_VENTA..ADECUACION. En IMPLANTACION los
    blockers existentes (DdA-firma) quedan intactos.
    """
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _set_project_phase(db, project_uuid, WorkflowPhase.IMPLANTACION)

    state = await compute_workflow_state(db, project_uuid)

    assert state.current_phase == WorkflowPhase.IMPLANTACION.value
    assert all(
        not a.action.startswith("fase0_") for a in state.next_admin_actions
    )


@pytest.mark.asyncio
async def test_governance_injection_lazy_import_works(
    db: AsyncSession,
) -> None:
    """Anti-circular smoke · proyecto fresco PRE_VENTA inyecta fase0_kickoff.

    Que aparezca la acción fase0_* demuestra que el import lazy de
    compute_fase0_governance_state (m17) resuelve sin ciclo en runtime.
    """
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    state = await compute_workflow_state(db, project_uuid)

    gov = [a for a in state.next_admin_actions if a.action.startswith("fase0_")]
    assert len(gov) == 1
    assert gov[0].motor == "m17"
    assert "{project_id}" not in gov[0].target_url
    assert project_id_str in gov[0].target_url  # kickoff → /onboarding scoped


@pytest.mark.asyncio
async def test_detect_blockers_governance_separacion_and_cadencia(
    db: AsyncSession,
) -> None:
    """Blockers de gobierno additive · default None no-op · branch nueva.

    Prueba directa de _detect_blockers (la integración exacta del Batch 2)
    en ADECUACION (no dispara los 3 blockers existentes), con dicts de
    gobierno sintéticos. La corrección del composer en sí la cubren los
    tests de m17 (test_fase0_governance.py · no se tocan).
    """
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    # default None → cero blockers de gobierno (no-op · consumidores actuales).
    none_blockers = await _detect_blockers(
        db, project_uuid, WorkflowPhase.ADECUACION, "media", None,
    )
    assert none_blockers == []

    # separación obligatoria no conforme → blocker m30.
    gov_sep = {"steps": [
        {"key": "roles", "separacion": {"obligatoria": True, "compliant": False}},
    ]}
    sep_blockers = await _detect_blockers(
        db, project_uuid, WorkflowPhase.ADECUACION, "media", gov_sep,
    )
    assert any(b.motor == "m30" and b.waiting_on == "admin" for b in sep_blockers)

    # separación NO obligatoria (BASICA) aunque no compliant → sin blocker m30.
    gov_basica = {"steps": [
        {"key": "roles", "separacion": {"obligatoria": False, "compliant": False}},
    ]}
    basica_blockers = await _detect_blockers(
        db, project_uuid, WorkflowPhase.ADECUACION, "basica", gov_basica,
    )
    assert all(b.motor != "m30" for b in basica_blockers)

    # cadencia comité con alerta → blocker m_meetings.
    gov_cad = {"steps": [
        {"key": "comite", "cadencia": {"alerta_pre_auditoria": True}},
    ]}
    cad_blockers = await _detect_blockers(
        db, project_uuid, WorkflowPhase.ADECUACION, "media", gov_cad,
    )
    assert any(
        b.motor == "m_meetings" and b.waiting_on == "admin"
        for b in cad_blockers
    )
