"""Agent 21 — DiscrepancyDetectorService (1.D.A v3.10).

Servicio determinista (NO LLM) que ejecuta detectores cross-motor SQL
para identificar incoherencias / NCs que un auditor ENS detectaría.

Sostiene R1 inviolable CLAUDE.md (motores deterministas > LLM para
decisiones normativas · trazabilidad ENAC > flexibilidad LLM).

Detectores implementados (5 ENS-only):
- magerit_vs_dda: análisis MAGERIT con riesgos críticos (MC/C) cuyas
  amenazas/dimensiones afectadas no tienen ninguna medida ENS DdA
  marcada como aplicable.
- dda_vs_evidence: medidas DdA marcadas aplicable + sin evidencia
  vigente (M07) asociada.
- magerit_vs_findings (1.D.A v3.10): riesgos críticos MAGERIT con 0
  findings tracking remediación · gap claro tracking ENS.
- dda_vs_documents (1.D.A v3.10): medidas DdA aplicables + 0 documentos
  política/procedimiento approved · NC cobertura documental.
- findings_vs_remediation (1.D.A v3.10): findings críticos/altos
  abiertos + 0 remediation_plans asignados · NC tracking remediación.

Pattern peek-no-LLM: scan_project crea scan_run (`pending`→`running`),
ejecuta cada detector, persiste discrepancies y cierra `completed`.
La clase legacy `DetectorDiscrepanciasAgent` (LLM wrapper) se mantiene
para invocaciones explicit-LLM si caller necesita reasoning narrativo.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.a21_discrepancies import A21Discrepancy, A21ScanRun


class DiscrepancyDetectorService:
    """Detector determinista cross-motor."""

    DETECTOR_MOTORS: dict[str, list[str]] = {
        "magerit_vs_dda": ["m02", "m03"],
        "dda_vs_evidence": ["m03", "m07"],
        "magerit_vs_findings": ["m02", "m04"],
        "dda_vs_documents": ["m03", "m06"],
        "findings_vs_remediation": ["m04", "m19"],
    }

    async def scan_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> A21ScanRun:
        """Crea scan_run, ejecuta detectores, persiste discrepancies."""
        run = A21ScanRun(
            project_id=project_id,
            run_status="running",
            started_at=datetime.now(timezone.utc),
            motors_scanned=[],
        )
        db.add(run)
        await db.flush()

        all_discrepancies: list[dict[str, Any]] = []
        motors_set: set[str] = set()
        try:
            for detector_name, motors in self.DETECTOR_MOTORS.items():
                detector_fn = getattr(self, f"_detect_{detector_name}")
                items = await detector_fn(db, project_id)
                for item in items:
                    item["discrepancy_type"] = detector_name
                    all_discrepancies.append(item)
                motors_set.update(motors)

            for d in all_discrepancies:
                disc = A21Discrepancy(
                    scan_run_id=run.id,
                    project_id=project_id,
                    discrepancy_type=d["discrepancy_type"],
                    severity=d["severity"],
                    motor_a=d["motor_a"],
                    motor_b=d["motor_b"],
                    description=d["description"],
                    evidence_a=d.get("evidence_a") or {},
                    evidence_b=d.get("evidence_b") or {},
                )
                db.add(disc)

            run.motors_scanned = sorted(motors_set)
            run.discrepancies_found = len(all_discrepancies)
            run.run_status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            await db.flush()
        except Exception as exc:
            run.run_status = "failed"
            run.error_message = str(exc)[:500]
            run.completed_at = datetime.now(timezone.utc)
            await db.flush()
            raise

        return run

    async def _detect_magerit_vs_dda(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Riesgos MAGERIT críticos (MC/C) sin medidas DdA aplicables.

        Heurística: si hay riesgos críticos abiertos pero el proyecto
        no tiene NINGUNA entry DdA marcada `aplicable`, hay un gap claro
        de cobertura.
        """
        critical_count = (await db.execute(sa_text(
            """
            SELECT COUNT(*) FROM magerit_risk_calculation rc
            JOIN magerit_analysis ma ON rc.analysis_id = ma.id
            WHERE ma.project_id = :pid
              AND ma.deleted_at IS NULL
              AND rc.risk_level IN ('MC', 'C')
            """,
        ), {"pid": str(project_id)})).scalar() or 0

        dda_aplicable_count = (await db.execute(sa_text(
            """
            SELECT COUNT(*) FROM dda_entries
            WHERE project_id = :pid
              AND deleted_at IS NULL
              AND aplicabilidad = 'aplicable'
            """,
        ), {"pid": str(project_id)})).scalar() or 0

        if critical_count > 0 and dda_aplicable_count == 0:
            return [{
                "severity": "critical",
                "motor_a": "m02",
                "motor_b": "m03",
                "description": (
                    f"{critical_count} riesgo(s) crítico(s) MAGERIT (MC/C) "
                    "abiertos · 0 medidas DdA aplicables. El proyecto carece "
                    "de cobertura ENS para los riesgos identificados."
                ),
                "evidence_a": {
                    "magerit_critical_count": int(critical_count),
                    "level_filter": ["MC", "C"],
                },
                "evidence_b": {"dda_aplicable_count": 0},
            }]
        return []

    async def _detect_dda_vs_evidence(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Medidas DdA aplicables sin evidencia vigente correspondiente.

        Heurística simple: contar medidas aplicables y evidencias vigentes;
        si aplicables > 0 y vigentes == 0, NC clara. Si aplicables > 5x
        vigentes, NC moderada (cobertura insuficiente).
        """
        aplicables = (await db.execute(sa_text(
            """
            SELECT COUNT(*) FROM dda_entries
            WHERE project_id = :pid
              AND deleted_at IS NULL
              AND aplicabilidad = 'aplicable'
            """,
        ), {"pid": str(project_id)})).scalar() or 0

        vigentes = (await db.execute(sa_text(
            """
            SELECT COUNT(*) FROM evidence
            WHERE project_id = :pid
              AND deleted_at IS NULL
              AND vigente = TRUE
            """,
        ), {"pid": str(project_id)})).scalar() or 0

        if aplicables > 0 and vigentes == 0:
            return [{
                "severity": "high",
                "motor_a": "m03",
                "motor_b": "m07",
                "description": (
                    f"{aplicables} medida(s) DdA aplicable(s) · 0 evidencias "
                    "vigentes. Las medidas declaradas aplicables carecen de "
                    "evidencia documental válida."
                ),
                "evidence_a": {"dda_aplicable_count": int(aplicables)},
                "evidence_b": {"evidence_vigente_count": 0},
            }]
        if aplicables > 0 and vigentes > 0 and aplicables >= 5 * vigentes:
            return [{
                "severity": "medium",
                "motor_a": "m03",
                "motor_b": "m07",
                "description": (
                    f"Cobertura insuficiente: {aplicables} medidas aplicables "
                    f"vs sólo {vigentes} evidencias vigentes (ratio "
                    f"{aplicables / max(vigentes, 1):.1f}x). Riesgo de "
                    "auditoría ENAC por evidencia incompleta."
                ),
                "evidence_a": {"dda_aplicable_count": int(aplicables)},
                "evidence_b": {"evidence_vigente_count": int(vigentes)},
            }]
        return []

    async def _detect_magerit_vs_findings(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Riesgos críticos MAGERIT sin findings tracking remediación.

        Heurística: si hay riesgos MC/C abiertos pero 0 findings registrados
        para el proyecto (M04 gap engine), no hay tracking de remediación
        documental · gap claro auditoría ENAC.
        """
        critical_risks = (await db.execute(sa_text(
            """
            SELECT COUNT(*) FROM magerit_risk_calculation rc
            JOIN magerit_analysis ma ON rc.analysis_id = ma.id
            WHERE ma.project_id = :pid
              AND ma.deleted_at IS NULL
              AND rc.risk_level IN ('MC', 'C')
            """,
        ), {"pid": str(project_id)})).scalar() or 0

        findings_count = (await db.execute(sa_text(
            """
            SELECT COUNT(*) FROM findings
            WHERE project_id = :pid
              AND deleted_at IS NULL
            """,
        ), {"pid": str(project_id)})).scalar() or 0

        if critical_risks > 0 and findings_count == 0:
            return [{
                "severity": "high",
                "motor_a": "m02",
                "motor_b": "m04",
                "description": (
                    f"{critical_risks} riesgo(s) crítico(s) MAGERIT (MC/C) "
                    "abiertos · 0 findings registrados M04. Sin tracking "
                    "remediación · auditor ENAC marcará NC por gap proceso."
                ),
                "evidence_a": {
                    "magerit_critical_count": int(critical_risks),
                    "level_filter": ["MC", "C"],
                },
                "evidence_b": {"findings_count": 0},
            }]
        return []

    async def _detect_dda_vs_documents(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Medidas DdA aplicables sin documentos política/procedimiento approved.

        Heurística: contar medidas DdA aplicables y documentos M06 generados
        clasificacion política o procedimiento estado approved. Si aplicables
        > 0 y documentos approved == 0 · NC clara. Si aplicables > 8x docs
        approved · NC moderada (cobertura documental insuficiente).
        """
        aplicables = (await db.execute(sa_text(
            """
            SELECT COUNT(*) FROM dda_entries
            WHERE project_id = :pid
              AND deleted_at IS NULL
              AND aplicabilidad = 'aplicable'
            """,
        ), {"pid": str(project_id)})).scalar() or 0

        docs_approved = (await db.execute(sa_text(
            """
            SELECT COUNT(*) FROM documents
            WHERE project_id = :pid
              AND deleted_at IS NULL
              AND clasificacion IN ('politica', 'procedimiento')
              AND estado = 'approved'
            """,
        ), {"pid": str(project_id)})).scalar() or 0

        if aplicables > 0 and docs_approved == 0:
            return [{
                "severity": "high",
                "motor_a": "m03",
                "motor_b": "m06",
                "description": (
                    f"{aplicables} medida(s) DdA aplicable(s) · 0 documentos "
                    "política/procedimiento approved. Cobertura documental "
                    "ENS ausente · NC severa auditoría ENAC."
                ),
                "evidence_a": {"dda_aplicable_count": int(aplicables)},
                "evidence_b": {
                    "documents_approved_count": 0,
                    "clasificacion_filter": ["politica", "procedimiento"],
                },
            }]
        if aplicables > 0 and docs_approved > 0 and aplicables >= 8 * docs_approved:
            return [{
                "severity": "medium",
                "motor_a": "m03",
                "motor_b": "m06",
                "description": (
                    f"Cobertura documental insuficiente: {aplicables} medidas "
                    f"aplicables vs sólo {docs_approved} documento(s) approved "
                    f"(ratio {aplicables / max(docs_approved, 1):.1f}x). Riesgo "
                    "auditoría por documentación parcial."
                ),
                "evidence_a": {"dda_aplicable_count": int(aplicables)},
                "evidence_b": {"documents_approved_count": int(docs_approved)},
            }]
        return []

    async def _detect_findings_vs_remediation(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Findings críticos/altos abiertos sin remediation_plans asignados.

        Heurística: findings severidad in (critica, alta) y estado abierto
        sin plan remediación · NC tracking proceso. Si findings críticos
        sin remediación · severity critical (peor caso). Si solo altas
        sin remediación · severity high.
        """
        critical_open = (await db.execute(sa_text(
            """
            SELECT COUNT(*) FROM findings f
            WHERE f.project_id = :pid
              AND f.deleted_at IS NULL
              AND f.severidad = 'critica'
              AND COALESCE(f.estado, 'abierto') IN ('abierto', 'en_curso')
              AND NOT EXISTS (
                SELECT 1 FROM remediation_plans rp
                WHERE rp.finding_id = f.id
                  AND rp.deleted_at IS NULL
              )
            """,
        ), {"pid": str(project_id)})).scalar() or 0

        high_open = (await db.execute(sa_text(
            """
            SELECT COUNT(*) FROM findings f
            WHERE f.project_id = :pid
              AND f.deleted_at IS NULL
              AND f.severidad = 'alta'
              AND COALESCE(f.estado, 'abierto') IN ('abierto', 'en_curso')
              AND NOT EXISTS (
                SELECT 1 FROM remediation_plans rp
                WHERE rp.finding_id = f.id
                  AND rp.deleted_at IS NULL
              )
            """,
        ), {"pid": str(project_id)})).scalar() or 0

        results: list[dict[str, Any]] = []
        if critical_open > 0:
            results.append({
                "severity": "critical",
                "motor_a": "m04",
                "motor_b": "m19",
                "description": (
                    f"{critical_open} finding(s) crítico(s) abierto(s) sin "
                    "remediation_plan asignado. Auditor ENAC marca NC severa "
                    "por gestión de no conformidades sin tracking."
                ),
                "evidence_a": {
                    "findings_critical_unplanned_count": int(critical_open),
                    "severidad_filter": "critica",
                },
                "evidence_b": {"remediation_plans_count": 0},
            })
        if high_open > 0:
            results.append({
                "severity": "high",
                "motor_a": "m04",
                "motor_b": "m19",
                "description": (
                    f"{high_open} finding(s) alta(s) abierto(s) sin "
                    "remediation_plan asignado. Riesgo escalación a crítica "
                    "sin tracking remediación."
                ),
                "evidence_a": {
                    "findings_high_unplanned_count": int(high_open),
                    "severidad_filter": "alta",
                },
                "evidence_b": {"remediation_plans_count": 0},
            })
        return results

    async def list_scan_runs(
        self, db: AsyncSession, project_id: uuid.UUID, limit: int = 10,
    ) -> list[A21ScanRun]:
        rows = (await db.execute(
            select(A21ScanRun).where(
                A21ScanRun.project_id == project_id,
                A21ScanRun.deleted_at.is_(None),
            ).order_by(A21ScanRun.started_at.desc()).limit(limit),
        )).scalars().all()
        return list(rows)

    async def list_discrepancies(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        resolution_status: str | None = None,
        severity: str | None = None,
        scan_run_id: uuid.UUID | None = None,
    ) -> list[A21Discrepancy]:
        stmt = select(A21Discrepancy).where(
            A21Discrepancy.project_id == project_id,
            A21Discrepancy.deleted_at.is_(None),
        )
        if resolution_status:
            stmt = stmt.where(
                A21Discrepancy.resolution_status == resolution_status,
            )
        if severity:
            stmt = stmt.where(A21Discrepancy.severity == severity)
        if scan_run_id:
            stmt = stmt.where(A21Discrepancy.scan_run_id == scan_run_id)
        stmt = stmt.order_by(A21Discrepancy.created_at.desc())
        rows = (await db.execute(stmt)).scalars().all()
        return list(rows)

    async def resolve_discrepancy(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        discrepancy_id: uuid.UUID,
        *,
        new_status: str,
        notes: str | None = None,
        resolved_by: uuid.UUID | None = None,
    ) -> A21Discrepancy:
        if new_status not in ("acknowledged", "resolved", "dismissed", "open"):
            raise ValueError(f"new_status invalido: {new_status}")
        disc = await db.get(A21Discrepancy, discrepancy_id)
        if disc is None or disc.project_id != project_id:
            raise ValueError("Discrepancy no encontrada")
        disc.resolution_status = new_status
        disc.resolution_notes = notes
        if new_status in ("resolved", "dismissed"):
            disc.resolved_at = datetime.now(timezone.utc)
            disc.resolved_by = resolved_by
        else:
            disc.resolved_at = None
            disc.resolved_by = None
        await db.flush()
        return disc
