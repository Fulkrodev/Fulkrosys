"""Corrective loop service tests · Phase 10.2 (Ejecutable 5 Sesión 3B-2B.10).

Verifica state machine canonical open → in_progress → closed:
1. open_loop_for_gap returns LoopState con state=open + loop_id generado
2. transition_loop happy path open → in_progress → closed
3. InvalidLoopTransition raised cuando skipping states inversos
4. list_open_loops filters terminal closed correctly
5. audit_log events emitted Sub-atom 5.A 3-way OR (project_id + client_id)
6. close_loop convenience wrapper functional
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m09_audit_prep.corrective_loop_service import (
    InvalidLoopTransition,
    LOOP_STATE_CLOSED,
    LOOP_STATE_IN_PROGRESS,
    LOOP_STATE_OPEN,
    LoopState,
    close_loop,
    list_open_loops,
    open_loop_for_gap,
    transition_loop,
)
from backend.tests.conftest import _admin_setup, setup_test_project


@pytest.mark.asyncio
async def test_open_loop_for_gap_returns_open_state(db):
    """open_loop_for_gap emits CORRECTIVE_LOOP_OPENED · returns LoopState(state=open)."""
    client_id, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        state = await open_loop_for_gap(
            db,
            project_id,
            gap_id="op.acc.6",
            gap_type="evidence_missing",
            severity="critical",
            client_id=uuid.UUID(client_id),
            usuario="tester@example.com",
        )

    assert isinstance(state, LoopState)
    assert state.state == LOOP_STATE_OPEN
    assert state.gap_id == "op.acc.6"
    assert state.gap_type == "evidence_missing"
    assert state.severity == "critical"
    assert state.project_id == str(project_id)
    assert state.loop_id  # UUID generated


@pytest.mark.asyncio
async def test_transition_loop_canonical_cycle(db):
    """open → in_progress → closed canonical transitions all valid."""
    client_id, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        state = await open_loop_for_gap(
            db,
            project_id,
            gap_id="mp.s.2",
            gap_type="public_bucket",
            severity="critical",
            client_id=uuid.UUID(client_id),
        )
        loop_id = uuid.UUID(state.loop_id)

        in_progress = await transition_loop(
            db, loop_id, LOOP_STATE_IN_PROGRESS,
            client_id=uuid.UUID(client_id),
        )
        assert in_progress.state == LOOP_STATE_IN_PROGRESS

        closed = await transition_loop(
            db, loop_id, LOOP_STATE_CLOSED,
            client_id=uuid.UUID(client_id),
            resolution_note="Bucket policy fixed by admin",
        )
        assert closed.state == LOOP_STATE_CLOSED
        assert closed.resolution_note == "Bucket policy fixed by admin"


@pytest.mark.asyncio
async def test_invalid_transition_closed_to_open_raises(db):
    """Closed state is terminal · cannot transition back to any state."""
    client_id, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        state = await open_loop_for_gap(
            db,
            project_id,
            gap_id="mp.info.3",
            gap_type="encryption_missing",
            severity="critical",
            client_id=uuid.UUID(client_id),
        )
        loop_id = uuid.UUID(state.loop_id)

        await close_loop(
            db, loop_id,
            resolution_note="Encryption enabled",
            client_id=uuid.UUID(client_id),
        )

        with pytest.raises(InvalidLoopTransition):
            await transition_loop(
                db, loop_id, LOOP_STATE_OPEN,
                client_id=uuid.UUID(client_id),
            )

        with pytest.raises(InvalidLoopTransition):
            await transition_loop(
                db, loop_id, LOOP_STATE_IN_PROGRESS,
                client_id=uuid.UUID(client_id),
            )


@pytest.mark.asyncio
async def test_list_open_loops_filters_closed(db):
    """list_open_loops returns open + in_progress · excludes closed."""
    client_id, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        s1 = await open_loop_for_gap(
            db, project_id, gap_id="op.acc.6", gap_type="evidence_missing",
            severity="critical", client_id=uuid.UUID(client_id),
        )
        s2 = await open_loop_for_gap(
            db, project_id, gap_id="op.exp.8", gap_type="logging_missing",
            severity="high", client_id=uuid.UUID(client_id),
        )
        s3 = await open_loop_for_gap(
            db, project_id, gap_id="op.cont.3", gap_type="backup_missing",
            severity="high", client_id=uuid.UUID(client_id),
        )

        await transition_loop(
            db, uuid.UUID(s2.loop_id), LOOP_STATE_IN_PROGRESS,
            client_id=uuid.UUID(client_id),
        )
        await close_loop(
            db, uuid.UUID(s3.loop_id),
            resolution_note="Backups configured",
            client_id=uuid.UUID(client_id),
        )

        open_states = await list_open_loops(db, project_id)

    open_ids = {s.loop_id for s in open_states}
    assert s1.loop_id in open_ids  # still open
    assert s2.loop_id in open_ids  # in_progress
    assert s3.loop_id not in open_ids  # closed excluded
    assert len(open_states) == 2


@pytest.mark.asyncio
async def test_audit_log_events_emitted_sub_atom_5a_3way_or(db):
    """Verify audit_log events emitted con project_id + client_id (Sub-atom 5.A 3-way OR)."""
    client_id, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        state = await open_loop_for_gap(
            db,
            project_id,
            gap_id="mp.s.2",
            gap_type="public_bucket",
            severity="critical",
            client_id=uuid.UUID(client_id),
            usuario="audit_test@example.com",
        )
        await db.flush()

        rows = (await db.execute(sa_text(
            "SELECT accion, project_id, client_id, usuario FROM audit_log "
            "WHERE tabla = 'corrective_loops' AND registro_id = :lid"
        ), {"lid": state.loop_id})).all()

    assert len(rows) == 1
    accion, pid, cid, usr = rows[0]
    assert accion == "corrective.loop.opened"
    assert str(pid) == str(project_id)
    assert str(cid) == client_id
    assert usr == "audit_test@example.com"


@pytest.mark.asyncio
async def test_transition_loop_not_found_raises(db):
    """transition_loop on non-existent loop_id raises ValueError."""
    random_loop = uuid.uuid4()
    with pytest.raises(ValueError, match="not found"):
        await transition_loop(db, random_loop, LOOP_STATE_IN_PROGRESS)
