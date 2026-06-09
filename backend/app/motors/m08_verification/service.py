"""M8 v5.1 — Verificacion Tecnica — Servicio principal.

Servicio operativo Checkpoints 1+2+3. Cubre orquestador de fases,
ZFP engine, mapeo ENS e integraciones cross-motor (M3/M5/M7/M9).

Operaciones expuestas:
- create_run            : crea registro + auto-deriva scope
- get_run               : por id
- list_runs             : por proyecto
- list_findings         : por run con filtros
- patch_finding         : cambia estado (FP / accepted_risk / etc.)
- patch_finding_mapping : corrige mapeo ENS manualmente
- retest, remediation_plan, handoff, ingest, report, heatmap,
  score, delta : implementados (no son stubs 501)

Items diferidos en backlog formal (no bloqueantes MVP):
- TODO-M8-G1 [MEDIA] Learn FP automaticamente (ML model post-MVP)
- TODO-M8-G2 [BAJA]  Lynis-SSH wrapper hosts remotos
- TODO-M8-G3 [MEDIA] scan_window via M14 contract overrides
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m08_verification.models import (
    VerificationFinding,
    VerificationRun,
)


# ────────────────────────────────────────────────────────────────────
# Excepciones
# ────────────────────────────────────────────────────────────────────

class VerificationError(Exception):
    """Error generico del motor de verificacion tecnica."""


class RunNotFoundError(VerificationError):
    pass


class FindingNotFoundError(VerificationError):
    pass


class RunStateError(VerificationError):
    pass


class ValidationError(VerificationError):
    pass


# ────────────────────────────────────────────────────────────────────
# Servicio
# ────────────────────────────────────────────────────────────────────

class VerificationService:
    """Servicio de verificacion tecnica (M8 v5.1).

    El metodo `create_run` invoca a `scope_deriver.derive_scope` para
    obtener targets/web_apps/exclusiones/scan_window automaticamente.
    En este checkpoint 1, si scope_deriver no encuentra activos, se
    devuelve un scope vacio explicito en vez de fallar.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── Runs ────────────────────────────────────────────────────────

    async def create_run(
        self,
        project_id: uuid.UUID,
        category: str,
        mode: str = "internal",
        tools_config: dict[str, Any] | None = None,
        schedule_now: bool = False,
        created_by: str = "marcos",
        *,
        enforce_gates: bool = True,
    ) -> VerificationRun:
        """Crea un run y auto-deriva el scope de Fulkro.

        Gate (P7-F1 · handoff H6): un run ``mode == "external"`` toca infra del
        cliente (acción técnica) y exige autorización previa del cliente vía
        magic-link ``autorizar_accion_tecnica`` (ADR-014 read-only OAuth /
        ADR-020 pentest authorization flow OTP step-up). Los runs ``internal``
        (self-scan / dogfooding sobre infra de Fulkro) NO la requieren. Mirror
        del patrón m03_dda/service.py:92.
        """
        if enforce_gates and mode == "external":
            from backend.app.core.workflow_gates import (
                require_pentest_authorisation,
            )
            await require_pentest_authorisation(self.db, project_id)

        from backend.app.motors.m08_verification.scope_deriver import (
            derive_scope,
        )
        scope, derived_from = await derive_scope(self.db, project_id, category)

        # FIX 2026-06-07: antes status="pending" SIEMPRE + schedule_now ignorado →
        # list_due_runs (status='scheduled' AND scheduled_start<=now) NUNCA lo recogía
        # → el botón "Lanzar verificación" no ejecutaba nada. Ahora el run nace
        # 'scheduled' con scheduled_start=now (schedule_now) para que el scheduler lo
        # dispare; sin schedule_now queda 'scheduled' a la próxima ventana nocturna.
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        scheduled_start = now if schedule_now else now + timedelta(hours=1)
        run = VerificationRun(
            project_id=project_id,
            category=category,
            mode=mode,
            status="scheduled",
            scheduled_start=scheduled_start,
            scope_jsonb=scope,
            scope_derived_from=derived_from,
            tools_config=tools_config or {},
            created_by=created_by,
        )
        self.db.add(run)
        await self.db.flush()
        return run

    async def get_run(self, run_id: uuid.UUID) -> VerificationRun:
        run = await self.db.get(VerificationRun, run_id)
        if run is None or run.deleted_at is not None:
            raise RunNotFoundError(f"VerificationRun {run_id} no encontrado")
        return run

    async def list_runs(
        self,
        project_id: uuid.UUID,
        status: str | None = None,
    ) -> list[VerificationRun]:
        stmt = select(VerificationRun).where(
            VerificationRun.project_id == project_id,
            VerificationRun.deleted_at.is_(None),
        )
        if status:
            stmt = stmt.where(VerificationRun.status == status)
        stmt = stmt.order_by(VerificationRun.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ─── Findings ────────────────────────────────────────────────────

    async def list_findings(
        self,
        run_id: uuid.UUID,
        severity: str | None = None,
        status: str | None = None,
        ens_measure: str | None = None,
        classification: str | None = None,
    ) -> list[VerificationFinding]:
        stmt = select(VerificationFinding).where(
            VerificationFinding.run_id == run_id,
            VerificationFinding.deleted_at.is_(None),
        )
        if severity:
            stmt = stmt.where(VerificationFinding.severity == severity)
        if status:
            stmt = stmt.where(VerificationFinding.status == status)
        if ens_measure:
            stmt = stmt.where(
                VerificationFinding.ens_primary_measure == ens_measure,
            )
        if classification:
            stmt = stmt.where(
                VerificationFinding.zfp_gate5_classification == classification,
            )
        stmt = stmt.order_by(
            VerificationFinding.confidence_score.desc(),
            VerificationFinding.severity.asc(),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_finding(self, finding_id: uuid.UUID) -> VerificationFinding:
        f = await self.db.get(VerificationFinding, finding_id)
        if f is None or f.deleted_at is not None:
            raise FindingNotFoundError(
                f"VerificationFinding {finding_id} no encontrado"
            )
        return f

    async def patch_finding_status(
        self,
        finding_id: uuid.UUID,
        status: str | None = None,
        false_positive_reason: str | None = None,
        accepted_risk_justification: str | None = None,
        accepted_risk_approved_by: str | None = None,
    ) -> VerificationFinding:
        f = await self.get_finding(finding_id)
        if status:
            f.status = status
            if status == "remediated":
                f.remediated_at = datetime.now(timezone.utc)
            elif status == "false_positive":
                f.false_positive_reason = (
                    false_positive_reason or "marcado por consultor"
                )
                # Future · TODO-M8-G1 cerrado pre-cliente · requiere dataset
                # FP labeled >= 200 samples · ver backlog_formal.md.
                # gate2_fp_filter rule-based operativo (zfp_engine.py).
            elif status == "accepted_risk":
                if not accepted_risk_justification:
                    raise ValidationError(
                        "accepted_risk requiere justification",
                    )
                f.accepted_risk_justification = accepted_risk_justification
                f.accepted_risk_approved_by = accepted_risk_approved_by
        if false_positive_reason and not status:
            f.false_positive_reason = false_positive_reason
        if accepted_risk_justification and not status:
            f.accepted_risk_justification = accepted_risk_justification
        if accepted_risk_approved_by and not status:
            f.accepted_risk_approved_by = accepted_risk_approved_by
        await self.db.flush()
        return f

    async def patch_finding_mapping(
        self,
        finding_id: uuid.UUID,
        ens_measures: list[dict[str, Any]],
        ens_primary_measure: str | None,
    ) -> VerificationFinding:
        f = await self.get_finding(finding_id)
        f.ens_measures = ens_measures
        if ens_primary_measure is not None:
            f.ens_primary_measure = ens_primary_measure
        await self.db.flush()
        return f
