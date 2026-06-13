"""AuditDryRunService · orchestrator M10 + A11 (ADR-037 SAN-D MB-15.1).

Pipeline dry-run pre-auditoría externa:

1. Trigger M10 ``AuditSimulatorService.run_simulation`` → 58 preguntas
   ENAC determinísticas L0-L5 matching evidencia real.
2. Build m10_audit_result + client_context dicts (mismo shape que
   ``agent_11_wrapper.py`` para consistency).
3. Trigger A11 ``Agent11AuditorVirtual.generate_supplementary_audit`` →
   PAC sector-aware + 3-5 preguntas sectoriales + narrativa ejecutiva.
4. Persistir ``audit_dry_run_results`` con M10 payload + A11 payload +
   métricas agregadas.
5. Trigger AlertService si critical_gaps > 0 (category=audit_due,
   severity=warning|critical).

Coste compute: 1 batch determinista M10 + 1 LLM call A11 (vs 58 LLM
calls del briefing v2 literal · 50× ahorro · DEC-A11-58-LLM-CALLS
ADR-037 Deferrables).
"""
from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy import text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.database import set_tenant_context

from backend.app.agents.agent_11_auditor_virtual import (
    Agent11AuditorVirtual,
)
from backend.app.agents.models.dry_run import AuditDryRunResult
from backend.app.agents.schemas.dry_run import (
    DryRunHistoryEntry,
    DryRunResult,
    DryRunSummary,
    M10FindingSummary,
    M10Summary,
)
from backend.app.models.audit_sim import (
    AuditSimulationFinding,
)
from backend.app.models.core import Project
from backend.app.motors.m10_audit_sim.audit_simulator import (
    AuditSimulatorService,
)
from backend.app.motors.m18_communication.alert_service import AlertService


def _infer_sector(client) -> str:
    if not client or not client.sector:
        return "otro"
    s = client.sector.lower()
    if any(k in s for k in ("salud", "sanid", "hospital", "clinic")):
        return "sanidad"
    if any(k in s for k in ("aapp", "publica", "ministerio", "ayunt", "gobierno")):
        return "aapp"
    if any(k in s for k in ("fintech", "banca", "seguros", "fondo")):
        return "fintech"
    return "otro"


def _infer_size(num_employees: int | None) -> str:
    if num_employees is None:
        return "PYME"
    if num_employees < 50:
        return "PYME"
    if num_employees < 250:
        return "mediana"
    return "grande"


