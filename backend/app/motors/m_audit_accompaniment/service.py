"""Audit accompaniment service · pure functional state machine + advisory lock.

Sesión 3B-4 Ejecutable 7.5 (2026-05-27).

Patterns reused:
- #18 state machine canonical (transitions strict per branch BÁSICO vs MEDIO_ALTO)
- #22 advisory lock per project_id (pg_advisory_xact_lock concurrent admin safe)
- #14 SSE + ClientNotification dual emit (auto-trigger cliente updates realtime)

audit_log emit Sub-atom 5.A 3-way OR · project_id + client_id propagated.

Cliente-mínimo filosofía: cliente RECIBE timeline updates · NO opera proceso.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.database import set_tenant_context
from backend.app.motors.m_audit_accompaniment.state_machine import (
    ACCOMPANIMENT_ARTIFACT_UPLOADED,
    ACCOMPANIMENT_CYCLE_COMPLETED,
    ACCOMPANIMENT_INVALID_TRANSITION,
    ACCOMPANIMENT_STATE_ADVANCED,
    CATEGORY_BRANCH_BASICO,
    InvalidAccompanimentTransition,
    get_initial_state,
    get_transitions_for_branch,
    is_terminal_state,
    resolve_category_branch,
)


logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
# Dataclasses
# ════════════════════════════════════════════════════════════════════════


@dataclass
class TimelineEntry:
    """Historic transition entry para timeline UI rendering."""

    from_state: Optional[str]
    to_state: str
    advanced_by: Optional[str]
    advanced_at: str
    transition_metadata: dict = field(default_factory=dict)


@dataclass
class ArtifactEntry:
    """Artifact uploaded entry para timeline UI rendering."""

    id: str
    state: str
    artifact_type: str
    file_path: str
    file_size_bytes: int
    sha256: str
    uploaded_by: Optional[str]
    uploaded_at: str


@dataclass
class AccompanimentTimeline:
    """Full timeline snapshot · JSON-serializable."""

    project_id: str
    category_branch: str
    current_state: str
    last_advanced_at: Optional[str]
    is_terminal: bool
    transitions: list[TimelineEntry] = field(default_factory=list)
    artifacts: list[ArtifactEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ════════════════════════════════════════════════════════════════════════
# Helpers (audit_log + SSE + client_notification)
# ════════════════════════════════════════════════════════════════════════


async def _resolve_project_meta(
    db: AsyncSession, project_id: uuid.UUID,
) -> tuple[Optional[uuid.UUID], Optional[str]]:
    """Lookup client_id + categoria_objetivo. None tuple si project not found.

    Bajo el rol runtime ``fulkro_app`` la RLS está forzada y ``projects`` queda
    invisible hasta fijar el contexto de tenant (``current_client_id()`` NULL →
    0 filas → categoria=None → BASICO incorrecto para MEDIA/ALTA). Mirroreamos
    el patrón de m27_conformity ``_set_project_rls``: resolvemos el owner vía la
    función SECURITY DEFINER ``get_project_owner`` (bypassa RLS exponiendo solo
    el client_id), fijamos el contexto de tenant para esta transacción y recién
    entonces leemos ``categoria_objetivo`` (ya visible bajo RLS). Esto también
    habilita las lecturas/escrituras project-scoped posteriores en la misma
    transacción (``_ensure_state_row`` etc.).
    """
    cid = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"),
        {"pid": str(project_id)},
    )).scalar()
    if not cid:
        return None, None
    client_id = cid if isinstance(cid, uuid.UUID) else uuid.UUID(str(cid))
    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    categoria = (await db.execute(sa_text(
        "SELECT categoria_objetivo FROM projects WHERE id = :pid"
    ), {"pid": str(project_id)})).scalar()
    return client_id, categoria


async def _emit_accompaniment_audit_log(
    db: AsyncSession,
    *,
    accion: str,
    project_id: uuid.UUID,
    client_id: Optional[uuid.UUID],
    payload: dict,
    usuario: Optional[str] = None,
) -> None:
    """Insert audit_log row · Sub-atom 5.A 3-way OR (project_id + client_id)."""
    await db.execute(sa_text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, client_id, payload_new, timestamp) "
        "VALUES (gen_random_uuid(), 'audit_accompaniment', :rid, "
        ":accion, :user, :pid, :cid, :payload, now())"
    ), {
        "rid": str(project_id),
        "accion": accion,
        "user": usuario or "system",
        "pid": str(project_id),
        "cid": str(client_id) if client_id else None,
        "payload": json.dumps(payload),
    })


async def _emit_sse_state_advanced(
    project_id: uuid.UUID, from_state: Optional[str], to_state: str, branch: str,
) -> None:
    """SSE dispatch cliente channel · Pattern #14 dual emit."""
    try:
        channel = f"project:{project_id}"
        await sse_dispatcher.dispatch(
            channel,
            "accompaniment.state.advanced",
            {
                "project_id": str(project_id),
                "from_state": from_state,
                "to_state": to_state,
                "category_branch": branch,
            },
        )
    except Exception as exc:
        logger.warning(
            "SSE dispatch accompaniment.state.advanced failed (best-effort): %s",
            exc,
        )


