"""Project planning, risks, communication."""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, Integer, Float, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class ProjectPlan(FullMixin, Base):
    __tablename__ = "project_plans"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    wbs: Mapped[dict | None] = mapped_column(JSONB)
    milestones: Mapped[dict | None] = mapped_column(JSONB)
    critical_path: Mapped[dict | None] = mapped_column(JSONB)
    resource_allocation: Mapped[dict | None] = mapped_column(JSONB)
    aprobado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    gantt_xlsx_path: Mapped[str | None] = mapped_column(String(500))
    gantt_pdf_path: Mapped[str | None] = mapped_column(String(500))
    # --- Motor 17 additions ---
    categoria: Mapped[str | None] = mapped_column(String(10), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date_estimated: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date_actual: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_effort_marcos_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_effort_platform_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_duration_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    critical_path_length_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    critical_path_tasks: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    marcos_weekly_capacity_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    client_weekly_capacity_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    estado: Mapped[str | None] = mapped_column(String(20), nullable=True)
    baseline_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    baseline_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    mermaid_gantt: Mapped[str | None] = mapped_column(Text, nullable=True)
    meeting_plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class WbsTask(FullMixin, Base):
    __tablename__ = "wbs_tasks"
    project_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("project_plans.id"), nullable=False)
    task_code: Mapped[str] = mapped_column(String(20), nullable=False)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("wbs_tasks.id"))
    phase: Mapped[str | None] = mapped_column(String(50))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    duration_days: Mapped[int | None] = mapped_column(Integer)
    effort_marcos_hours: Mapped[float | None] = mapped_column(Float)
    effort_platform: Mapped[str | None] = mapped_column(String(50))
    responsible: Mapped[str | None] = mapped_column(String(255))
    dependencies: Mapped[dict | None] = mapped_column(JSONB)
    deliverable_e_code: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str | None] = mapped_column(String(50))
    blockers: Mapped[dict | None] = mapped_column(JSONB)
    # --- Motor 17 additions ---
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True,
    )
    effort_platform_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_critical_path: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    slack_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    progress_pct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    baseline_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    baseline_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    milestone_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    blocker_description: Mapped[str | None] = mapped_column(Text, nullable=True)


class ChangeRequest(FullMixin, Base):
    """Solicitud formal de cambio (M17)."""

    __tablename__ = "change_requests"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"),
        nullable=False, index=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_plans.id"),
        nullable=False, index=True,
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    impacto_plazo_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impacto_esfuerzo_horas: Mapped[float | None] = mapped_column(Float, nullable=True)
    impacto_presupuesto_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="propuesto", server_default="propuesto",
    )
    solicitado_por: Mapped[str] = mapped_column(String(200), nullable=False)
    aprobado_por: Mapped[str | None] = mapped_column(String(200), nullable=True)
    aprobado_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )

    __table_args__ = (
        Index("ix_change_requests_project_estado", "project_id", "estado"),
    )


class ProjectRisk(FullMixin, Base):
    __tablename__ = "project_risks"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    risk_code: Mapped[str] = mapped_column(String(20), nullable=False)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    probabilidad: Mapped[float | None] = mapped_column(Float)
    impacto_dias: Mapped[int | None] = mapped_column(Integer)
    impacto_euros: Mapped[float | None] = mapped_column(Numeric(10, 2))
    categoria: Mapped[str | None] = mapped_column(String(50))
    owner: Mapped[str | None] = mapped_column(String(255))
    trigger_condicion: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(50))
    mitigation_plan: Mapped[dict | None] = mapped_column(JSONB)
    contingency_plan: Mapped[dict | None] = mapped_column(JSONB)
    materialization_evidence: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        doc="Evidencia de materialización del riesgo: trigger_evidence, materialized_by, timestamp. Separado del contingency_plan que es el PLAN puro.",
    )
    closure_evidence: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        doc="Evidencia de cierre: resolution_notes, closed_by, timestamp. Separado del mitigation_plan que es el PLAN puro.",
    )
    materializado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    cerrado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class StatusReport(FullMixin, Base):
    __tablename__ = "status_reports"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    tipo: Mapped[str | None] = mapped_column(String(50))
    # weekly_sponsor | monthly_comite | quarterly_direccion
    # | compliance_resources | quick_wins
    destinatario_rol: Mapped[str | None] = mapped_column(String(100))
    # sponsor | comite_seguridad | direccion | cliente_general
    periodo_inicio: Mapped[date | None] = mapped_column(Date)
    periodo_fin: Mapped[date | None] = mapped_column(Date)
    contenido_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    semaforo_rag: Mapped[str | None] = mapped_column(String(10))
    # green | amber | red (solo para quarterly)
    docx_path: Mapped[str | None] = mapped_column(String(500))
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    contenido_path: Mapped[str | None] = mapped_column(String(500))
    estado: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    # draft → generated → reviewed → sent
    generado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    revisado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    abierto_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    fecha_generacion: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    enviado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    leido_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
