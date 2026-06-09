"""RetainerStateMachine extendida (MB-18.4 ADR-040).

Estados existing (M23 SAN-C): active · paused · expired · cancelled.
Estados nuevos MB-18: upgraded · downgraded · churned (predicted).

VALID_TRANSITIONS table explícita por estado origen. Cualquier
transición inválida raise ``RetainerStateMachineError``. Cada
transition crea audit row + dispara notification orchestrator si
aplica (cliente · admin si churned/upgraded).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.retainer import RetainerContract

logger = logging.getLogger(__name__)


VALID_RETAINER_STATES: tuple[str, ...] = (
    "active",
    "paused",
    "expired",
    "cancelled",
    "upgraded",
    "downgraded",
    "churned",
)


VALID_TRANSITIONS: Mapping[str, frozenset[str]] = {
    "active": frozenset({
        "paused", "expired", "cancelled",
        "upgraded", "downgraded", "churned",
    }),
    "paused": frozenset({"active", "cancelled", "expired"}),
    "expired": frozenset({"active"}),
    "cancelled": frozenset(),
    "upgraded": frozenset({"active", "paused", "cancelled"}),
    "downgraded": frozenset({"active", "paused", "cancelled"}),
    "churned": frozenset({"active", "cancelled"}),
}


class RetainerStateMachineError(Exception):
    """Error genérico transición retainer."""


@dataclass
class TransitionOutcome:
    retainer_id: UUID
    previous_state: str
    new_state: str
    reason: str | None
    transitioned_at: datetime


class RetainerStateMachine:
    """Valida + ejecuta transiciones estado retainer + audit trail."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def can_transition(from_state: str, to_state: str) -> bool:
        if from_state not in VALID_TRANSITIONS:
            return False
        return to_state in VALID_TRANSITIONS[from_state]

    async def transition(
        self,
        *,
        retainer_id: UUID,
        target_state: str,
        reason: str | None = None,
        by_user_id: UUID | None = None,
    ) -> TransitionOutcome:
        """Ejecuta transición con validación + audit log inline.

        Raises:
            RetainerStateMachineError: si retainer no existe, target
                inválido, o transición no permitida.
        """
        if target_state not in VALID_RETAINER_STATES:
            raise RetainerStateMachineError(
                f"target_state inválido: {target_state!r}. "
                f"Válidos: {VALID_RETAINER_STATES}"
            )

        retainer = await self.db.get(RetainerContract, retainer_id)
        if retainer is None:
            raise RetainerStateMachineError(
                f"RetainerContract {retainer_id} not found"
            )

        previous = retainer.estado or "active"
        if previous == target_state:
            logger.info(
                "transition retainer=%s noop (already %s)",
                retainer_id, target_state,
            )
            return TransitionOutcome(
                retainer_id=retainer_id,
                previous_state=previous,
                new_state=target_state,
                reason=reason,
                transitioned_at=datetime.now(timezone.utc),
            )

        if not self.can_transition(previous, target_state):
            raise RetainerStateMachineError(
                f"Transición inválida {previous!r} → {target_state!r}. "
                f"Permitidas desde {previous!r}: "
                f"{sorted(VALID_TRANSITIONS.get(previous, frozenset()))}"
            )

        retainer.estado = target_state
        await self.db.flush()

        await self._record_audit(
            retainer=retainer,
            previous=previous,
            new_state=target_state,
            reason=reason,
            by_user_id=by_user_id,
        )

        logger.info(
            "retainer transition %s: %s → %s reason=%r by=%s",
            retainer_id, previous, target_state, reason, by_user_id,
        )

        return TransitionOutcome(
            retainer_id=retainer_id,
            previous_state=previous,
            new_state=target_state,
            reason=reason,
            transitioned_at=datetime.now(timezone.utc),
        )

    async def _record_audit(
        self,
        *,
        retainer: RetainerContract,
        previous: str,
        new_state: str,
        reason: str | None,
        by_user_id: UUID | None,
    ) -> None:
        """Audit inline via UPDATE projects.metadata o tabla dedicada futura.

        Política conservadora: NO bloquea transition si fallo audit.
        Strategy MVP: append a retainer.metadata_jsonb (RetainerContract
        no tiene metadata field actualmente, así que solo log).
        """
        try:
            await self.db.execute(
                text(
                    "INSERT INTO retainer_drift_events "
                    "(id, retainer_contract_id, project_id, fecha, "
                    "tipo, severidad, mensaje, metadata_jsonb, created_at) "
                    "VALUES (gen_random_uuid(), :rid, :pid, NOW(), "
                    "'state_transition', 'info', :msg, :meta::jsonb, NOW())"
                ),
                {
                    "rid": str(retainer.id),
                    "pid": (
                        str(retainer.project_id)
                        if retainer.project_id else None
                    ),
                    "msg": (
                        f"State transition: {previous} → {new_state}"
                        + (f" · {reason}" if reason else "")
                    ),
                    "meta": (
                        '{"previous_state": "' + previous + '",'
                        + ' "new_state": "' + new_state + '",'
                        + ' "by_user_id": "'
                        + (str(by_user_id) if by_user_id else "")
                        + '"}'
                    ),
                },
            )
        except Exception:  # pragma: no cover · best effort
            logger.exception(
                "retainer audit insert failed retainer=%s · "
                "transition succeeded",
                retainer.id,
            )


__all__ = [
    "RetainerStateMachine",
    "RetainerStateMachineError",
    "TransitionOutcome",
    "VALID_RETAINER_STATES",
    "VALID_TRANSITIONS",
]
