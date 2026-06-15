"""Engagement ofensivo (tier dedicado) · orquesta provisión + ejecución + teardown.

Conecta ``offensive_provisioner`` con el bucle de evidencia M8. FAIL-CLOSED: exige
autorización explícita (``authorized_by``) + atestación de un humano CUALIFICADO
(``attestor_cert``) ANTES de levantar o ejecutar nada (doc §2 · ADR-020). Sin eso
NO corre — ni un escaneo ofensivo autónomo sin autorización firmada.

Flujo: autorización → provisión box efímera → sesión firmada (scope_enforcer) →
ejecución de las tools del tier (vía mcp_client, scope-enforced) → candidatos →
findings canónicos (reusa process_and_persist) → TEARDOWN garantizado (finally) →
evidencia R6 (provisión + ejecución + atestación + destrucción).

Encuadre ENS (registrado como metadato auditable): para ALTA mp.s.3 esto es
verificación ofensiva SUPERVISADA; la prueba de penetración certificable requiere
pentester independiente del implantador. ``independence_note`` documenta esa
separación para el dossier ENAC.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m08_verification.autopilot.ephemeral_connector import (
    create_ephemeral_session,
    revoke_ephemeral_session,
)
from backend.app.motors.m08_verification.autopilot.offensive_provisioner import (
    OffensiveBox,
    provision_box,
    teardown_box,
)
from backend.app.motors.m08_verification.models import EvidenceRecord, VerificationRun
from backend.app.motors.m08_verification.normalization.adapters import (
    mcp_result_to_candidates,
)

logger = logging.getLogger(__name__)


class OffensiveAuthorizationError(Exception):
    """El engagement ofensivo no está autorizado/atestado · fail-closed."""


def _evidence(db, run, *, action, actor, payload, manifest):
    db.add(EvidenceRecord(
        project_id=run.project_id, client_id=None, run_id=run.id, finding_id=None,
        run_manifest_hash=manifest, actor=actor, action=action,
        component="m08:offensive.engagement", payload=payload,
    ))


async def run_offensive_engagement(
    db: AsyncSession,
    run_id: uuid.UUID | str,
    tier: str,
    *,
    authorized_by: str,
    attestor_cert: str,
    tool_invocations: list[dict[str, Any]],
    independence_note: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Ejecuta un engagement ofensivo del tier sobre el scope autorizado del run.

    ``tool_invocations``: lista de {"server","tool","args"} a ejecutar en la box.
    FAIL-CLOSED si falta autorización o atestación cualificada.
    """
    if not (authorized_by or "").strip():
        raise OffensiveAuthorizationError(
            "engagement ofensivo SIN authorized_by · no se levanta nada (ADR-020)"
        )
    if not (attestor_cert or "").strip():
        raise OffensiveAuthorizationError(
            "engagement ofensivo SIN atestación de humano cualificado (attestor_cert) · "
            "ENS ALTA mp.s.3 exige pentester cualificado · fail-closed"
        )

    now = now or datetime.now(timezone.utc)
    run = await db.get(VerificationRun, uuid.UUID(str(run_id)))
    if run is None:
        raise ValueError(f"VerificationRun {run_id} no existe")
    scope = run.scope_jsonb or {}

    # Sesión efímera firmada (misma garantía zero-standing-access + scope_enforcer).
    session = create_ephemeral_session(run, scope, now=now)
    manifest = run.run_manifest_hash

    box: OffensiveBox = await provision_box(tier, label=f"run-{run.id}")
    _evidence(
        db, run, action="offensive.box_provisioned", actor=f"authorized_by:{authorized_by}",
        manifest=manifest,
        payload={
            "tier": tier, "box_id": box.box_id, "status": box.status,
            "mock": box.mock, "host": box.host, "error": box.error,
            "attestor_cert": attestor_cert, "independence_note": independence_note,
            "boundary": "verificacion ofensiva SUPERVISADA · NO sustituye pentest independiente certificable (ENS ALTA mp.s.3)",
        },
    )

    candidates: list[dict] = []
    attempted: list[str] = []
    failed: list[str] = []
    try:
        if box.status in ("error",):
            failed.append(f"provision:{box.error}")
        else:
            import json as _json

            from backend.app.mcp_client import (
                pentest_authorization_context,
                try_invoke_mcp_or_none,
            )

            # §6 · auth/firma/run_id van por contextvar task-local (no os.environ
            # global · race). Las credenciales de la box ofensiva (env_overrides)
            # sí van por os.environ porque el hijo las hereda vía os.environ.copy()
            # (no son el token de scope compartido entre runs).
            prev_env = {k: os.environ.get(k) for k in box.env_overrides()}
            os.environ.update(box.env_overrides())
            try:
                with pentest_authorization_context(
                    _json.dumps(session["authorization"]),
                    session["signature"],
                    run_id=run.id,
                ):
                    for inv in tool_invocations:
                        server = inv.get("server", "")
                        tool = inv.get("tool", "")
                        args = inv.get("args", {}) or {}
                        label = f"{server}:{tool}"
                        attempted.append(label)
                        try:
                            resp = await try_invoke_mcp_or_none(
                                server=server, tool=tool, args=args,
                                timeout_seconds=1800,
                            )
                            cands = mcp_result_to_candidates(
                                resp, server=server, tool=tool,
                                target=str(args.get("target") or box.host or "offensive"),
                            )
                            candidates.extend(cands)
                        except Exception as exc:  # pragma: no cover — fail-soft
                            logger.warning("offensive %s falló: %s", label, exc)
                            failed.append(label)
            finally:
                # restaurar env de la box (no dejar credenciales colgando)
                for k, v in prev_env.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v

        # Persistir hallazgos en el bucle canónico (reusa el pipeline del autopilot).
        persisted = {"persisted": 0}
        if candidates:
            from backend.app.motors.m08_verification.autopilot.orchestrator import (
                process_and_persist,
            )
            persisted = await process_and_persist(db, run, candidates, enable_triage=False)

        _evidence(
            db, run, action="offensive.engagement_executed",
            actor=f"attestor:{attestor_cert}", manifest=manifest,
            payload={
                "tier": tier, "tools_attempted": attempted, "tools_failed": failed,
                "findings_persisted": persisted.get("persisted", 0),
                "authorized_by": authorized_by, "independence_note": independence_note,
            },
        )
        return {
            "run_id": str(run.id), "tier": tier, "box_id": box.box_id,
            "box_status": box.status, "mock": box.mock,
            "tools_attempted": attempted, "tools_failed": failed,
            "findings_persisted": persisted.get("persisted", 0),
        }
    finally:
        # TEARDOWN GARANTIZADO (zero standing access) + revocar sesión.
        await teardown_box(box)
        revoke_ephemeral_session(run, now=datetime.now(timezone.utc))
        _evidence(
            db, run, action="offensive.box_destroyed", actor="system",
            manifest=manifest,
            payload={"tier": tier, "box_id": box.box_id, "status": box.status,
                     "destroyed_at": box.destroyed_at.isoformat() if box.destroyed_at else None},
        )
        await db.flush()
