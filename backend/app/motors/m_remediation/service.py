"""Motor de orquestación de remediación · m_remediation (ADR-055).

Ciclo seguro idéntico para cloud y host:

    preflight (read_state)              ──→ si ya cumple → SKIPPED_COMPLIANT
        └─ snapshot (state_before)
            └─ [dry_run] → SUCCEEDED (no aplica)
            └─ apply
                └─ verify (read_state)  ──→ cumple → SUCCEEDED
                                        ──→ no cumple/excepción → rollback → ROLLED_BACK
                                        ──→ rollback falla → FAILED

Garantías:
  - Determinista (R1): el tier y el modo se resuelven del catálogo + política,
    nunca de un LLM.
  - Kill-switch revalidado EN EJECUCIÓN (defensa en profundidad · no solo al crear).
  - Idempotente: preflight evita reaplicar lo ya cumplido.
  - Reversible: snapshot previo + rollback automático si la verificación falla.
  - Auditado (R6): cada transición → audit_log (writer central · hash chain).
  - Default seguro: sin writer configurado → FAILED explícito, jamás falso éxito.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit_writer import emit_audit_log
from backend.app.motors.m_cloud_connectors.models import CloudConnector
from backend.app.motors.m_remediation.catalog import get_action_spec
from backend.app.motors.m_remediation.models import (
    TERMINAL_JOB_STATES,
    RemediationJob,
    RemediationJobStatus,
    RemediationSnapshot,
    RemediationSourceKind,
)
from backend.app.motors.m_remediation.policy import (
    AutoRemediationPolicy,
    ExecutionMode,
    resolve_execution_mode,
)
from backend.app.motors.m_remediation.writers import (
    RemediationWriter,
    WriterNotConfigured,
    get_writer,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Excepciones


class RemediationServiceError(Exception):
    """Base."""


class JobNotFoundError(RemediationServiceError):
    pass


class AuthorizationRequiredError(RemediationServiceError):
    """Job GUARDED sin autorización previa · no se puede ejecutar."""


class RemediationDisabledError(RemediationServiceError):
    """Kill-switch/política deja la acción como plan · no se aplica."""


class InvalidJobTransitionError(RemediationServiceError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────
# Servicio


class RemediationService:
    """Orquestador del ciclo de remediación seguro."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── creación ────────────────────────────────────────────────────────

    async def create_job(
        self,
        *,
        project_id: uuid.UUID,
        action_type: str,
        source_kind: str | RemediationSourceKind,
        source_gap_id: uuid.UUID | None = None,
        source_finding_id: uuid.UUID | None = None,
        connector_id: uuid.UUID | None = None,
        agent_id: uuid.UUID | None = None,
        target_ref: str | None = None,
        params: dict | None = None,
        created_by_user_id: uuid.UUID | None = None,
        client_id: uuid.UUID | None = None,
        dry_run: bool = False,
    ) -> RemediationJob:
        """Crea un job · clasifica tier (catálogo) + estado inicial (política)."""
        spec = get_action_spec(action_type)
        if spec is None:
            raise RemediationServiceError(f"Acción no catalogada: {action_type}")

        kind = (
            source_kind.value
            if isinstance(source_kind, RemediationSourceKind)
            else source_kind
        )

        target_enabled, policy = await self._resolve_target_flags(
            connector_id=connector_id, agent_id=agent_id,
        )
        mode = resolve_execution_mode(
            action_type, target_enabled=target_enabled, policy=policy,
        )
        initial_status = {
            ExecutionMode.BLOCKED: RemediationJobStatus.BLOCKED.value,
            ExecutionMode.REQUIRE_AUTHORIZATION: (
                RemediationJobStatus.AWAITING_AUTHORIZATION.value
            ),
            ExecutionMode.AUTO: RemediationJobStatus.QUEUED.value,
            # DISABLED → queda como plan (queued); execute_job lo rechazará.
            ExecutionMode.DISABLED: RemediationJobStatus.QUEUED.value,
        }[mode]

        job = RemediationJob(
            project_id=project_id,
            client_id=client_id,
            source_kind=kind,
            source_gap_id=source_gap_id,
            source_finding_id=source_finding_id,
            connector_id=connector_id,
            agent_id=agent_id,
            action_type=action_type,
            tier=spec.tier.value,
            status=initial_status,
            target_ref=target_ref,
            params=params,
            dry_run=dry_run,
            created_by_user_id=created_by_user_id,
        )
        self.db.add(job)
        await self.db.flush()
        await self._audit(job, "remediation.created")
        return job

    # ── autorización previa (GUARDED) ─────────────────────────────────────

    async def authorize_job(
        self, job_id: uuid.UUID, *, user_id: uuid.UUID | None,
    ) -> RemediationJob:
        """Concede la autorización previa para un job GUARDED."""
        job = await self._load_job(job_id)
        if job.status != RemediationJobStatus.AWAITING_AUTHORIZATION.value:
            raise InvalidJobTransitionError(
                f"Job {job_id} en estado {job.status}; no requiere autorización.",
            )
        job.authorized_by_user_id = user_id
        job.authorized_at = _now()
        job.status = RemediationJobStatus.QUEUED.value
        await self.db.flush()
        await self._audit(job, "remediation.authorized")
        return job

    async def approve_and_execute_job(
        self,
        job_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None,
        writer: "RemediationWriter | None" = None,
    ) -> RemediationJob:
        """FASE 4 · un solo clic 'aprobar y ejecutar'.

        Autoriza el job si está AWAITING_AUTHORIZATION (GUARDED) y a continuación
        dispara el ciclo seguro. Para SAFE_AUTO (QUEUED) ejecuta directo. Nada se
        ejecuta sin esta acción humana explícita (decisión Marcos · proponer→aprobar
        →ejecutar). Idempotente sobre estados terminales (execute_job)."""
        job = await self._load_job(job_id)
        if job.status == RemediationJobStatus.AWAITING_AUTHORIZATION.value:
            await self.authorize_job(job_id, user_id=user_id)
        return await self.execute_job(job_id, writer=writer)

    # ── ejecución (el corazón) ─────────────────────────────────────────────

    async def execute_job(
        self,
        job_id: uuid.UUID,
        *,
        writer: RemediationWriter | None = None,
        chain_retest: bool = True,
    ) -> RemediationJob:
        """Ejecuta el ciclo seguro y (IMPL-5) encadena el retest quirúrgico.

        Tras una remediación que deja el activo en el estado deseado (SUCCEEDED o
        SKIPPED_COMPLIANT) y que provenía de un hallazgo de pentest (m08), dispara
        el re-test determinista que vuelve a comprobar SOLO ese hallazgo y, si está
        resuelto, lo cierra (CLOSED) con evidencia R6 inmutable — cerrando el bucle
        diagnóstico→remediación→verificación que certifica el auditor ENAC.
        Idempotente sobre estados terminales."""
        job = await self._execute_cycle(job_id, writer=writer)
        if chain_retest:
            await self._maybe_chain_retest(job)
        return job

    async def _maybe_chain_retest(self, job: RemediationJob) -> None:
        """IMPL-5 · re-test encadenado best-effort del finding origen.

        Solo aplica si el job (a) dejó el activo conforme y (b) provino de un
        finding de m08. En entornos sin escáneres instalados el retest registra
        traza 'error/inconclusive' SIN cerrar falsamente el finding (honesto · el
        cierre real ocurre en Hetzner con MCP/escáneres). Nunca rompe el resultado
        de la remediación."""
        if job.source_finding_id is None:
            return
        if job.status not in (
            RemediationJobStatus.SUCCEEDED.value,
            RemediationJobStatus.SKIPPED_COMPLIANT.value,
        ):
            return
        try:
            from backend.app.motors.m08_verification.models import (
                VerificationFinding,
            )
            from backend.app.motors.m08_verification.remediation.retest_runner import (  # noqa: E501
                run_retest,
            )

            # SAVEPOINT: el re-test corre AISLADO de la transacción principal. Si
            # falla (escáner, RLS, constraint…) se revierte solo el savepoint y la
            # remediación exitosa NO se pierde — best-effort de verdad, no poison.
            sp = await self.db.begin_nested()
            try:
                finding = await self.db.get(
                    VerificationFinding, job.source_finding_id,
                )
                if finding is None:
                    await sp.rollback()
                    return
                await run_retest(
                    self.db, finding, triggered_by="remediation_chain",
                )
                await sp.commit()
            except Exception:  # noqa: BLE001
                await sp.rollback()
                raise
            await self._audit(job, "remediation.retest_chained")
        except Exception:  # noqa: BLE001 — el encadenado es best-effort
            logger.exception(
                "Retest encadenado falló (best-effort) para job %s", job.id,
            )

    async def _execute_cycle(
        self,
        job_id: uuid.UUID,
        *,
        writer: RemediationWriter | None = None,
    ) -> RemediationJob:
        """Ejecuta el ciclo seguro completo. Idempotente sobre estados terminales."""
        job = await self._load_job(job_id)
        if job.status in TERMINAL_JOB_STATES:
            return job  # idempotente · ya resuelto

        spec = get_action_spec(job.action_type)
        if spec is None:
            return await self._fail(job, "Acción no catalogada (fail-closed).")

        # Revalidar kill-switch EN EJECUCIÓN (defensa en profundidad).
        target_enabled, policy = await self._resolve_target_flags(
            connector_id=job.connector_id, agent_id=job.agent_id,
        )
        mode = resolve_execution_mode(
            job.action_type, target_enabled=target_enabled, policy=policy,
        )

        if mode == ExecutionMode.BLOCKED:
            return await self._finish(
                job, RemediationJobStatus.BLOCKED,
                error_message="Acción destructiva · nunca automática (ADR-055).",
            )
        if mode == ExecutionMode.DISABLED:
            raise RemediationDisabledError(
                "Remediación deshabilitada por kill-switch/política · queda como plan.",
            )
        if (
            mode == ExecutionMode.REQUIRE_AUTHORIZATION
            and job.authorized_at is None
        ):
            if job.status != RemediationJobStatus.AWAITING_AUTHORIZATION.value:
                job.status = RemediationJobStatus.AWAITING_AUTHORIZATION.value
                await self.db.flush()
            raise AuthorizationRequiredError(
                "Acción GUARDED · requiere autorización previa antes de ejecutar.",
            )

        # Resolver writer: override de test > fábrica-por-conector (credenciales
        # reales descifradas de M16) > registro global opt-in > FAILED explícito.
        if writer is None:
            writer = await self._resolve_writer(job, spec)
            if writer is None:
                return await self._fail(
                    job,
                    f"Sin writer configurado para '{spec.provider}' · la escritura "
                    "es opt-in (requiere credenciales/scopes concedidos por el cliente).",
                )

        # Blast-radius guard.
        affected = (job.params or {}).get("affected_count")
        if (
            spec.blast_radius_max is not None
            and isinstance(affected, int)
            and affected > spec.blast_radius_max
        ):
            return await self._fail(
                job,
                f"Blast radius {affected} supera el máximo {spec.blast_radius_max} "
                "para esta acción · requiere revisión manual.",
            )

        job.started_at = _now()

        # 1 · PREFLIGHT
        await self._set_status(job, RemediationJobStatus.PREFLIGHT)
        try:
            state_before = await writer.read_state(
                job.action_type, job.target_ref, job.params,
            )
        except Exception as exc:  # noqa: BLE001
            return await self._fail(job, f"Preflight (read_state) falló: {exc}")

        if state_before.get(spec.desired_assertion) is True:
            job.result = {"preflight_state": state_before, "idempotent": True}
            return await self._finish(job, RemediationJobStatus.SKIPPED_COMPLIANT)

        # 2 · SNAPSHOT
        await self._set_status(job, RemediationJobStatus.SNAPSHOTTING)
        snap = RemediationSnapshot(
            project_id=job.project_id,
            job_id=job.id,
            action_type=job.action_type,
            target_ref=job.target_ref,
            state_before=state_before,
            created_by_user_id=job.created_by_user_id,
        )
        self.db.add(snap)
        await self.db.flush()

        # 2.5 · dry-run → no aplica nada (ensayo)
        if job.dry_run:
            job.result = {
                "dry_run": True,
                "preflight_state": state_before,
                "would_apply": True,
            }
            return await self._finish(job, RemediationJobStatus.SUCCEEDED)

        # 3 · APPLY
        await self._set_status(job, RemediationJobStatus.APPLYING)
        try:
            apply_result = await writer.apply(
                job.action_type, job.target_ref, job.params,
            )
        except Exception as exc:  # noqa: BLE001
            return await self._rollback_or_fail(
                job, writer, snap, f"Apply falló: {exc}",
            )

        # 4 · VERIFY
        await self._set_status(job, RemediationJobStatus.VERIFYING)
        try:
            state_after = await writer.read_state(
                job.action_type, job.target_ref, job.params,
            )
        except Exception as exc:  # noqa: BLE001
            return await self._rollback_or_fail(
                job, writer, snap, f"Verify (read_state) falló: {exc}",
            )

        if state_after.get(spec.desired_assertion) is True:
            job.result = {
                "apply_result": apply_result,
                "state_before": state_before,
                "state_after": state_after,
                "verified": True,
            }
            return await self._finish(job, RemediationJobStatus.SUCCEEDED)

        # Verify falló → rollback.
        return await self._rollback_or_fail(
            job, writer, snap,
            "Verificación falló: la propiedad deseada no se cumple tras aplicar.",
        )

    # ── rollback ───────────────────────────────────────────────────────────

    async def _rollback_or_fail(
        self,
        job: RemediationJob,
        writer: RemediationWriter,
        snap: RemediationSnapshot,
        reason: str,
    ) -> RemediationJob:
        """Intenta revertir desde el snapshot · ROLLED_BACK o FAILED."""
        try:
            rb = await writer.rollback(
                job.action_type, job.target_ref, snap.state_before,
            )
        except Exception as exc:  # noqa: BLE001
            job.result = {
                "rolled_back": False,
                "reason": reason,
                "rollback_error": str(exc),
            }
            return await self._finish(
                job, RemediationJobStatus.FAILED,
                error_message=f"{reason} · ADEMÁS el rollback falló: {exc}",
            )
        job.result = {"rolled_back": True, "rollback_result": rb, "reason": reason}
        return await self._finish(
            job, RemediationJobStatus.ROLLED_BACK, error_message=reason,
        )

    # ── consultas ──────────────────────────────────────────────────────────

    async def list_jobs(
        self, project_id: uuid.UUID, *, status: str | None = None,
    ) -> list[RemediationJob]:
        stmt = select(RemediationJob).where(
            RemediationJob.project_id == project_id,
            RemediationJob.deleted_at.is_(None),
        )
        if status:
            stmt = stmt.where(RemediationJob.status == status)
        stmt = stmt.order_by(RemediationJob.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_job(self, job_id: uuid.UUID) -> RemediationJob:
        return await self._load_job(job_id)

    # ── internos ───────────────────────────────────────────────────────────

    async def _load_job(self, job_id: uuid.UUID) -> RemediationJob:
        job = await self.db.get(RemediationJob, job_id)
        if job is None:
            raise JobNotFoundError(f"RemediationJob {job_id} no encontrado")
        return job

    async def _resolve_target_flags(
        self,
        *,
        connector_id: uuid.UUID | None,
        agent_id: uuid.UUID | None,
    ) -> tuple[bool, str]:
        """Capa 2+3 del kill-switch · (target_enabled, policy)."""
        if connector_id is not None:
            connector = await self.db.get(CloudConnector, connector_id)
            if connector is None:
                return (False, AutoRemediationPolicy.OFF.value)
            return (
                bool(connector.remediation_enabled),
                connector.auto_remediation_policy or AutoRemediationPolicy.OFF.value,
            )
        if agent_id is not None:
            # Host on-prem (Fase 3): un agente ACTIVE habilita el objetivo con
            # política FULL (safe_auto auto + guarded con autorización previa).
            from backend.app.motors.m_remediation.agent_models import (
                RemediationAgent,
                RemediationAgentStatus,
            )

            agent = await self.db.get(RemediationAgent, agent_id)
            if agent is None or agent.status != RemediationAgentStatus.ACTIVE.value:
                return (False, AutoRemediationPolicy.OFF.value)
            return (True, AutoRemediationPolicy.FULL.value)
        # Sin objetivo → deshabilitado.
        return (False, AutoRemediationPolicy.OFF.value)

    async def _resolve_writer(self, job: RemediationJob, spec):
        """Obtiene el writer real del job (fábrica por conector → registro global)."""
        if job.connector_id is not None:
            connector = await self.db.get(CloudConnector, job.connector_id)
            if connector is not None:
                from backend.app.motors.m_remediation.cloud_writers import (
                    build_writer_for_connector,
                )

                writer = await build_writer_for_connector(self.db, connector)
                if writer is not None:
                    return writer
        try:
            return get_writer(spec.provider)
        except WriterNotConfigured:
            return None

    async def _set_status(
        self, job: RemediationJob, status: RemediationJobStatus,
    ) -> None:
        job.status = status.value
        await self.db.flush()
        await self._audit(job, f"remediation.{status.value}")

    async def _finish(
        self,
        job: RemediationJob,
        status: RemediationJobStatus,
        *,
        error_message: str | None = None,
    ) -> RemediationJob:
        job.status = status.value
        job.finished_at = _now()
        if error_message:
            job.error_message = error_message
        await self.db.flush()
        await self._audit(job, f"remediation.{status.value}")
        return job

    async def _fail(
        self,
        job: RemediationJob,
        message: str,
        *,
        status: RemediationJobStatus = RemediationJobStatus.FAILED,
    ) -> RemediationJob:
        job.result = {**(job.result or {}), "error": message}
        return await self._finish(job, status, error_message=message)

    async def _audit(self, job: RemediationJob, accion: str) -> None:
        """Audit R6 + Sub-atom 5.A 3-way OR (best-effort · no rompe el ciclo)."""
        await emit_audit_log(
            self.db,
            tabla="remediation_jobs",
            registro_id=job.id,
            accion=accion[:60],
            project_id=job.project_id,
            client_id=job.client_id,
            payload_new={
                "action_type": job.action_type,
                "tier": job.tier,
                "status": job.status,
                "target_ref": job.target_ref,
                "dry_run": job.dry_run,
            },
        )