async def _ensure_state_row(
    db: AsyncSession,
    project_id: uuid.UUID,
    branch: str,
) -> str:
    """Get-or-create state row · returns current_state.

    Idempotent · safe under advisory lock concurrent admin calls.
    """
    row = (await db.execute(sa_text(
        "SELECT current_state FROM audit_accompaniment_state "
        "WHERE project_id = :pid AND deleted_at IS NULL"
    ), {"pid": str(project_id)})).first()
    if row is not None:
        return row[0]

    initial = get_initial_state(branch)
    await db.execute(sa_text(
        "INSERT INTO audit_accompaniment_state "
        "(id, project_id, current_state, category_branch, "
        "accompaniment_metadata, created_at) "
        "VALUES (gen_random_uuid(), :pid, :state, :branch, '{}'::jsonb, now())"
    ), {
        "pid": str(project_id),
        "state": initial,
        "branch": branch,
    })
    return initial


# ════════════════════════════════════════════════════════════════════════
# Public API · pure functional state machine
# ════════════════════════════════════════════════════════════════════════


async def transition_state(
    db: AsyncSession,
    project_id: uuid.UUID,
    target_state: str,
    *,
    usuario: Optional[str] = None,
    transition_metadata: Optional[dict] = None,
    allow_open_nc: bool = False,
) -> dict:
    """Advance state machine to target_state · validates canonical transitions.

    Pattern #22 advisory lock per project_id evita race concurrent admin.
    Pattern #14 SSE auto-trigger cliente realtime post-commit.
    Sub-atom 5.A audit_log 3-way OR propagated.

    GATE-7 (#40/#43 · FRENTE D): el parón pre-ENAC bloquea la solicitud de
    auditoría ENAC y la firma de la Declaración de Conformidad si el último
    simulacro tiene NC mayores abiertas, y exige un simulacro ejecutado antes de
    marcar la auditoría interna como completada. ``allow_open_nc=True`` es el
    escape-hatch administrativo justificado (queda trazado en audit_log).

    Raises:
        InvalidAccompanimentTransition · si current → target_state NO en VALID_TRANSITIONS
        WorkflowGateError · si GATE-7 no se cumple (NC mayores / sin simulacro)
        ValueError · si project_id no existe
    """
    await db.execute(sa_text(
        "SELECT pg_advisory_xact_lock(hashtext('accompaniment_' || :pid))"
    ), {"pid": str(project_id)})

    client_id, categoria = await _resolve_project_meta(db, project_id)
    if client_id is None and categoria is None:
        row = (await db.execute(sa_text(
            "SELECT 1 FROM projects WHERE id = :pid"
        ), {"pid": str(project_id)})).first()
        if row is None:
            raise ValueError(f"Project {project_id} not found")

    branch = resolve_category_branch(categoria)
    current_state = await _ensure_state_row(db, project_id, branch)

    valid_transitions = get_transitions_for_branch(branch)
    allowed_next = valid_transitions.get(current_state, set())

    if target_state not in allowed_next:
        await _emit_accompaniment_audit_log(
            db,
            accion=ACCOMPANIMENT_INVALID_TRANSITION,
            project_id=project_id,
            client_id=client_id,
            payload={
                "from_state": current_state,
                "attempted_to_state": target_state,
                "branch": branch,
                "reason": "not_in_VALID_TRANSITIONS",
            },
            usuario=usuario,
        )
        raise InvalidAccompanimentTransition(
            f"Invalid transition {current_state} → {target_state} (branch={branch})"
        )

    # GATE-7 (#40/#43 · FRENTE D): parón pre-ENAC sobre el último simulacro.
    # Bloquea solicitud ENAC / firma de conformidad con NC mayores abiertas y
    # exige simulacro ejecutado antes de la auditoría interna completada.
    from backend.app.core.workflow_gates import require_clean_audit_sim

    await require_clean_audit_sim(
        db,
        project_id,
        target_state=target_state,
        allow_open_nc=allow_open_nc,
    )

    await db.execute(sa_text(
        "UPDATE audit_accompaniment_state "
        "SET current_state = :ts, last_advanced_at = now(), updated_at = now() "
        "WHERE project_id = :pid"
    ), {"ts": target_state, "pid": str(project_id)})

    await db.execute(sa_text(
        "INSERT INTO audit_accompaniment_transitions "
        "(id, project_id, from_state, to_state, advanced_by, "
        "advanced_at, transition_metadata, created_at) "
        "VALUES (gen_random_uuid(), :pid, :fs, :ts, :usr, now(), :meta, now())"
    ), {
        "pid": str(project_id),
        "fs": current_state,
        "ts": target_state,
        "usr": usuario,
        "meta": json.dumps(transition_metadata or {}),
    })

    await _emit_accompaniment_audit_log(
        db,
        accion=ACCOMPANIMENT_STATE_ADVANCED,
        project_id=project_id,
        client_id=client_id,
        payload={
            "from_state": current_state,
            "to_state": target_state,
            "category_branch": branch,
            # GATE-7 escape-hatch trazado (#40): True si se forzó pese a NC mayores
            "nc_override": bool(allow_open_nc),
        },
        usuario=usuario,
    )

    if is_terminal_state(branch, target_state):
        await _emit_accompaniment_audit_log(
            db,
            accion=ACCOMPANIMENT_CYCLE_COMPLETED,
            project_id=project_id,
            client_id=client_id,
            payload={
                "final_state": target_state,
                "category_branch": branch,
            },
            usuario=usuario,
        )

    await _emit_sse_state_advanced(project_id, current_state, target_state, branch)

    return {
        "project_id": str(project_id),
        "from_state": current_state,
        "to_state": target_state,
        "category_branch": branch,
        "is_terminal": is_terminal_state(branch, target_state),
    }