class AuditDryRunService:
    """Orchestrator M10 + A11 + persistencia + alertas."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._m10 = AuditSimulatorService()
        self._a11 = Agent11AuditorVirtual()

    async def _scope_to_project(self, project_id: UUID) -> None:
        """FIX(RLS): resuelve owner vía get_project_owner (SECURITY DEFINER)
        y fija tenant context antes de cualquier query RLS-protegida. La global
        dep NO fija el contexto para admin → sin esto las filas projects /
        audit_dry_run_results quedan ocultas bajo RLS (fulkro_app)."""
        owner = (
            await self.db.execute(
                _sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
            )
        ).scalar()
        if not owner:
            raise ValueError(f"Project {project_id} not found")
        await set_tenant_context(self.db, client_id=owner, project_id=project_id)

    async def execute_dry_run(
        self,
        project_id: UUID,
        executor_id: UUID | None = None,
    ) -> DryRunResult:
        """Pipeline completo · 30-90s típico (M10 batch + A11 LLM)."""
        start = time.time()

        # FIX(RLS): fija tenant context antes del primer SELECT(Project)
        await self._scope_to_project(project_id)

        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.client))
        )
        project = (await self.db.execute(stmt)).scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        categoria = (project.categoria_objetivo or "BASICA").upper()
        archetype = project.archetype

        # 1. Trigger M10 run_simulation
        m10_run = await self._m10.run_simulation(
            self.db, project_id=project_id, categoria=categoria,
        )
        await self.db.flush()

        # 2. Cargar findings M10
        findings = (
            await self.db.execute(
                select(AuditSimulationFinding)
                .where(AuditSimulationFinding.run_id == m10_run.id)
                .where(AuditSimulationFinding.deleted_at.is_(None))
            )
        ).scalars().all()
        findings = list(findings)

        # 3. Build M10 audit_result dict (shape A11 wrapper)
        nc_mayores = [
            {"codigo": f.measure_code, "descripcion": f.measure_name or f.measure_code}
            for f in findings if f.evaluacion == "no_conforme_mayor"
        ]
        nc_menores = [
            {"codigo": f.measure_code, "descripcion": f.measure_name or f.measure_code}
            for f in findings if f.evaluacion == "no_conforme_menor"
        ]
        scores_familia = m10_run.scores_por_familia or {}
        # FIX(dead-default): el histograma de madurez se leía de
        # scores_familia["_total_LX"], claves que _scores_by_family NUNCA emite
        # → el auditor A11 (LLM) veía SIEMPRE L5..L0 = 0/0/0/0/0/0. Se computa
        # de los findings reales (nivel_madurez por medida evaluada).
        _hist = {f"L{i}": 0 for i in range(6)}
        for _f in findings:
            if _f.evaluacion == "no_aplica":
                continue
            _lv = _f.nivel_madurez if _f.nivel_madurez in _hist else None
            if _lv:
                _hist[_lv] += 1
        m10_audit_result = {
            "score_conformidad": int(m10_run.score_global or 0),
            "categoria_ens": m10_run.categoria or categoria,
            "nc_mayores": nc_mayores,
            "nc_menores": nc_menores,
            "preguntas_L5": _hist["L5"],
            "preguntas_L4": _hist["L4"],
            "preguntas_L3": _hist["L3"],
            "preguntas_L2": _hist["L2"],
            "preguntas_L1": _hist["L1"],
            "preguntas_L0": _hist["L0"],
            "preguntas_respondidas_total": int(m10_run.measures_evaluated or 0),
        }

        # 4. Build client_context
        client = project.client
        target_audit_str: str | None = None
        if isinstance(project.fecha_objetivo_certificacion, date):
            target_audit_str = project.fecha_objetivo_certificacion.isoformat()
        client_context: dict[str, Any] = {
            "company_name": client.nombre if client else "",
            "sector": _infer_sector(client),
            "size": _infer_size(client.numero_empleados if client else None),
            "ens_category": categoria,
            "is_aapp": _infer_sector(client) == "aapp",
            "target_audit_date": target_audit_str,
        }

        # 5. Trigger A11 senior layer
        a11_payload: dict[str, Any]
        try:
            a11_result = await self._a11.generate_supplementary_audit(
                self.db,
                m10_audit_result=m10_audit_result,
                client_context=client_context,
                project_id=project_id,
            )
            a11_payload = (
                a11_result if isinstance(a11_result, dict) else {"raw": str(a11_result)}
            )
        except Exception as exc:
            a11_payload = {"error": f"A11 fallo: {exc}", "fallback": True}

        # 6. Métricas agregadas
        total_questions = len(findings)
        questions_with_evidence = sum(
            1 for f in findings
            if f.evaluacion in ("conforme", "no_conforme_menor", "observacion")
        )
        gaps_detected = len(nc_mayores) + len(nc_menores)
        critical_gaps = len(nc_mayores)

        score = int(m10_run.score_global or 0)
        execution_time_ms = int((time.time() - start) * 1000)

        # 7. Persistir
        m10_summary_jsonb = {
            "run_id": str(m10_run.id),
            "score_global": int(m10_run.score_global or 0),
            "nivel_madurez_global": m10_run.nivel_madurez_global,
            "conformes": m10_run.conformes,
            "no_conformes_mayores": m10_run.no_conformes_mayores,
            "no_conformes_menores": m10_run.no_conformes_menores,
            "observaciones": m10_run.observaciones,
            "no_aplica": m10_run.no_aplica,
            "contradicciones_count": m10_run.contradicciones_count,
            "scores_por_familia": dict(scores_familia),
            "findings": [
                {
                    "measure_code": f.measure_code,
                    "measure_name": f.measure_name,
                    "evaluacion": f.evaluacion,
                    "nivel_madurez": f.nivel_madurez,
                    "contradiccion_detectada": bool(f.contradiccion_detectada),
                }
                for f in findings
            ],
        }

        result = AuditDryRunResult(
            project_id=project_id,
            executed_at=datetime.now(timezone.utc),
            executed_by=executor_id,
            m10_run_id=m10_run.id,
            category_at_execution=categoria,
            archetype_at_execution=archetype,
            total_questions=total_questions,
            questions_with_evidence=questions_with_evidence,
            overall_readiness_score=score,
            gaps_detected=gaps_detected,
            critical_gaps=critical_gaps,
            execution_time_ms=execution_time_ms,
            m10_payload=m10_summary_jsonb,
            a11_payload=a11_payload,
            model_used="claude-opus-4-7",
        )
        self.db.add(result)
        await self.db.flush()
        await self.db.refresh(result)

        # 8. Trigger alert si critical_gaps > 0
        if critical_gaps > 0:
            severity = "critical" if critical_gaps >= 5 else "warning"
            try:
                await AlertService(self.db).trigger_alert(
                    project_id=project_id,
                    severity=severity,
                    category="audit_due",
                    title=(
                        f"Dry-run detectó {critical_gaps} NC mayores · "
                        f"resolver antes de auditoría externa"
                    ),
                    description=(
                        f"Readiness {score}% · {gaps_detected} gaps total · "
                        f"{critical_gaps} no conformidades mayores"
                    ),
                    action_url=(
                        f"/admin/projects/{project_id}/audit-dry-run/results/{result.id}"
                    ),
                    triggered_by="audit_dry_run_service",
                    metadata={
                        "result_id": str(result.id),
                        "m10_run_id": str(m10_run.id),
                    },
                )
            except Exception:
                # Alert dispatch failure no debe romper dry-run completion
                pass

        return self._to_dry_run_result(result, m10_summary_jsonb)

    async def get_summary(self, project_id: UUID) -> DryRunSummary:
        """Resumen dashboard · histórico last 5."""
        # FIX(RLS): fija tenant context antes del SELECT(audit_dry_run_results)
        await self._scope_to_project(project_id)

        rows = (
            await self.db.execute(
                select(AuditDryRunResult)
                .where(AuditDryRunResult.project_id == project_id)
                .where(AuditDryRunResult.deleted_at.is_(None))
                .order_by(AuditDryRunResult.executed_at.desc())
                .limit(5)
            )
        ).scalars().all()
        rows = list(rows)

        if not rows:
            return DryRunSummary()

        latest = rows[0]
        return DryRunSummary(
            last_executed_at=latest.executed_at,
            overall_readiness_score=latest.overall_readiness_score,
            gaps_detected=latest.gaps_detected,
            critical_gaps=latest.critical_gaps,
            history=[
                DryRunHistoryEntry(
                    id=r.id,
                    executed_at=r.executed_at,
                    score=r.overall_readiness_score,
                    gaps=r.gaps_detected,
                    critical_gaps=r.critical_gaps,
                )
                for r in rows
            ],
        )

    async def get_result(
        self, project_id: UUID, result_id: UUID,
    ) -> DryRunResult | None:
        # FIX(RLS): fija tenant context antes del SELECT(audit_dry_run_results)
        await self._scope_to_project(project_id)

        row = (
            await self.db.execute(
                select(AuditDryRunResult)
                .where(AuditDryRunResult.id == result_id)
                .where(AuditDryRunResult.project_id == project_id)
                .where(AuditDryRunResult.deleted_at.is_(None))
            )
        ).scalar_one_or_none()
        if not row:
            return None
        return self._to_dry_run_result(row, row.m10_payload or {})

    @staticmethod
    def _to_dry_run_result(
        row: AuditDryRunResult, m10_payload: dict[str, Any],
    ) -> DryRunResult:
        findings_raw = m10_payload.get("findings", []) if m10_payload else []
        findings_summaries = [
            M10FindingSummary(
                measure_code=f.get("measure_code", ""),
                measure_name=f.get("measure_name"),
                evaluacion=f.get("evaluacion", ""),
                nivel_madurez=f.get("nivel_madurez", ""),
                contradiccion_detectada=bool(f.get("contradiccion_detectada", False)),
            )
            for f in findings_raw
        ]
        m10_summary: M10Summary | None = None
        if m10_payload and m10_payload.get("run_id"):
            m10_summary = M10Summary(
                run_id=UUID(m10_payload["run_id"]),
                score_global=int(m10_payload.get("score_global", 0)),
                nivel_madurez_global=m10_payload.get("nivel_madurez_global", "L0"),
                conformes=int(m10_payload.get("conformes", 0)),
                no_conformes_mayores=int(m10_payload.get("no_conformes_mayores", 0)),
                no_conformes_menores=int(m10_payload.get("no_conformes_menores", 0)),
                observaciones=int(m10_payload.get("observaciones", 0)),
                no_aplica=int(m10_payload.get("no_aplica", 0)),
                contradicciones_count=int(m10_payload.get("contradicciones_count", 0)),
                findings=findings_summaries,
            )

        return DryRunResult(
            id=row.id,
            project_id=row.project_id,
            executed_at=row.executed_at,
            m10_run_id=row.m10_run_id,
            category_at_execution=row.category_at_execution,
            archetype_at_execution=row.archetype_at_execution,
            total_questions=row.total_questions,
            questions_with_evidence=row.questions_with_evidence,
            overall_readiness_score=row.overall_readiness_score,
            gaps_detected=row.gaps_detected,
            critical_gaps=row.critical_gaps,
            execution_time_ms=row.execution_time_ms,
            m10_summary=m10_summary,
            a11_payload=row.a11_payload,
            model_used=row.model_used,
        )
