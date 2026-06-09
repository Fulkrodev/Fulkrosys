"""Corrective loop service · state machine open → in_progress → closed.

Sesión 3B-2B.10 Ejecutable 5 Phase 10.2 (2026-05-27).

State machine canonical Pattern #18 (state machine reuse Phase 3A Sesión 3B-2B.8):
- States: ``open`` (initial) → ``in_progress`` (admin remediation started) → ``closed`` (terminal)
- Invalid transitions raise InvalidLoopTransition (no skipping states)
- audit_log emit corrective.loop.opened · corrective.loop.in_progress · corrective.loop.closed
  (Sub-atom 5.A 3-way OR · project_id + client_id propagated)

Storage strategy ADR-025 sostained:
- NO new table · derive current state from latest audit_log event per loop_id
- loop_id = synthetic UUID (generated at open) · registro_id field in audit_log
- payload_new jsonb stores loop metadata (gap_id, gap_type, severity, resolution_note)
- ORDER BY seq DESC LIMIT 1 retrieves latest state per loop_id

Pure functional service · NO HTTP coupling · accept db + project_id.
Reusable consumer: SimulacroPreEnacService (Phase 10.3).
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from typing import Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m09_audit_prep.audit_events import (
    CORRECTIVE_LOOP_CLOSED,
    CORRECTIVE_LOOP_IN_PROGRESS,
    CORRECTIVE_LOOP_OPENED,
)


# ════════════════════════════════════════════════════════════════════════
# State machine canonical
# ════════════════════════════════════════════════════════════════════════

LOOP_STATE_OPEN = "open"
LOOP_STATE_IN_PROGRESS = "in_progress"
LOOP_STATE_CLOSED = "closed"

VALID_TRANSITIONS: dict[str, set[str]] = {
    LOOP_STATE_OPEN: {LOOP_STATE_IN_PROGRESS, LOOP_STATE_CLOSED},
    LOOP_STATE_IN_PROGRESS: {LOOP_STATE_CLOSED},
    LOOP_STATE_CLOSED: set(),
}

STATE_EVENT_MAP: dict[str, str] = {
    LOOP_STATE_OPEN: CORRECTIVE_LOOP_OPENED,
    LOOP_STATE_IN_PROGRESS: CORRECTIVE_LOOP_IN_PROGRESS,
    LOOP_STATE_CLOSED: CORRECTIVE_LOOP_CLOSED,
}


class InvalidLoopTransition(ValueError):
    """Raised when attempting an invalid state transition."""


@dataclass
class LoopState:
    """Current state snapshot of a corrective loop."""

    loop_id: str
    state: str
    project_id: str
    gap_id: Optional[str]
    gap_type: Optional[str]
    severity: Optional[str]
    resolution_note: Optional[str]
    opened_at: Optional[str]
    last_updated_at: Optional[str]
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ════════════════════════════════════════════════════════════════════════
# Persistence helpers (audit_log derived · ADR-025 sostained)
# ════════════════════════════════════════════════════════════════════════


async def _emit_loop_event(
    db: AsyncSession,
    *,
    loop_id: uuid.UUID,
    project_id: uuid.UUID,
    client_id: Optional[uuid.UUID],
    accion: str,
    payload: dict,
    usuario: Optional[str] = None,
) -> None:
    """Insert audit_log row for loop event · Sub-atom 5.A 3-way OR."""
    await db.execute(sa_text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, client_id, payload_new, timestamp) "
        "VALUES (gen_random_uuid(), 'corrective_loops', :lid, "
        ":accion, :user, :pid, :cid, :payload, now())"
    ), {
        "lid": str(loop_id),
        "accion": accion,
        "user": usuario or "system",
        "pid": str(project_id),
        "cid": str(client_id) if client_id else None,
        "payload": json.dumps(payload),
    })


async def _fetch_latest_state_row(
    db: AsyncSession, loop_id: uuid.UUID,
) -> Optional[tuple]:
    """Latest audit_log row for loop_id (state machine current state)."""
    row = (await db.execute(sa_text(
        "SELECT accion, payload_new, project_id, timestamp, "
        "(SELECT MIN(timestamp) FROM audit_log al2 "
        " WHERE al2.registro_id = :lid AND al2.tabla = 'corrective_loops') AS opened_at "
        "FROM audit_log "
        "WHERE registro_id = :lid AND tabla = 'corrective_loops' "
        "ORDER BY seq DESC LIMIT 1"
    ), {"lid": str(loop_id)})).first()
    return row


def _accion_to_state(accion: str) -> str:
    """Reverse-map audit_log accion → loop state."""
    for state, ev in STATE_EVENT_MAP.items():
        if ev == accion:
            return state
    return LOOP_STATE_OPEN


async def _build_loop_state(
    db: AsyncSession, loop_id: uuid.UUID,
) -> Optional[LoopState]:
    row = await _fetch_latest_state_row(db, loop_id)
    if row is None:
        return None
    accion, payload_new, project_id, last_ts, opened_at = row
    payload = payload_new if isinstance(payload_new, dict) else {}
    state = _accion_to_state(accion)
    return LoopState(
        loop_id=str(loop_id),
        state=state,
        project_id=str(project_id) if project_id else "",
        gap_id=payload.get("gap_id"),
        gap_type=payload.get("gap_type"),
        severity=payload.get("severity"),
        resolution_note=payload.get("resolution_note"),
        opened_at=opened_at.isoformat() if opened_at else None,
        last_updated_at=last_ts.isoformat() if last_ts else None,
        metadata=payload.get("metadata", {}),
    )


# ════════════════════════════════════════════════════════════════════════
# Public API · pure functional state machine
# ════════════════════════════════════════════════════════════════════════


async def open_loop_for_gap(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    gap_id: str,
    gap_type: str,
    severity: str,
    client_id: Optional[uuid.UUID] = None,
    metadata: Optional[dict] = None,
    usuario: Optional[str] = None,
) -> LoopState:
    """Open new corrective loop for gap · initial state ``open``.

    Args:
        db: AsyncSession
        project_id: project scope
        gap_id: external identifier (medida_code · evidence_id · etc)
        gap_type: 'evidence_missing' · 'dda_mismatch' · 'pentest_finding' · etc
        severity: 'critical' · 'high' · 'medium' · 'low'
        client_id: optional (Sub-atom 5.A 3-way OR)
        metadata: optional additional context (jsonb stored)
        usuario: audit_log actor

    Returns:
        LoopState con state='open' · loop_id generado
    """
    loop_id = uuid.uuid4()
    payload = {
        "gap_id": gap_id,
        "gap_type": gap_type,
        "severity": severity,
        "metadata": metadata or {},
    }
    await _emit_loop_event(
        db,
        loop_id=loop_id,
        project_id=project_id,
        client_id=client_id,
        accion=CORRECTIVE_LOOP_OPENED,
        payload=payload,
        usuario=usuario,
    )
    state = await _build_loop_state(db, loop_id)
    assert state is not None, "Loop state should exist post-open emit"
    return state


async def transition_loop(
    db: AsyncSession,
    loop_id: uuid.UUID,
    to_state: str,
    *,
    client_id: Optional[uuid.UUID] = None,
    resolution_note: Optional[str] = None,
    usuario: Optional[str] = None,
) -> LoopState:
    """Transition loop state · validates canonical transitions.

    Sesión 3B-2B.11 Phase 11.2: pg_advisory_xact_lock per loop_id evita race
    condition concurrent transitions (read-modify-write atomic). Mirror del
    pattern audit_log existing (advisory lock canonical PostgreSQL approach
    para serialize critical mutations · no rompe RLS · transaction-scoped).

    Raises:
        InvalidLoopTransition · si current → to_state not valid
        ValueError · si loop_id not found
    """
    from sqlalchemy import text as sa_text

    await db.execute(sa_text(
        "SELECT pg_advisory_xact_lock(hashtext('corrective_loop_' || :lid))"
    ), {"lid": str(loop_id)})

    current = await _build_loop_state(db, loop_id)
    if current is None:
        raise ValueError(f"Loop {loop_id} not found")

    if to_state not in VALID_TRANSITIONS.get(current.state, set()):
        raise InvalidLoopTransition(
            f"Invalid transition {current.state} → {to_state}"
        )

    payload = {
        "gap_id": current.gap_id,
        "gap_type": current.gap_type,
        "severity": current.severity,
        "resolution_note": resolution_note,
        "metadata": current.metadata,
    }
    project_id_uuid = uuid.UUID(current.project_id) if current.project_id else None
    if project_id_uuid is None:
        raise ValueError(f"Loop {loop_id} missing project_id in audit_log")

    accion = STATE_EVENT_MAP[to_state]
    await _emit_loop_event(
        db,
        loop_id=loop_id,
        project_id=project_id_uuid,
        client_id=client_id,
        accion=accion,
        payload=payload,
        usuario=usuario,
    )

    new_state = await _build_loop_state(db, loop_id)
    assert new_state is not None
    return new_state


async def close_loop(
    db: AsyncSession,
    loop_id: uuid.UUID,
    *,
    resolution_note: str,
    client_id: Optional[uuid.UUID] = None,
    usuario: Optional[str] = None,
) -> LoopState:
    """Convenience wrapper · transition to closed con resolution_note."""
    return await transition_loop(
        db,
        loop_id,
        LOOP_STATE_CLOSED,
        client_id=client_id,
        resolution_note=resolution_note,
        usuario=usuario,
    )


async def list_open_loops(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> list[LoopState]:
    """List corrective loops for project · state != closed (open + in_progress).

    Returns loops in chronological order (oldest first by opened_at).
    """
    distinct_loops = (await db.execute(sa_text(
        "SELECT DISTINCT registro_id FROM audit_log "
        "WHERE tabla = 'corrective_loops' AND project_id = :pid"
    ), {"pid": str(project_id)})).all()

    states: list[LoopState] = []
    for row in distinct_loops:
        loop_id = row[0]
        state = await _build_loop_state(db, loop_id)
        if state is not None and state.state != LOOP_STATE_CLOSED:
            states.append(state)

    states.sort(key=lambda s: s.opened_at or "")
    return states