async def upload_artifact(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    state: str,
    artifact_type: str,
    file_bytes: bytes,
    file_path: str,
    usuario: Optional[str] = None,
    artifact_metadata: Optional[dict] = None,
) -> dict:
    """Persist artifact upload · sha256 + size + audit_log emit.

    Caller responsible for actually writing file_bytes to file_path (storage
    layer concern). Service persists metadata + sha256 + emit audit_log.
    """
    await db.execute(sa_text(
        "SELECT pg_advisory_xact_lock(hashtext('accompaniment_' || :pid))"
    ), {"pid": str(project_id)})

    client_id, _ = await _resolve_project_meta(db, project_id)
    sha256_hex = hashlib.sha256(file_bytes).hexdigest()
    size_bytes = len(file_bytes)

    artifact_id = uuid.uuid4()
    await db.execute(sa_text(
        "INSERT INTO audit_accompaniment_artifacts "
        "(id, project_id, state, artifact_type, file_path, file_size_bytes, "
        "sha256, uploaded_by, uploaded_at, artifact_metadata, created_at) "
        "VALUES (:id, :pid, :st, :type, :path, :size, :sha, :usr, now(), :meta, now())"
    ), {
        "id": str(artifact_id),
        "pid": str(project_id),
        "st": state,
        "type": artifact_type,
        "path": file_path,
        "size": size_bytes,
        "sha": sha256_hex,
        "usr": usuario,
        "meta": json.dumps(artifact_metadata or {}),
    })

    await _emit_accompaniment_audit_log(
        db,
        accion=ACCOMPANIMENT_ARTIFACT_UPLOADED,
        project_id=project_id,
        client_id=client_id,
        payload={
            "artifact_id": str(artifact_id),
            "state": state,
            "artifact_type": artifact_type,
            "sha256": sha256_hex,
            "size_bytes": size_bytes,
        },
        usuario=usuario,
    )

    return {
        "artifact_id": str(artifact_id),
        "state": state,
        "artifact_type": artifact_type,
        "sha256": sha256_hex,
        "size_bytes": size_bytes,
    }


