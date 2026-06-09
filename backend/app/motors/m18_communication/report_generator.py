"""M18 Report Generator — reportes deterministas de proyecto.

5 tipos de reporte (spec §3.2.9 / §Motor 18 / Apéndice F.6):
- weekly_sponsor: status semanal, 1 página
- monthly_comite: status mensual Comité Seguridad, 3-5 páginas
- quarterly_direccion: status trimestral Dirección, 1 página + RAG
- compliance_resources: cumplimiento compromisos del cliente
- quick_wins: logros rápidos (feed M20)

Todo determinista. Datos reales de:
- M17 planning (progreso, tareas, retrasos)
- M19 ProjectRisk (riesgos)
- M5 obligations
- M7 evidence
- M10 audit_simulation_runs (NC mayores)
- M14 client_commitments
"""
from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_sim import AuditSimulationRun
from backend.app.models.collaboration import WorkspaceFeedItem
from backend.app.models.commercial import ClientCommitment
from backend.app.models.documents import Evidence
from backend.app.models.findings import Finding
from backend.app.models.planning import (
    ProjectPlan,
    ProjectRisk,
    StatusReport,
    WbsTask,
)


REPORT_TEMPLATES: dict[str, dict[str, Any]] = {
    "weekly_sponsor": {
        "nombre": "Status Semanal — Sponsor",
        "secciones": [
            "resumen_semana", "tareas_completadas", "tareas_proxima_semana",
            "bloqueadores", "decisiones_pendientes",
        ],
        "longitud_objetivo": "1 página",
        "destinatario_default": "sponsor",
    },
    "monthly_comite": {
        "nombre": "Status Mensual — Comité de Seguridad",
        "secciones": [
            "resumen_ejecutivo", "metricas_avance", "hitos_alcanzados",
            "hallazgos_recientes", "riesgos_actualizados", "proximos_pasos",
            "decisiones_requeridas",
        ],
        "longitud_objetivo": "3-5 páginas",
        "destinatario_default": "comite_seguridad",
    },
    "quarterly_direccion": {
        "nombre": "Status Trimestral — Dirección",
        "secciones": [
            "semaforo_rag", "resumen_ejecutivo", "hitos_logrados",
            "riesgos_criticos", "decisiones_direccion",
        ],
        "longitud_objetivo": "1 página ejecutiva",
        "destinatario_default": "direccion",
    },
    "compliance_resources": {
        "nombre": "Cumplimiento de Recursos del Cliente",
        "secciones": [
            "compromisos_contractuales", "cumplimiento_actual",
            "incumplimientos", "impacto_proyecto", "accion_requerida",
        ],
        "longitud_objetivo": "1-2 páginas",
        "destinatario_default": "sponsor",
    },
    "quick_wins": {
        "nombre": "Quick Wins del Proyecto",
        "secciones": ["logros_rapidos", "impacto_seguridad", "siguiente_quick_win"],
        "longitud_objetivo": "feed item corto",
        "destinatario_default": "cliente_general",
    },
}


class ReportError(Exception):
    pass


