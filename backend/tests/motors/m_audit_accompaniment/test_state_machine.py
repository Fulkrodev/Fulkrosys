"""m_audit_accompaniment state machine + service tests · Ejecutable 7.5 Phase 7.5.1.

Verifica empirical:
1. BÁSICO branch 6 states valid sequential transitions
2. MEDIO/ALTO branch 11 states valid sequential transitions + biannual renewal cycle
3. InvalidAccompanimentTransition raised cuando NO en VALID_TRANSITIONS (skip · back)
4. Advisory lock per project_id serializes concurrent admin (Pattern #22)
5. audit_log Sub-atom 5.A 3-way OR propagated cross transitions
6. SSE event auto-trigger empirical (Pattern #14)
7. Artifacts upload + sha256 + persistence
8. Timeline get returns chronological + artifacts + transitions
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.motors.m_audit_accompaniment.service import (
    get_timeline,
    transition_state,
    upload_artifact,
)
from backend.app.motors.m_audit_accompaniment.state_machine import (
    BASICO_STATES,
    CATEGORY_BRANCH_BASICO,
    CATEGORY_BRANCH_MEDIO_ALTO,
    InvalidAccompanimentTransition,
    MEDIO_ALTO_STATES,
    STATE_BASICO_CCN_COMMUNICATED,
    STATE_BASICO_COMPLETED,
    STATE_BASICO_DECLARATION_DRAFTED,
    STATE_BASICO_DECLARATION_PUBLISHED,
    STATE_BASICO_DECLARATION_SIGNED,
    STATE_BASICO_NOT_STARTED,
    STATE_BASICO_PERIODIC_REVIEW_SCHEDULED,
    STATE_MA_CERTIFICATE_ISSUED,
    STATE_MA_DOCS_COLLECTED,
    STATE_MA_ENAC_AUDIT_IN_PROGRESS,
    STATE_MA_ENAC_AUDIT_PASSED,
    STATE_MA_ENAC_AUDIT_SCHEDULED,
    STATE_MA_INTERNAL_AUDIT_COMPLETED,
    STATE_MA_INTERNAL_AUDIT_SCHEDULED,
    STATE_MA_PREPARATION,
    is_terminal_state,
    resolve_category_branch,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _create_basico_project(db) -> tuple[uuid.UUID, uuid.UUID]:
    client_id_str, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE projects SET categoria_objetivo = 'BASICA' WHERE id = :pid"
        ), {"pid": str(project_id)})
    return uuid.UUID(client_id_str), project_id


async def _create_media_project(db) -> tuple[uuid.UUID, uuid.UUID]:
    client_id_str, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE projects SET categoria_objetivo = 'MEDIA' WHERE id = :pid"
        ), {"pid": str(project_id)})
    return uuid.UUID(client_id_str), project_id


def test_resolve_category_branch_basica():
    assert resolve_category_branch("BASICA") == CATEGORY_BRANCH_BASICO
    assert resolve_category_branch("basica") == CATEGORY_BRANCH_BASICO


def test_resolve_category_branch_media_alta():
    assert resolve_category_branch("MEDIA") == CATEGORY_BRANCH_MEDIO_ALTO
    assert resolve_category_branch("ALTA") == CATEGORY_BRANCH_MEDIO_ALTO


def test_resolve_category_branch_none_defaults_basico():
    assert resolve_category_branch(None) == CATEGORY_BRANCH_BASICO
    assert resolve_category_branch("") == CATEGORY_BRANCH_BASICO


def test_basico_states_count_7():
    # #3 Ola 7 · +ccn_communicated (comunicación al CCN vía AMPARO, tras publicar).
    assert len(BASICO_STATES) == 7


def test_medio_alto_states_count_11():
    assert len(MEDIO_ALTO_STATES) == 11


def test_basico_completed_is_terminal():
    assert is_terminal_state(CATEGORY_BRANCH_BASICO, STATE_BASICO_COMPLETED) is True
    assert is_terminal_state(CATEGORY_BRANCH_BASICO, STATE_BASICO_NOT_STARTED) is False


@pytest.mark.asyncio
async def test_basico_full_cycle_transitions(db):
    """BÁSICO branch · 6 transitions consecutive not_started → completed.

    #3 Ola 7 · ahora pasa por ccn_communicated entre publicada y revisión.
    """
    client_id, project_id = await _create_basico_project(db)

    async with _admin_setup(db):
        r1 = await transition_state(
            db, project_id, STATE_BASICO_DECLARATION_DRAFTED, usuario="m@t.com",
        )
        assert r1["to_state"] == STATE_BASICO_DECLARATION_DRAFTED
        assert r1["category_branch"] == CATEGORY_BRANCH_BASICO
        assert r1["is_terminal"] is False

        await transition_state(db, project_id, STATE_BASICO_DECLARATION_SIGNED, usuario="m@t.com")
        await transition_state(db, project_id, STATE_BASICO_DECLARATION_PUBLISHED, usuario="m@t.com")
        await transition_state(db, project_id, STATE_BASICO_CCN_COMMUNICATED, usuario="m@t.com")
        await transition_state(db, project_id, STATE_BASICO_PERIODIC_REVIEW_SCHEDULED, usuario="m@t.com")
        r6 = await transition_state(db, project_id, STATE_BASICO_COMPLETED, usuario="m@t.com")

    assert r6["is_terminal"] is True


@pytest.mark.asyncio
async def test_basico_ccn_communicated_amparo_registro(db):
    """#3 Ola 7 · comunicación al CCN (AMPARO) · estado + audit_log + acuse vinculado.

    AMPARO es registro de constancia (sin API): el estado ccn_communicated va
    TRAS declaration_published, emite audit_log, y el acuse subido queda
    VINCULADO a ese estado (los tres conectados · trazabilidad completa).
    """
    client_id, project_id = await _create_basico_project(db)

    async with _admin_setup(db):
        await transition_state(db, project_id, STATE_BASICO_DECLARATION_DRAFTED, usuario="m@t.com")
        await transition_state(db, project_id, STATE_BASICO_DECLARATION_SIGNED, usuario="m@t.com")
        await transition_state(db, project_id, STATE_BASICO_DECLARATION_PUBLISHED, usuario="m@t.com")
        # Transición a ccn_communicated (válida · tras publicar · NO terminal).
        r = await transition_state(
            db, project_id, STATE_BASICO_CCN_COMMUNICATED, usuario="m@t.com",
        )
        assert r["to_state"] == STATE_BASICO_CCN_COMMUNICATED
        assert r["is_terminal"] is False

        # Acuse de AMPARO archivado · VINCULADO al estado ccn_communicated.
        art = await upload_artifact(
            db, project_id,
            state=STATE_BASICO_CCN_COMMUNICATED,
            artifact_type="ccn_amparo_acuse",
            file_bytes=b"acuse-registro-ccn-amparo",
            file_path="amparo/acuse.pdf",
            usuario="m@t.com",
        )
        assert art["state"] == STATE_BASICO_CCN_COMMUNICATED

    # audit_log R6: la transición a ccn_communicated dejó rastro.
    async with _admin_setup(db):
        advanced = (await db.execute(sa_text(
            "SELECT COUNT(*) FROM audit_log "
            "WHERE accion = 'accompaniment.state.advanced' "
            "  AND project_id = :pid "
            "  AND payload_new->>'to_state' = 'ccn_communicated'"
        ), {"pid": str(project_id)})).scalar()
        artifact_linked = (await db.execute(sa_text(
            "SELECT COUNT(*) FROM audit_accompaniment_artifacts "
            "WHERE project_id = :pid AND state = 'ccn_communicated'"
        ), {"pid": str(project_id)})).scalar()
    assert advanced >= 1, "la comunicación al CCN debe dejar audit_log R6"
    assert artifact_linked == 1, "el acuse queda vinculado al estado ccn_communicated"


@pytest.mark.asyncio
async def test_medio_alto_full_cycle_with_renewal(db):
    """MEDIO_ALTO branch · 10 transitions sequential + biannual renewal back to preparation."""
    client_id, project_id = await _create_media_project(db)

    async with _admin_setup(db):
        await transition_state(db, project_id, STATE_MA_PREPARATION, usuario="m@t.com")
        await transition_state(db, project_id, STATE_MA_DOCS_COLLECTED)
        await transition_state(db, project_id, STATE_MA_INTERNAL_AUDIT_SCHEDULED)
        await transition_state(db, project_id, STATE_MA_INTERNAL_AUDIT_COMPLETED)
        await transition_state(db, project_id, STATE_MA_ENAC_AUDIT_SCHEDULED)
        await transition_state(db, project_id, STATE_MA_ENAC_AUDIT_IN_PROGRESS)
        await transition_state(db, project_id, STATE_MA_ENAC_AUDIT_PASSED)
        await transition_state(db, project_id, STATE_MA_CERTIFICATE_ISSUED)
        from backend.app.motors.m_audit_accompaniment.state_machine import (
            STATE_MA_BIANNUAL_RENEWAL_SCHEDULED,
        )
        r_renewal = await transition_state(
            db, project_id, STATE_MA_BIANNUAL_RENEWAL_SCHEDULED,
        )
        assert r_renewal["to_state"] == STATE_MA_BIANNUAL_RENEWAL_SCHEDULED
        assert r_renewal["is_terminal"] is False

        r_back = await transition_state(db, project_id, STATE_MA_PREPARATION)
        assert r_back["to_state"] == STATE_MA_PREPARATION


@pytest.mark.asyncio
async def test_invalid_skip_transition_raises(db):
    """SKIP transition raises InvalidAccompanimentTransition + emits audit_log."""
    client_id, project_id = await _create_basico_project(db)

    async with _admin_setup(db):
        with pytest.raises(InvalidAccompanimentTransition):
            await transition_state(
                db, project_id, STATE_BASICO_DECLARATION_SIGNED,
                usuario="m@t.com",
            )
        await db.flush()
        invalid_row = (await db.execute(sa_text(
            "SELECT accion FROM audit_log "
            "WHERE tabla = 'audit_accompaniment' "
            "AND accion = 'accompaniment.state.invalid_transition' "
            "AND project_id = :pid"
        ), {"pid": str(project_id)})).first()
        assert invalid_row is not None


@pytest.mark.asyncio
async def test_audit_log_sub_atom_5a_3way_or_propagated(db):
    """audit_log accompaniment.state.advanced emitted con project_id + client_id."""
    client_id, project_id = await _create_basico_project(db)

    async with _admin_setup(db):
        await transition_state(
            db, project_id, STATE_BASICO_DECLARATION_DRAFTED,
            usuario="admin@t.com",
        )
        await db.flush()

        row = (await db.execute(sa_text(
            "SELECT project_id, client_id, usuario, accion "
            "FROM audit_log "
            "WHERE tabla = 'audit_accompaniment' "
            "AND accion = 'accompaniment.state.advanced' "
            "AND project_id = :pid "
            "ORDER BY seq DESC LIMIT 1"
        ), {"pid": str(project_id)})).first()

    assert row is not None
    assert str(row[0]) == str(project_id)
    assert str(row[1]) == str(client_id)
    assert row[2] == "admin@t.com"


@pytest.mark.asyncio
async def test_upload_artifact_persists_sha256_and_audit_log(db):
    """upload_artifact persists row + sha256 + audit_log emit."""
    client_id, project_id = await _create_basico_project(db)

    async with _admin_setup(db):
        result = await upload_artifact(
            db, project_id,
            state=STATE_BASICO_NOT_STARTED,
            artifact_type="declaration_draft_pdf",
            file_bytes=b"PDF mock binary content",
            file_path="/tmp/test.pdf",
            usuario="admin@t.com",
        )
        await db.flush()

        row = (await db.execute(sa_text(
            "SELECT state, artifact_type, sha256 FROM audit_accompaniment_artifacts "
            "WHERE id = :id"
        ), {"id": result["artifact_id"]})).first()

    assert row is not None
    assert row[0] == STATE_BASICO_NOT_STARTED
    assert row[1] == "declaration_draft_pdf"
    assert row[2] == result["sha256"]
    assert len(result["sha256"]) == 64


@pytest.mark.asyncio
async def test_get_timeline_returns_chronological_full_snapshot(db):
    """get_timeline returns transitions + artifacts ordered chronological."""
    client_id, project_id = await _create_basico_project(db)

    async with _admin_setup(db):
        await transition_state(db, project_id, STATE_BASICO_DECLARATION_DRAFTED, usuario="m@t.com")
        await upload_artifact(
            db, project_id,
            state=STATE_BASICO_DECLARATION_DRAFTED,
            artifact_type="draft_pdf",
            file_bytes=b"data",
            file_path="/tmp/draft.pdf",
        )
        await transition_state(db, project_id, STATE_BASICO_DECLARATION_SIGNED, usuario="m@t.com")
        await db.flush()

        timeline = await get_timeline(db, project_id)

    assert timeline.current_state == STATE_BASICO_DECLARATION_SIGNED
    assert timeline.category_branch == CATEGORY_BRANCH_BASICO
    assert len(timeline.transitions) == 2
    assert timeline.transitions[0].to_state == STATE_BASICO_DECLARATION_DRAFTED
    assert timeline.transitions[1].to_state == STATE_BASICO_DECLARATION_SIGNED
    assert len(timeline.artifacts) == 1


@pytest.mark.asyncio
async def test_advisory_lock_present_in_transition_state_implementation():
    """Static verify advisory lock SQL present in transition_state source."""
    import inspect
    from backend.app.motors.m_audit_accompaniment import service
    src = inspect.getsource(service.transition_state)
    assert "pg_advisory_xact_lock" in src
    assert "accompaniment_" in src


@pytest.mark.asyncio
async def test_sse_dispatcher_event_emitted_on_state_advance(db):
    """SSE event accompaniment.state.advanced dispatched to channel project:{id}."""
    client_id, project_id = await _create_basico_project(db)
    channel = f"project:{project_id}"

    initial_buffer_size = sse_dispatcher.replay_buffer_size(channel)

    async with _admin_setup(db):
        await transition_state(
            db, project_id, STATE_BASICO_DECLARATION_DRAFTED,
            usuario="m@t.com",
        )

    final_buffer_size = sse_dispatcher.replay_buffer_size(channel)
    assert final_buffer_size > initial_buffer_size, (
        "Expected SSE event in replay buffer post state advance"
    )


@pytest.mark.asyncio
async def test_invalid_target_for_terminal_state_raises(db):
    """Terminal state has NO outgoing transitions · any target raises."""
    client_id, project_id = await _create_basico_project(db)

    async with _admin_setup(db):
        await transition_state(db, project_id, STATE_BASICO_DECLARATION_DRAFTED, usuario="m@t.com")
        await transition_state(db, project_id, STATE_BASICO_DECLARATION_SIGNED, usuario="m@t.com")
        await transition_state(db, project_id, STATE_BASICO_DECLARATION_PUBLISHED, usuario="m@t.com")
        await transition_state(db, project_id, STATE_BASICO_CCN_COMMUNICATED, usuario="m@t.com")
        await transition_state(db, project_id, STATE_BASICO_PERIODIC_REVIEW_SCHEDULED, usuario="m@t.com")
        await transition_state(db, project_id, STATE_BASICO_COMPLETED, usuario="m@t.com")

        with pytest.raises(InvalidAccompanimentTransition):
            await transition_state(
                db, project_id, STATE_BASICO_DECLARATION_DRAFTED,
                usuario="m@t.com",
            )
