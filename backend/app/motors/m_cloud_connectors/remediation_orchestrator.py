"""Cloud Remediation Orchestrator · Bloque 3+5 v3.12.

Orquestador del workflow approval cloud remediation:
  admin propone gap → cliente aprueba/rechaza → admin ejecuta → marca executed/failed

State machine deterministic (ADR-031 ENAC-ready trazabilidad):

  detected
    └─ propose_to_cliente() ──→ proposed_to_cliente
                                  ├─ cliente_approve() ──→ approved
                                  │                          └─ start_execution() ──→ executing
                                  │                                                     ├─ mark_executed() ──→ executed
                                  │                                                     └─ mark_failed() ──→ failed
                                  └─ cliente_reject() ──→ rejected

Per transition:
  - UPDATE CloudGap.approval_status + timestamps
  - INSERT CloudRemediationApprovalLog row (audit trail inmutable)
  - DISPATCH SSE event audience-aware (admin/cliente)
  - GRACEFUL error: try/except outer · NUNCA bloquea state transition

ADR-014 read-only sostained · NO destructive cloud writes (admin/cliente manual
ejecución externa · orchestrator solo trackea state + logs).

R1 INVIOLABLE · pure state machine deterministic · NO LLM decisiones approval.
R23 sostener · project_id RLS enforced via context.
R29 firmísimo cliente · friendly notes opcional · NO presión coercitiva.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.motors.m_cloud_connectors.models import (
    CloudGap,
    CloudRemediationActorType,
    CloudRemediationApprovalLog,
    CloudRemediationApprovalStatus,
    CloudRemediationFailureCategory,
    CloudRemediationLogAction,
)


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Exceptions


class RemediationError(Exception):
    """Base · remediation orchestrator errors."""


class GapNotFoundError(RemediationError):
    """CloudGap NO existe (e.g. project_id mismatch RLS)."""


class InvalidTransitionError(RemediationError):
    """State transition NO permitida (e.g. cliente_approve sobre 'detected')."""


class DuplicateLogError(RemediationError):
    """Idempotency violation · log con mismo (gap_id+action+key) ya existe."""


# ──────────────────────────────────────────────────────────────────────
# State machine transitions allowed


_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    CloudRemediationApprovalStatus.DETECTED.value: {
        CloudRemediationApprovalStatus.PROPOSED_TO_CLIENTE.value,
    },
    CloudRemediationApprovalStatus.PROPOSED_TO_CLIENTE.value: {
        CloudRemediationApprovalStatus.APPROVED.value,
        CloudRemediationApprovalStatus.REJECTED.value,
    },
    CloudRemediationApprovalStatus.APPROVED.value: {
        CloudRemediationApprovalStatus.EXECUTING.value,
    },
    CloudRemediationApprovalStatus.EXECUTING.value: {
        CloudRemediationApprovalStatus.EXECUTED.value,
        CloudRemediationApprovalStatus.FAILED.value,
    },
    # Phase A Enhancement · EXECUTED → VERIFICATION_PENDING (auto) →
    # VERIFIED (admin reports) OR back to EXECUTING (admin re-corrects)
    CloudRemediationApprovalStatus.EXECUTED.value: {
        CloudRemediationApprovalStatus.VERIFICATION_PENDING.value,
        # Legacy: si admin NO usa verification flow · EXECUTED terminal sostained
    },
    CloudRemediationApprovalStatus.VERIFICATION_PENDING.value: {
        CloudRemediationApprovalStatus.VERIFIED.value,
        CloudRemediationApprovalStatus.EXECUTING.value,  # re-correct path
    },
    # Terminal states · NO transitions out
    CloudRemediationApprovalStatus.REJECTED.value: set(),
    CloudRemediationApprovalStatus.VERIFIED.value: set(),
    CloudRemediationApprovalStatus.FAILED.value: set(),
}


# ──────────────────────────────────────────────────────────────────────
# Idempotency · Phase A Enhancement


def compute_idempotency_key(
    gap_id: uuid.UUID,
    action: str,
    pre_state: str,
    extra: str | None = None,
) -> str:
    """Deterministic idempotency key SHA-256 of (gap_id + action + pre_state + extra).

    Same (gap_id, action, pre_state) tuple genera same key · UNIQUE constraint
    en DB rejecta duplicate INSERT cuando admin double-clicks o retry.

    Caller puede pasar `extra` (e.g. timestamp granularity) si NEED distinct
    keys per minute-bucket etc.
    """
    parts = [str(gap_id), action, pre_state]
    if extra:
        parts.append(extra)
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:64]  # Keep within VARCHAR(128) safe


def _can_transition(from_status: str, to_status: str) -> bool:
    """Pure function · valida transición permitida state machine."""
    allowed = _ALLOWED_TRANSITIONS.get(from_status, set())
    return to_status in allowed


# ──────────────────────────────────────────────────────────────────────
# Orchestrator service


class CloudRemediationOrchestrator:
    """Orquestador del workflow approval cloud remediation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ──────────────────────────────────────────────────────────────────
    # State transitions

    async def propose_to_cliente(
        self,
        gap_id: uuid.UUID,
        admin_user_id: uuid.UUID | None,
        notes: str | None = None,
    ) -> CloudGap:
        """Admin dispara propuesta hacia cliente portal.

        Transition: detected → proposed_to_cliente
        """
        gap = await self._load_gap_or_raise(gap_id)
        self._assert_can_transition(
            gap, CloudRemediationApprovalStatus.PROPOSED_TO_CLIENTE.value,
        )

        now = datetime.now(timezone.utc)
        gap.approval_status = CloudRemediationApprovalStatus.PROPOSED_TO_CLIENTE.value
        gap.proposed_to_cliente_at = now

        await self._record_log(
            gap=gap,
            action=CloudRemediationLogAction.PROPOSED_TO_CLIENTE.value,
            actor_user_id=admin_user_id,
            actor_type=CloudRemediationActorType.ADMIN.value,
            notes=notes,
        )
        await self.db.flush()

        await self._maybe_dispatch_sse(
            gap=gap,
            event_type="cloud_remediation_proposed",
            audience="cliente",
        )
        return gap

    async def cliente_approve(
        self,
        gap_id: uuid.UUID,
        cliente_user_id: uuid.UUID | None,
        notes: str | None = None,
    ) -> CloudGap:
        """Cliente aprueba propuesta.

        Transition: proposed_to_cliente → approved
        """
        gap = await self._load_gap_or_raise(gap_id)
        self._assert_can_transition(
            gap, CloudRemediationApprovalStatus.APPROVED.value,
        )

        now = datetime.now(timezone.utc)
        gap.approval_status = CloudRemediationApprovalStatus.APPROVED.value
        gap.cliente_approval_at = now
        gap.cliente_approval_user_id = cliente_user_id

        await self._record_log(
            gap=gap,
            action=CloudRemediationLogAction.CLIENTE_APPROVED.value,
            actor_user_id=cliente_user_id,
            actor_type=CloudRemediationActorType.CLIENTE.value,
            notes=notes,
        )
        await self.db.flush()

        await self._maybe_dispatch_sse(
            gap=gap,
            event_type="cloud_remediation_approved",
            audience="admin",
        )
        return gap

    async def cliente_reject(
        self,
        gap_id: uuid.UUID,
        cliente_user_id: uuid.UUID | None,
        notes: str | None = None,
    ) -> CloudGap:
        """Cliente rechaza propuesta · estado terminal.

        Transition: proposed_to_cliente → rejected
        """
        gap = await self._load_gap_or_raise(gap_id)
        self._assert_can_transition(
            gap, CloudRemediationApprovalStatus.REJECTED.value,
        )

        now = datetime.now(timezone.utc)
        gap.approval_status = CloudRemediationApprovalStatus.REJECTED.value
        gap.cliente_approval_at = now
        gap.cliente_approval_user_id = cliente_user_id

        await self._record_log(
            gap=gap,
            action=CloudRemediationLogAction.CLIENTE_REJECTED.value,
            actor_user_id=cliente_user_id,
            actor_type=CloudRemediationActorType.CLIENTE.value,
            notes=notes,
        )
        await self.db.flush()

        await self._maybe_dispatch_sse(
            gap=gap,
            event_type="cloud_remediation_rejected",
            audience="admin",
        )
        return gap

    async def start_execution(
        self,
        gap_id: uuid.UUID,
        admin_user_id: uuid.UUID | None,
        notes: str | None = None,
    ) -> CloudGap:
        """Admin inicia ejecución remediation post-approval cliente.

        Transition: approved → executing
        """
        gap = await self._load_gap_or_raise(gap_id)
        self._assert_can_transition(
            gap, CloudRemediationApprovalStatus.EXECUTING.value,
        )

        gap.approval_status = CloudRemediationApprovalStatus.EXECUTING.value

        await self._record_log(
            gap=gap,
            action=CloudRemediationLogAction.EXECUTING.value,
            actor_user_id=admin_user_id,
            actor_type=CloudRemediationActorType.ADMIN.value,
            notes=notes,
        )
        await self.db.flush()

        await self._maybe_dispatch_sse(
            gap=gap,
            event_type="cloud_remediation_executing",
            audience="cliente",
        )
        return gap

    async def mark_executed(
        self,
        gap_id: uuid.UUID,
        admin_user_id: uuid.UUID | None,
        evidence_link_id: uuid.UUID | None = None,
        notes: str | None = None,
        correlation_id: uuid.UUID | None = None,
        auto_enter_verification: bool = False,
    ) -> CloudGap:
        """Admin marca executed · gap resuelto.

        Transition: executing → executed · sets resolved_at + evidence_link_id.

        Phase A Enhancement opt-in: si ``auto_enter_verification=True``
        gap automatically transitions executed → verification_pending para
        admin reporte verify success (sostiene 3-point commitment ADR-014
        read-only · admin manually verified cloud action externa).

        Default False preserva backward compat orchestrator direct callers
        (tests existing). API endpoint passes True para production infallibility
        flow.
        """
        gap = await self._load_gap_or_raise(gap_id)
        self._assert_can_transition(
            gap, CloudRemediationApprovalStatus.EXECUTED.value,
        )

        pre_state = gap.approval_status
        now = datetime.now(timezone.utc)
        gap.approval_status = CloudRemediationApprovalStatus.EXECUTED.value
        gap.resolved_at = now
        gap.resolved_by_user_id = admin_user_id
        if evidence_link_id is not None:
            gap.evidence_link_id = evidence_link_id
        if notes:
            gap.resolution_note = notes

        idempotency_key = compute_idempotency_key(
            gap_id, CloudRemediationLogAction.EXECUTED.value, pre_state,
        )
        await self._record_log(
            gap=gap,
            action=CloudRemediationLogAction.EXECUTED.value,
            actor_user_id=admin_user_id,
            actor_type=CloudRemediationActorType.ADMIN.value,
            notes=notes,
            metadata={
                "evidence_link_id": (
                    str(evidence_link_id) if evidence_link_id else None
                ),
                "pre_state": pre_state,
                "post_state": CloudRemediationApprovalStatus.EXECUTED.value,
            },
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        await self.db.flush()

        await self._maybe_dispatch_sse(
            gap=gap,
            event_type="cloud_remediation_executed",
            audience="cliente",
        )

        # Phase A Enhancement · auto-enter verification_pending state
        if auto_enter_verification:
            await self._auto_transition_to_verification_pending(
                gap, admin_user_id, correlation_id=correlation_id,
            )

        return gap

    async def _auto_transition_to_verification_pending(
        self,
        gap: CloudGap,
        admin_user_id: uuid.UUID | None,
        correlation_id: uuid.UUID | None = None,
    ) -> None:
        """Internal · auto-transition executed → verification_pending Phase A."""
        pre_state = gap.approval_status
        now = datetime.now(timezone.utc)
        gap.approval_status = CloudRemediationApprovalStatus.VERIFICATION_PENDING.value
        gap.verification_pending_at = now

        idempotency_key = compute_idempotency_key(
            gap.id,
            CloudRemediationLogAction.VERIFICATION_PENDING.value,
            pre_state,
        )
        await self._record_log(
            gap=gap,
            action=CloudRemediationLogAction.VERIFICATION_PENDING.value,
            actor_user_id=admin_user_id,
            actor_type=CloudRemediationActorType.SYSTEM.value,
            notes="Auto-transition post mark_executed · awaiting admin verify report",
            metadata={
                "pre_state": pre_state,
                "post_state": CloudRemediationApprovalStatus.VERIFICATION_PENDING.value,
                "auto_transition": True,
            },
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        await self.db.flush()

        await self._maybe_dispatch_sse(
            gap=gap,
            event_type="cloud_remediation_verification_pending",
            audience="admin",
        )

    async def mark_verified(
        self,
        gap_id: uuid.UUID,
        admin_user_id: uuid.UUID | None,
        notes: str | None = None,
        correlation_id: uuid.UUID | None = None,
    ) -> CloudGap:
        """Admin reporta verify success post-execute · estado terminal VERIFIED.

        Phase A Enhancement · Transition: verification_pending → verified.

        Admin manually verifica cloud action externa successful (e.g. consultó
        cloud console · confirmó configuration desired aplicada) · marca aquí.

        Esta transición dispara cross-system propagation Phase B (CloudGap
        status update + m_compliance recheck + dossier evidence + adenda trigger
        + notifications cross-stakeholders).
        """
        gap = await self._load_gap_or_raise(gap_id)
        self._assert_can_transition(
            gap, CloudRemediationApprovalStatus.VERIFIED.value,
        )

        pre_state = gap.approval_status
        now = datetime.now(timezone.utc)
        gap.approval_status = CloudRemediationApprovalStatus.VERIFIED.value
        gap.verified_at = now
        gap.verified_by_user_id = admin_user_id

        idempotency_key = compute_idempotency_key(
            gap_id, CloudRemediationLogAction.VERIFIED.value, pre_state,
        )
        await self._record_log(
            gap=gap,
            action=CloudRemediationLogAction.VERIFIED.value,
            actor_user_id=admin_user_id,
            actor_type=CloudRemediationActorType.ADMIN.value,
            notes=notes,
            metadata={
                "pre_state": pre_state,
                "post_state": CloudRemediationApprovalStatus.VERIFIED.value,
                "friendly_message": (
                    "Marcos confirmó que la solución funciona correctamente. "
                    "Tu sistema está más seguro."
                ),
            },
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        await self.db.flush()

        await self._maybe_dispatch_sse(
            gap=gap,
            event_type="cloud_remediation_verified",
            audience="cliente",
        )

        # Phase B cross-system propagation hook (graceful · NUNCA bloquea)
        await self._maybe_dispatch_system_consciousness(
            gap=gap, correlation_id=correlation_id, admin_user_id=admin_user_id,
        )

        return gap

    async def request_rollback(
        self,
        gap_id: uuid.UUID,
        admin_user_id: uuid.UUID | None,
        reason: str,
        correlation_id: uuid.UUID | None = None,
    ) -> CloudGap:
        """Admin solicita rollback post verification fail · transition back to executing.

        Phase A Enhancement · admin reports verification failed (cloud state
        NO matches desired) · re-enters EXECUTING para correction manual.

        Sostiene ADR-014 read-only · NO automated rollback API call cloud ·
        admin manually rollback cloud action + re-execute.
        """
        gap = await self._load_gap_or_raise(gap_id)
        self._assert_can_transition(
            gap, CloudRemediationApprovalStatus.EXECUTING.value,
        )

        pre_state = gap.approval_status
        gap.approval_status = CloudRemediationApprovalStatus.EXECUTING.value
        gap.verification_pending_at = None  # reset · admin re-execute

        idempotency_key = compute_idempotency_key(
            gap_id, CloudRemediationLogAction.ROLLBACK_REQUESTED.value, pre_state,
        )
        await self._record_log(
            gap=gap,
            action=CloudRemediationLogAction.ROLLBACK_REQUESTED.value,
            actor_user_id=admin_user_id,
            actor_type=CloudRemediationActorType.ADMIN.value,
            notes=reason,
            metadata={
                "pre_state": pre_state,
                "post_state": CloudRemediationApprovalStatus.EXECUTING.value,
                "rollback_reason": reason,
                "friendly_message": (
                    "Marcos detectó algo en la verificación · está revisando "
                    "el sistema. Sin prisa por tu parte."
                ),
            },
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        await self.db.flush()

        await self._maybe_dispatch_sse(
            gap=gap,
            event_type="cloud_remediation_rollback_requested",
            audience="admin",
        )
        return gap

    async def mark_failed(
        self,
        gap_id: uuid.UUID,
        admin_user_id: uuid.UUID | None,
        error_notes: str,
        error_metadata: dict | None = None,
        failure_category: str | None = None,
        correlation_id: uuid.UUID | None = None,
    ) -> CloudGap:
        """Admin marca failed durante ejecución · estado terminal.

        Transition: executing → failed.

        Phase A Enhancement · ``failure_category`` obligatorio enums
        CloudRemediationFailureCategory (transient · permanent · partial · unknown)
        + ``error_metadata`` structured (stack trace · cloud API response · context).
        """
        gap = await self._load_gap_or_raise(gap_id)
        self._assert_can_transition(
            gap, CloudRemediationApprovalStatus.FAILED.value,
        )

        pre_state = gap.approval_status
        gap.approval_status = CloudRemediationApprovalStatus.FAILED.value

        # Phase A Enhancement · validate failure_category
        category = failure_category or CloudRemediationFailureCategory.UNKNOWN.value
        valid_categories = {c.value for c in CloudRemediationFailureCategory}
        if category not in valid_categories:
            logger.warning(
                "mark_failed received invalid failure_category=%s · falling back to unknown",
                category,
            )
            category = CloudRemediationFailureCategory.UNKNOWN.value

        # Friendly cliente message R29 (NO presión · empático)
        friendly_message = (
            "Marcos encontró un problema aplicando la solución. "
            "Ya lo está revisando · te avisaremos cuando esté listo. "
            "Sin prisa por tu parte."
        )

        merged_metadata: dict[str, Any] = {
            "pre_state": pre_state,
            "post_state": CloudRemediationApprovalStatus.FAILED.value,
            "failure_category": category,
            "friendly_message": friendly_message,
        }
        if error_metadata:
            merged_metadata.update(error_metadata)

        idempotency_key = compute_idempotency_key(
            gap_id, CloudRemediationLogAction.FAILED.value, pre_state,
        )
        await self._record_log(
            gap=gap,
            action=CloudRemediationLogAction.FAILED.value,
            actor_user_id=admin_user_id,
            actor_type=CloudRemediationActorType.ADMIN.value,
            notes=error_notes,
            metadata=merged_metadata,
            failure_category=category,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        await self.db.flush()

        await self._maybe_dispatch_sse(
            gap=gap,
            event_type="cloud_remediation_failed",
            audience="cliente",
        )
        return gap

    # ──────────────────────────────────────────────────────────────────
    # Phase B cross-system consciousness hook (stub Phase A · wired Phase B)

    async def _maybe_dispatch_system_consciousness(
        self,
        *,
        gap: CloudGap,
        correlation_id: uuid.UUID | None,
        admin_user_id: uuid.UUID | None,
    ) -> None:
        """Phase B hook · dispatch cross-system propagation post VERIFIED.

        Graceful pattern reuse M14 workflow_hooks._maybe_dispatch_X · NUNCA
        bloquea state transition. Implemented Phase B sub-atom.

        Stub Phase A · NO wired yet. Future Phase B wires:
        - CloudGap.status update derived view
        - m_compliance_monitor recheck trigger
        - M9 Dossier evidence auto-add
        - M14 AdendaGenerator trigger si material change
        - Dashboards SSE refresh
        - Notifications cross-stakeholders
        """
        try:
            from backend.app.motors.m_cloud_connectors.system_consciousness_hooks import (
                maybe_dispatch_remediation_verified,
            )
        except ImportError:
            logger.debug(
                "system_consciousness_hooks NOT available (Phase B not yet implemented) · gap=%s",
                gap.id,
            )
            return

        try:
            await maybe_dispatch_remediation_verified(
                db=self.db,
                gap=gap,
                admin_user_id=admin_user_id,
                correlation_id=correlation_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "system_consciousness hook failed (gap=%s) · %s · primary VERIFIED OK",
                gap.id, exc,
            )

    # ──────────────────────────────────────────────────────────────────
    # Audit trail queries

    async def list_audit_logs(
        self, gap_id: uuid.UUID,
    ) -> list[CloudRemediationApprovalLog]:
        """List todos los audit logs per gap (ENAC trazabilidad)."""
        result = await self.db.execute(
            select(CloudRemediationApprovalLog)
            .where(CloudRemediationApprovalLog.gap_id == gap_id)
            .order_by(CloudRemediationApprovalLog.created_at.asc())
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────────────────────────────
    # Internals

    async def _load_gap_or_raise(self, gap_id: uuid.UUID) -> CloudGap:
        gap = await self.db.get(CloudGap, gap_id)
        if gap is None:
            raise GapNotFoundError(f"CloudGap {gap_id} not found")
        return gap

    def _assert_can_transition(
        self, gap: CloudGap, target_status: str,
    ) -> None:
        if not _can_transition(gap.approval_status, target_status):
            raise InvalidTransitionError(
                f"Cannot transition CloudGap {gap.id} from "
                f"{gap.approval_status} to {target_status}",
            )

    async def _record_log(
        self,
        *,
        gap: CloudGap,
        action: str,
        actor_user_id: uuid.UUID | None,
        actor_type: str,
        notes: str | None = None,
        metadata: dict | None = None,
        idempotency_key: str | None = None,
        failure_category: str | None = None,
        correlation_id: uuid.UUID | None = None,
    ) -> CloudRemediationApprovalLog:
        """Persist audit log row · Phase A Enhancement con idempotency.

        Si ``idempotency_key`` provided · UNIQUE constraint (gap_id+action+key)
        previene duplicate INSERTs. Catch IntegrityError → return existing log
        (idempotent operation).
        """
        # Phase A Enhancement · idempotency check pre-insert (optimistic)
        if idempotency_key:
            existing = await self.db.execute(
                select(CloudRemediationApprovalLog)
                .where(
                    CloudRemediationApprovalLog.gap_id == gap.id,
                    CloudRemediationApprovalLog.action == action,
                    CloudRemediationApprovalLog.idempotency_key == idempotency_key,
                )
                .limit(1)
            )
            existing_row = existing.scalar_one_or_none()
            if existing_row is not None:
                logger.info(
                    "Idempotent log skip · gap=%s action=%s key=%s",
                    gap.id, action, idempotency_key[:16],
                )
                return existing_row

        log_row = CloudRemediationApprovalLog(
            gap_id=gap.id,
            project_id=gap.project_id,
            action=action,
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            notes=notes,
            metadata_jsonb=metadata,
            idempotency_key=idempotency_key,
            failure_category=failure_category,
            correlation_id=correlation_id,
        )
        try:
            # FIX: SAVEPOINT (begin_nested) en vez de rollback() global. Antes,
            # ante una carrera concurrente que viola la UNIQUE de idempotencia, el
            # rollback() revertía TODA la transacción —incluida la transición de
            # gap.approval_status ya aplicada en esta misma transacción— y el
            # endpoint hacía commit sobre una sesión revertida → incoherencia
            # entre lo que devolvía la API y lo persistido. El savepoint revierte
            # SOLO el INSERT del log y preserva la mutación de estado del gap.
            async with self.db.begin_nested():
                self.db.add(log_row)
                await self.db.flush()
        except IntegrityError as exc:
            # Concurrent INSERT raced · el savepoint ya revirtió SOLO el log ·
            # re-fetch existing (la transición del gap sigue viva en la transacción)
            logger.warning(
                "IntegrityError on log INSERT · gap=%s action=%s · re-fetching existing",
                gap.id, action,
            )
            if idempotency_key:
                existing = await self.db.execute(
                    select(CloudRemediationApprovalLog)
                    .where(
                        CloudRemediationApprovalLog.gap_id == gap.id,
                        CloudRemediationApprovalLog.action == action,
                        CloudRemediationApprovalLog.idempotency_key == idempotency_key,
                    )
                    .limit(1)
                )
                existing_row = existing.scalar_one_or_none()
                if existing_row is not None:
                    return existing_row
            raise DuplicateLogError(
                f"Failed to record log gap={gap.id} action={action}",
            ) from exc
        return log_row

    async def _maybe_dispatch_sse(
        self,
        *,
        gap: CloudGap,
        event_type: str,
        audience: str,
    ) -> None:
        """Graceful SSE dispatch · NUNCA bloquea state transition.

        Audience-aware audience filtering pattern reuse 1.D.G EXPANDED:
          - admin events: filter audience admin
          - cliente events: filter audience cliente
        """
        try:
            await sse_dispatcher.dispatch(
                channel=f"project:{gap.project_id}",
                event_type=event_type,
                data={
                    "gap_id": str(gap.id),
                    "approval_status": gap.approval_status,
                    "ens_measure_code": gap.ens_measure_code,
                    "severity": gap.severity,
                    "title": gap.title,
                    "audience": audience,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "SSE dispatch failed · gap=%s event=%s err=%s",
                gap.id, event_type, exc,
            )