class ReportGeneratorService:
    """Genera reportes de proyecto desde datos reales."""

    async def generate_report(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        tipo: str,
        periodo_inicio: date | None = None,
        periodo_fin: date | None = None,
    ) -> StatusReport:
        if tipo not in REPORT_TEMPLATES:
            raise ReportError(
                f"Tipo inválido: {tipo}. Válidos: {sorted(REPORT_TEMPLATES)}"
            )
        tpl = REPORT_TEMPLATES[tipo]
        today = date.today()

        # Defaults de período
        if tipo == "weekly_sponsor":
            periodo_fin = periodo_fin or today
            periodo_inicio = periodo_inicio or (periodo_fin - timedelta(days=7))
        elif tipo == "monthly_comite":
            periodo_fin = periodo_fin or today
            periodo_inicio = periodo_inicio or (periodo_fin - timedelta(days=30))
        elif tipo == "quarterly_direccion":
            periodo_fin = periodo_fin or today
            periodo_inicio = periodo_inicio or (periodo_fin - timedelta(days=90))
        else:
            periodo_fin = periodo_fin or today
            periodo_inicio = periodo_inicio or periodo_fin

        # Recolección de datos según tipo
        if tipo == "weekly_sponsor":
            contenido = await self._collect_weekly_data(db, project_id, periodo_inicio, periodo_fin)
        elif tipo == "monthly_comite":
            contenido = await self._collect_monthly_data(db, project_id, periodo_inicio, periodo_fin)
        elif tipo == "quarterly_direccion":
            contenido = await self._collect_quarterly_data(db, project_id, periodo_inicio, periodo_fin)
        elif tipo == "compliance_resources":
            contenido = await self._collect_compliance_data(db, project_id, periodo_inicio, periodo_fin)
        else:  # quick_wins
            contenido = await self._collect_quick_wins_data(db, project_id, periodo_inicio, periodo_fin)

        report = StatusReport(
            project_id=project_id,
            tipo=tipo,
            destinatario_rol=tpl["destinatario_default"],
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            contenido_jsonb=contenido,
            semaforo_rag=contenido.get("semaforo_rag"),
            estado="generated",
            generado_at=datetime.now(timezone.utc),
            fecha_generacion=datetime.now(timezone.utc),
        )
        db.add(report)
        await db.flush()
        return report

    # ═════════════ Colectores ═════════════

    async def _collect_weekly_data(
        self, db: AsyncSession, project_id: uuid.UUID, start: date, end: date,
    ) -> dict:
        tareas_completadas = await self._count_tasks(
            db, project_id, status_in=("completed", "done"),
            completed_between=(start, end),
        )
        tareas_proxima = await self._count_tasks(
            db, project_id, status_in=("pending", "planned", "in_progress"),
        )
        bloqueadores = await self._count_tasks(
            db, project_id, blocked_only=True,
        )
        riesgos_materializados = await self._count_materialized_risks(
            db, project_id, start, end,
        )
        return {
            "tipo": "weekly_sponsor",
            "resumen_semana": (
                f"Semana {start.isoformat()} → {end.isoformat()}. "
                f"{tareas_completadas} tareas completadas, "
                f"{bloqueadores} bloqueadores."
            ),
            "tareas_completadas_count": tareas_completadas,
            "tareas_proxima_semana_count": tareas_proxima,
            "bloqueadores_count": bloqueadores,
            "riesgos_materializados_semana": riesgos_materializados,
            "decisiones_pendientes": [],
        }

    async def _collect_monthly_data(
        self, db: AsyncSession, project_id: uuid.UUID, start: date, end: date,
    ) -> dict:
        tareas_totales = await self._count_tasks(db, project_id)
        tareas_completadas = await self._count_tasks(
            db, project_id, status_in=("completed", "done"),
        )
        hitos_alcanzados = await self._count_tasks(
            db, project_id, hitos_only=True, status_in=("completed", "done"),
        )
        riesgos_altos = await self._count_risks(db, project_id, high_only=True)
        findings_open = await self._count_findings(db, project_id, open_only=True)
        evidencias_nuevas = await self._count_evidences(db, project_id, created_between=(start, end))

        progreso_pct = int(
            (tareas_completadas / tareas_totales * 100) if tareas_totales else 0
        )

        return {
            "tipo": "monthly_comite",
            "resumen_ejecutivo": (
                f"Mes {start.isoformat()} → {end.isoformat()}. "
                f"Progreso global: {progreso_pct}%."
            ),
            "progreso_pct": progreso_pct,
            "tareas_totales": tareas_totales,
            "tareas_completadas": tareas_completadas,
            "hitos_alcanzados_count": hitos_alcanzados,
            "riesgos_altos_count": riesgos_altos,
            "findings_abiertos_count": findings_open,
            "evidencias_nuevas_count": evidencias_nuevas,
            "proximos_pasos": [],
            "decisiones_requeridas": [],
        }

    async def _collect_quarterly_data(
        self, db: AsyncSession, project_id: uuid.UUID, start: date, end: date,
    ) -> dict:
        tareas_totales = await self._count_tasks(db, project_id)
        tareas_completadas = await self._count_tasks(
            db, project_id, status_in=("completed", "done"),
        )
        progreso_pct = int(
            (tareas_completadas / tareas_totales * 100) if tareas_totales else 0
        )

        # Última simulación M10
        last_sim = (await db.execute(
            select(AuditSimulationRun).where(
                AuditSimulationRun.project_id == project_id,
            ).order_by(AuditSimulationRun.completed_at.desc().nulls_last()).limit(1)
        )).scalar_one_or_none()
        nc_mayores = last_sim.no_conformes_mayores if last_sim else 0
        sim_score = last_sim.score_global if last_sim else None

        # Retrasos
        retraso_semanas = await self._max_delay_weeks(db, project_id)

        riesgos_criticos = await self._count_risks(db, project_id, critical_only=True)

        rag = self._calculate_rag(
            progreso_pct=progreso_pct,
            nc_mayores=nc_mayores,
            riesgos_criticos=riesgos_criticos,
            retraso_semanas=retraso_semanas,
        )

        return {
            "tipo": "quarterly_direccion",
            "semaforo_rag": rag,
            "resumen_ejecutivo": (
                f"Trimestre {start.isoformat()} → {end.isoformat()}. "
                f"Progreso: {progreso_pct}%. Semáforo: {rag.upper()}."
            ),
            "progreso_pct": progreso_pct,
            "nc_mayores_simulacion": nc_mayores,
            "score_simulacion": sim_score,
            "riesgos_criticos_count": riesgos_criticos,
            "retraso_semanas": retraso_semanas,
            "hitos_logrados": [],
            "decisiones_direccion": [],
        }

    async def _collect_compliance_data(
        self, db: AsyncSession, project_id: uuid.UUID, start: date, end: date,
    ) -> dict:
        res = await db.execute(
            select(ClientCommitment).where(
                ClientCommitment.project_id == project_id,
            )
        )
        commitments = list(res.scalars().all())
        incumplidos = [c for c in commitments if c.cumplido is False]
        pendientes = [c for c in commitments if c.cumplido is None]
        cumplidos = [c for c in commitments if c.cumplido is True]

        return {
            "tipo": "compliance_resources",
            "total_compromisos": len(commitments),
            "cumplidos_count": len(cumplidos),
            "pendientes_count": len(pendientes),
            "incumplidos_count": len(incumplidos),
            "incumplimientos": [
                {
                    "id": str(c.id),
                    "tipo": c.tipo,
                    "parametro": c.parametro,
                    "valor_esperado": c.valor_esperado,
                    "valor_actual": c.valor_actual,
                }
                for c in incumplidos
            ],
            "accion_requerida": (
                "Regularizar compromisos incumplidos"
                if incumplidos else "Sin acciones requeridas"
            ),
        }

    async def _collect_quick_wins_data(
        self, db: AsyncSession, project_id: uuid.UUID, start: date, end: date,
    ) -> dict:
        feed_items = (await db.execute(
            select(WorkspaceFeedItem).where(
                WorkspaceFeedItem.project_id == project_id,
                WorkspaceFeedItem.tipo.in_(["hito_completado", "tarea_completada"]),
                WorkspaceFeedItem.created_at >= datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc),
            ).order_by(WorkspaceFeedItem.created_at.desc()).limit(10)
        )).scalars().all()

        return {
            "tipo": "quick_wins",
            "logros_rapidos": [
                {"titulo": i.titulo, "fecha": i.created_at.date().isoformat() if i.created_at else None}
                for i in feed_items
            ],
            "logros_count": len(feed_items),
            "impacto_seguridad": "Incremental",
            "siguiente_quick_win": None,
        }

    # ═════════════ Queries base ═════════════

    async def _count_tasks(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        status_in: tuple[str, ...] | None = None,
        blocked_only: bool = False,
        hitos_only: bool = False,
        completed_between: tuple[date, date] | None = None,
    ) -> int:
        """Count WbsTask rows of a project.

        Resolvemos ``project_id`` via JOIN con ProjectPlan
        (``WbsTask.project_plan_id → ProjectPlan.project_id``) para no
        depender de la columna denormalizada ``WbsTask.project_id``,
        que en M17 puede quedar a NULL al crear las tareas.
        """
        stmt = (
            select(func.count(WbsTask.id))
            .join(ProjectPlan, WbsTask.project_plan_id == ProjectPlan.id)
            .where(ProjectPlan.project_id == project_id)
        )
        if status_in:
            stmt = stmt.where(WbsTask.status.in_(status_in))
        if blocked_only:
            stmt = stmt.where(WbsTask.blocker_description.isnot(None))
        if hitos_only:
            stmt = stmt.where(WbsTask.milestone_code.isnot(None))
        res = await db.execute(stmt)
        return res.scalar() or 0

    async def _count_materialized_risks(
        self, db: AsyncSession, project_id: uuid.UUID, start: date, end: date,
    ) -> int:
        res = await db.execute(
            select(func.count(ProjectRisk.id)).where(
                ProjectRisk.project_id == project_id,
                ProjectRisk.materializado_at.isnot(None),
                ProjectRisk.materializado_at >= datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc),
            )
        )
        return res.scalar() or 0

    async def _count_risks(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        high_only: bool = False,
        critical_only: bool = False,
    ) -> int:
        stmt = select(func.count(ProjectRisk.id)).where(ProjectRisk.project_id == project_id)
        if critical_only:
            stmt = stmt.where(
                and_(ProjectRisk.probabilidad >= 0.7, ProjectRisk.impacto_dias >= 30),
            )
        elif high_only:
            stmt = stmt.where(ProjectRisk.probabilidad >= 0.5)
        res = await db.execute(stmt)
        return res.scalar() or 0

    async def _count_findings(
        self, db: AsyncSession, project_id: uuid.UUID, open_only: bool = False,
    ) -> int:
        stmt = select(func.count(Finding.id)).where(Finding.project_id == project_id)
        if open_only:
            stmt = stmt.where(Finding.estado.in_(("open", "pendiente", "abierto")))
        res = await db.execute(stmt)
        return res.scalar() or 0

    async def _count_evidences(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        created_between: tuple[date, date] | None = None,
    ) -> int:
        stmt = select(func.count(Evidence.id)).where(Evidence.project_id == project_id)
        if created_between:
            start, end = created_between
            stmt = stmt.where(
                Evidence.created_at >= datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc),
                Evidence.created_at <= datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc),
            )
        res = await db.execute(stmt)
        return res.scalar() or 0

    async def _max_delay_weeks(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> int:
        """Retraso máximo en semanas entre tareas completadas tarde."""
        from backend.app.motors.m17_planning.planning_service import detect_delays
        try:
            delays = await detect_delays(db, project_id)
            if not delays:
                return 0
            return max(
                (d.get("delay_days", 0) for d in delays),
                default=0,
            ) // 7
        except Exception:
            return 0

    # ═════════════ RAG determinista ═════════════

    @staticmethod
    def _calculate_rag(
        progreso_pct: int,
        nc_mayores: int,
        riesgos_criticos: int,
        retraso_semanas: int,
    ) -> str:
        # RED: progreso<70 OR nc>0 OR riesgos críticos>0 OR retraso>2
        if (
            progreso_pct < 70
            or nc_mayores > 0
            or riesgos_criticos > 0
            or retraso_semanas > 2
        ):
            return "red"
        # AMBER: progreso<90 OR retraso>0
        if progreso_pct < 90 or retraso_semanas > 0:
            return "amber"
        return "green"

    # ═════════════ Consultas + Lifecycle ═════════════

    async def get_report(
        self, db: AsyncSession, report_id: uuid.UUID,
    ) -> StatusReport | None:
        res = await db.execute(select(StatusReport).where(StatusReport.id == report_id))
        return res.scalar_one_or_none()

    async def list_reports(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        tipo: str | None = None,
        estado: str | None = None,
    ) -> list[StatusReport]:
        stmt = select(StatusReport).where(StatusReport.project_id == project_id)
        if tipo:
            stmt = stmt.where(StatusReport.tipo == tipo)
        if estado:
            stmt = stmt.where(StatusReport.estado == estado)
        stmt = stmt.order_by(StatusReport.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def mark_reviewed(
        self, db: AsyncSession, report_id: uuid.UUID,
    ) -> StatusReport:
        r = await self.get_report(db, report_id)
        if not r:
            raise ReportError(f"Report {report_id} no encontrado")
        if r.estado not in ("generated", "draft"):
            raise ReportError(
                f"Solo se revisan reportes generated/draft (actual: {r.estado})"
            )
        r.estado = "reviewed"
        r.revisado_at = datetime.now(timezone.utc)
        await db.flush()
        return r

    async def mark_sent(
        self, db: AsyncSession, report_id: uuid.UUID,
    ) -> StatusReport:
        r = await self.get_report(db, report_id)
        if not r:
            raise ReportError(f"Report {report_id} no encontrado")
        if r.estado != "reviewed":
            raise ReportError(
                f"Requiere revisión previa (actual: {r.estado})"
            )
        r.estado = "sent"
        r.enviado_at = datetime.now(timezone.utc)
        await db.flush()
        return r

    # ═════════════ DOCX ═════════════

    async def generate_docx(
        self, db: AsyncSession, report_id: uuid.UUID,
    ) -> bytes:
        from docx import Document as DocxDocument

        r = await self.get_report(db, report_id)
        if not r:
            raise ReportError(f"Report {report_id} no encontrado")
        tpl = REPORT_TEMPLATES.get(r.tipo, {"nombre": "Reporte"})
        content = r.contenido_jsonb or {}

        doc = DocxDocument()
        doc.add_heading(tpl["nombre"], level=0)
        doc.add_paragraph(f"Período: {r.periodo_inicio} → {r.periodo_fin}")
        doc.add_paragraph(f"Destinatario: {r.destinatario_rol}")
        if r.semaforo_rag:
            doc.add_paragraph(f"Semáforo RAG: {r.semaforo_rag.upper()}")

        doc.add_heading("Contenido", level=1)
        for key, value in content.items():
            if isinstance(value, (list, dict)):
                doc.add_paragraph(f"{key}: {value}")
            else:
                doc.add_paragraph(f"{key}: {value}")

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()
