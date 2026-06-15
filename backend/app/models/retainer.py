"""Retainer management post-certification (M23).

4 perfiles: R_LITE, R_STD, R_PLUS, R_CRITICAL.
Renewal clock + drift detector + dashboard multi-cliente.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, String, Integer, Float, Boolean, Numeric, Date, Text, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import (
    Base,
    ClientReviewMixinA,
    FullMixin,
)


class RetainerContract(FullMixin, Base):
    __tablename__ = "retainer_contracts"
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), index=True,
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contracts.id"))
    # Perfil retainer (addendum v2.2)
    perfil: Mapped[str | None] = mapped_column(String(20), default="R_STD")
    # R_LITE | R_STD | R_PLUS | R_CRITICAL
    modalidad: Mapped[str | None] = mapped_column(String(50), default="mensual")
    # mensual | trimestral | anual
    precio_mensual: Mapped[float | None] = mapped_column(Numeric(10, 2))
    inicio: Mapped[date | None] = mapped_column(Date)
    fin: Mapped[date | None] = mapped_column(Date)
    renovacion_automatica: Mapped[bool | None] = mapped_column(Boolean, default=True)
    sla_respuesta_horas: Mapped[int | None] = mapped_column(Integer)
    estado: Mapped[str | None] = mapped_column(String(20), default="active")
    # active | paused | expired | cancelled
    # Renewal clock
    next_renewal_date: Mapped[date | None] = mapped_column(Date)
    renewal_status: Mapped[str | None] = mapped_column(String(30))
    # null | T_MINUS_180 | T_MINUS_120 | T_MINUS_90 | T_MINUS_60 | T_MINUS_30
    # | RENEWED | LAPSED
    # Semáforo global
    rag_status: Mapped[str | None] = mapped_column(String(10), default="green")
    # green | amber | red
    # Métricas
    horas_consumidas_total: Mapped[float | None] = mapped_column(Float, default=0.0)
    horas_previstas_anual: Mapped[float | None] = mapped_column(Float, default=40.0)


class RetainerActivity(FullMixin, Base):
    __tablename__ = "retainer_activities"
    retainer_contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("retainer_contracts.id"), nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), index=True,
    )
    tipo_actividad: Mapped[str | None] = mapped_column(String(100), index=True)
    titulo: Mapped[str | None] = mapped_column(String(300))
    descripcion: Mapped[str | None] = mapped_column(Text)
    fecha_programada: Mapped[date | None] = mapped_column(Date, index=True)
    fecha_ejecutada: Mapped[date | None] = mapped_column(Date)
    estado: Mapped[str | None] = mapped_column(String(20), default="programada")
    # programada → en_curso → completada | cancelada | vencida
    horas_estimadas: Mapped[float | None] = mapped_column(Float, default=0.0)
    horas_consumidas: Mapped[float | None] = mapped_column(Float, default=0.0)
    evidencia_path: Mapped[str | None] = mapped_column(String(500))
    resultado: Mapped[str | None] = mapped_column(Text)
    prioridad: Mapped[str | None] = mapped_column(String(10), default="normal")
    # baja | normal | alta | urgente


class RetainerDriftEvent(FullMixin, Base):
    """Drift detector (addendum v2.2 §6.4.5.B)."""
    __tablename__ = "retainer_drift_events"

    retainer_contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("retainer_contracts.id"), nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    dimension: Mapped[str] = mapped_column(String(30), nullable=False)
    # infraestructura | identidad | proveedores | normativa | overlay
    # | cpstic | roles | continuidad | evidencias | contratos
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    severidad: Mapped[str] = mapped_column(String(10), nullable=False)
    # LOW | MEDIUM | HIGH | CRITICAL
    impacto: Mapped[str] = mapped_column(String(20), nullable=False)
    # EVIDENCE | DOCUMENT | CONTROL | ROUTE | AUDIT
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    # open | acknowledged | in_progress | resolved | accepted_risk
    resuelto_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class RetainerBillingEvent(FullMixin, Base):
    """Historico facturacion recurrente por retainer (Sesion 8 §2.1).

    Cada evento captura una factura emitida para un periodo concreto
    del retainer. FK a invoices(M15) cuando la factura se genera con
    QR Verifactu.
    """

    __tablename__ = "retainer_billing_events"

    retainer_contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("retainer_contracts.id"), nullable=False, index=True,
    )
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
    )
    billing_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    billing_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="emitted",
    )
    # emitted | paid | overdue | disputed | cancelled
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class RetainerQuarterlyReport(ClientReviewMixinA, FullMixin, Base):
    """Reporte trimestral/anual al cliente (E-801 / E-802).

    SAN-E v3.MB-6 atom 4 · trimestral uniforme + admin curate + cliente signoff.
    ClientReviewMixinA · 8ª aplicación pattern atomic.

    Workflow admin_curation_status (3 estados):
      draft → curated_by_admin → sent_to_client

    Cliente review MixinA · sólo visible cuando admin_curation_status='sent_to_client'.
    Firma `retainer_quarterly_signoff` (step-up OTP · audit ENAC trimestral).

    `summary_jsonb` schema_version v1.0 cement:
      - actividades · incidents · vulnerabilidades · normativa_changes · rag_overall
      - bonus stakeholder_changes + evidence_freshness (Q3-extra)
    """

    __tablename__ = "retainer_quarterly_reports"
    __table_args__ = (
        # Atom 4 retainer · MB-7.0.bis aligned (note: BD index uses 'retainer_quarterly'
        # prefix legacy NOT 'retainer_quarterly_reports').
        Index(
            "idx_retainer_quarterly_client_review",
            "project_id", "client_review_status",
            postgresql_where=text("client_review_status IS NOT NULL"),
        ),
        Index(
            "idx_retainer_quarterly_admin_pending",
            "project_id", "admin_curation_status",
            postgresql_where=text("admin_curation_status = 'draft'"),
        ),
        Index(
            "uq_retainer_quarterly_project_period",
            "project_id", "period_quarter",
            unique=True,
            postgresql_where=text("period_quarter IS NOT NULL"),
        ),
    )

    retainer_contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("retainer_contracts.id"), nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    period_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="trimestral",
    )
    # trimestral | anual | extraordinario
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    period_quarter: Mapped[str | None] = mapped_column(String(7))  # 'YYYY-QN'
    activities_completed: Mapped[int] = mapped_column(Integer, default=0)
    activities_pending: Mapped[int] = mapped_column(Integer, default=0)
    activities_overdue: Mapped[int] = mapped_column(Integer, default=0)
    incidents_detected: Mapped[int] = mapped_column(Integer, default=0)
    normativa_changes_relevant: Mapped[int] = mapped_column(Integer, default=0)
    vulns_critical: Mapped[int] = mapped_column(Integer, default=0)
    rag_overall: Mapped[str | None] = mapped_column(String(10), nullable=True)
    report_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    sent_to_magic_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    summary_jsonb: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    schema_version: Mapped[str] = mapped_column(
        String(8), nullable=False, default="1.0",
    )

    # Admin curation workflow (Q4-extra obligatorio · atom 4)
    admin_curation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft",
    )
    admin_curated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    admin_curated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )

    # Cliente firma link
    client_signing_intent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )


class PricingCatalog(FullMixin, Base):
    """Catalogo de precios vigente (implantacion + retainer + extras).

    Reemplaza pricing hardcoded; consumido por M13/M14/M15 (Paso 6) y
    por retainer_service (Paso 2) para buscar el precio del tier.

    Fuente de verdad de precios (§4.3): tabla ``pricing_config`` (editable en
    /admin/settings/pricing) + ``backend.app.core.pricing.rules.BASE_PRICES``
    (canónico unificado 2026-06-11 · BÁSICA 3.200 / MEDIA 10.700 / ALTA 22.800).
    NO hardcodear importes aquí (los seeds de 2026-04-21 quedaron obsoletos).
    """

    __tablename__ = "pricing_catalog"
    __table_args__ = (
        Index(
            "uq_pricing_catalog_category_tier_active",
            "category", "tier_code", "effective_from",
            unique=True,
        ),
    )

    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    # implantacion | retainer | complementario
    tier_code: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), default="EUR", nullable=False,
    )
    billing_unit: Mapped[str] = mapped_column(
        String(20), default="mensual", nullable=False,
    )
    # mensual | proyecto_fijo | hora | evento
    extras_jsonb: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[str] = mapped_column(String(20), default="2026-04-21")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