async def get_timeline(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> AccompanimentTimeline:
    """Return full timeline snapshot · current state + chronological transitions + artifacts."""
    _, categoria = await _resolve_project_meta(db, project_id)
    branch = resolve_category_branch(categoria)

    state_row = (await db.execute(sa_text(
        "SELECT current_state, category_branch, last_advanced_at "
        "FROM audit_accompaniment_state "
        "WHERE project_id = :pid AND deleted_at IS NULL"
    ), {"pid": str(project_id)})).first()

    if state_row is None:
        return AccompanimentTimeline(
            project_id=str(project_id),
            category_branch=branch,
            current_state=get_initial_state(branch),
            last_advanced_at=None,
            is_terminal=False,
            transitions=[],
            artifacts=[],
        )

    current_state = state_row[0]
    stored_branch = state_row[1]
    last_advanced_at = state_row[2]

    transition_rows = (await db.execute(sa_text(
        "SELECT from_state, to_state, advanced_by, advanced_at, transition_metadata "
        "FROM audit_accompaniment_transitions "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "ORDER BY advanced_at ASC"
    ), {"pid": str(project_id)})).all()

    transitions = [
        TimelineEntry(
            from_state=r[0],
            to_state=r[1],
            advanced_by=r[2],
            advanced_at=r[3].isoformat() if hasattr(r[3], "isoformat") else str(r[3]),
            transition_metadata=r[4] if isinstance(r[4], dict) else {},
        )
        for r in transition_rows
    ]

    artifact_rows = (await db.execute(sa_text(
        "SELECT id, state, artifact_type, file_path, file_size_bytes, "
        "sha256, uploaded_by, uploaded_at "
        "FROM audit_accompaniment_artifacts "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "ORDER BY uploaded_at ASC"
    ), {"pid": str(project_id)})).all()

    artifacts = [
        ArtifactEntry(
            id=str(r[0]),
            state=r[1],
            artifact_type=r[2],
            file_path=r[3],
            file_size_bytes=int(r[4]),
            sha256=r[5],
            uploaded_by=r[6],
            uploaded_at=r[7].isoformat() if hasattr(r[7], "isoformat") else str(r[7]),
        )
        for r in artifact_rows
    ]

    return AccompanimentTimeline(
        project_id=str(project_id),
        category_branch=stored_branch,
        current_state=current_state,
        last_advanced_at=(
            last_advanced_at.isoformat()
            if hasattr(last_advanced_at, "isoformat")
            else None
        ),
        is_terminal=is_terminal_state(stored_branch, current_state),
        transitions=transitions,
        artifacts=artifacts,
    )
