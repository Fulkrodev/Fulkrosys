"""Commercial cycle: leads, proposals, contracts, billing.

M13 Commercial Doc Factory + M14 Contracts Engine + M15 Billing Engine.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, Float, Integer, Boolean, Numeric, Date, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class Lead(FullMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_convertido_proyecto", "convertido_a_proyecto_id"),
        Index("ix_leads_estado_contacto", "estado_contacto"),
        Index("ix_leads_temperature_level", "temperature_level"),
        # §2.2: el CHECK existe en BD (sand_crm_lead_extensions) pero faltaba en
        # el ORM (drift) · declararlo alinea modelo↔BD (mismo nombre → sin diff
        # de autogenerate).
        CheckConstraint(
            "estado_contacto IS NULL OR estado_contacto IN ("
            "'nuevo', 'enviado', 'respondio', 'reunion_agendada', "
            "'propuesta_enviada', 'ganado', 'descartado', 'no_interesa')",
            name="ck_leads_estado_contacto",
        ),
    )
    empresa_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    empresa_cif: Mapped[str | None] = mapped_column(String(20))
    sector: Mapped[str | None] = mapped_column(String(100))
    tamano_estimado: Mapped[str | None] = mapped_column(String(50))
    contacto_email: Mapped[str | None] = mapped_column(String(255))
    contacto_telefono: Mapped[str | None] = mapped_column(String(50))
    origen: Mapped[str | None] = mapped_column(String(100))
    estado: Mapped[str | None] = mapped_column(String(50), default="nuevo")
    lead_score: Mapped[float | None] = mapped_column(Float)
    clasificacion_abc: Mapped[str | None] = mapped_column(String(1))
    notas: Mapped[str | None] = mapped_column(Text)
    asignado_a: Mapped[str | None] = mapped_column(String(255))
    fecha_entrada: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    fecha_ultima_actualizacion: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # ──────────────────────────────────────────────────────────────
    # SAN-D MB-19.1 · CRM workflow comercial extension (ADR-041)
    # ──────────────────────────────────────────────────────────────
    # estado_contacto: workflow 8 estados FASE 8.5 C2 v2 (CheckConstraint
    # dominio comercial):
    # nuevo · enviado · respondio · reunion_agendada · propuesta_enviada
    # · ganado · descartado · no_interesa.
    estado_contacto: Mapped[str | None] = mapped_column(String(50))
    primer_contacto_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    fecha_perdida: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    razon_perdida: Mapped[str | None] = mapped_column(String(200))
    fecha_conversion: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    convertido_a_proyecto_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"),
    )
    # temperature_level: 1-7 prioridad comercial del lead
    # (BAJA=1 · MEDIA=2-3 · ALTA=4-6 · MUY_ALTA=7).
    temperature_level: Mapped[int | None] = mapped_column(Integer)
    categoria_objetivo_ens: Mapped[str | None] = mapped_column(String(20))
    archetype_ens: Mapped[str | None] = mapped_column(String(50))
    # #7 · CIF normalizado (mayúsculas, sin espacios/guiones) = clave de dedup
    # robusta lead↔cliente (evita proyectos duplicados por formato de CIF distinto).
    cif_norm: Mapped[str | None] = mapped_column(String(20), index=True)
    # #7 · papel ante la AAPP (aloja datos / software / SaaS gestionado) capturado en
    # el cuestionario (q-papel_aapp). Criterio de categorización · usado YA en fase
    # lead; se arrastra a Project.papel_aapp en la promoción.
    papel_aapp: Mapped[str | None] = mapped_column(String(40))


class Proposal(FullMixin, Base):
    __tablename__ = "proposals"
    __table_args__ = (
        Index("ix_proposals_lead_active", "lead_id", "superseded"),
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id"), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    plantilla_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    pricing_model_id: Mapped[str | None] = mapped_column(String(50))
    categoria_objetivo: Mapped[str | None] = mapped_column(String(10))
    alcance: Mapped[dict | None] = mapped_column(JSONB)
    duracion_semanas: Mapped[int | None] = mapped_column(Integer)
    effort_marcos_horas: Mapped[float | None] = mapped_column(Float)
    importe_total: Mapped[float | None] = mapped_column(Numeric(12, 2))
    importe_desglose: Mapped[dict | None] = mapped_column(JSONB)
    hitos_pago: Mapped[dict | None] = mapped_column(JSONB)
    validez_hasta: Mapped[date | None] = mapped_column(Date)
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    docx_path: Mapped[str | None] = mapped_column(String(500))
    enviado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    abierto_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    notas_marcos: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str | None] = mapped_column(String(50), default="draft")

    # ──────────────────────────────────────────────────────────────
    # SAN-D MB-19.1 · revisions tracking extension (ADR-041)
    # ──────────────────────────────────────────────────────────────
    feedback_cliente: Mapped[str | None] = mapped_column(Text)
    cambios_desde_anterior: Mapped[str | None] = mapped_column(Text)
    superseded: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false",
    )
    fecha_aceptacion: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    agent_19_metadata: Mapped[dict | None] = mapped_column(JSONB)


class Contract(FullMixin, Base):
    __tablename__ = "contracts"
    lead_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("leads.id"))
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("proposals.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    tipo: Mapped[str | None] = mapped_column(String(50))
    plantilla_id: Mapped[str | None] = mapped_column(String(20))
    cliente_firmante_nombre: Mapped[str | None] = mapped_column(String(255))
    cliente_firmante_cargo: Mapped[str | None] = mapped_column(String(255))
    clausula_recursos: Mapped[dict | None] = mapped_column(JSONB)
    parametros_xyzpr: Mapped[dict | None] = mapped_column(JSONB)
    docx_path: Mapped[str | None] = mapped_column(String(500))
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    hash_sha256: Mapped[str | None] = mapped_column(String(64))
    # #10 B1 · alcance COMERCIAL congelado al generar (categoría + dimensiones de
    # la Proposal · §1 del contrato · distinto del alcance ENS narrativo E-155).
    alcance_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    # #43 · hash SHA-256 sobre los BYTES del DOCX/PDF canónico (lo firma m05).
    documento_sha256: Mapped[str | None] = mapped_column(String(64))
    # #43 · puente Contract → SigningIntent (m05 canvas Ed25519 · M-OLA2-C). El
    # intent lleva documento_sha256 como document_hash_sha256; el reverso ya es
    # gratis vía SigningIntent.signable_ref_id/type='contract'. Nullable.
    signing_intent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("signing_intents.id", ondelete="SET NULL"),
    )
    firmado_marcos_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    firmado_cliente_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    firmado_cliente_link_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    vigente_desde: Mapped[date | None] = mapped_column(Date)
    vigente_hasta: Mapped[date | None] = mapped_column(Date)
    estado: Mapped[str | None] = mapped_column(String(50), default="draft")
    adendas: Mapped[dict | None] = mapped_column(JSONB)
    scan_window: Mapped[dict | None] = mapped_column(JSONB)
    # Format ScanWindow Pydantic · m14_contracts/schemas.py · SAN-B.MB-3.bis.3


class Invoice(FullMixin, Base):
    __tablename__ = "invoices"
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    contract_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contracts.id"))
    numero_correlativo: Mapped[str | None] = mapped_column(String(30))
    tipo: Mapped[str | None] = mapped_column(String(50))
    concepto: Mapped[str | None] = mapped_column(Text)
    base_imponible: Mapped[float | None] = mapped_column(Numeric(12, 2))
    iva_percent: Mapped[float | None] = mapped_column(Float)
    iva_importe: Mapped[float | None] = mapped_column(Numeric(12, 2))
    irpf_percent: Mapped[float | None] = mapped_column(Float)
    irpf_importe: Mapped[float | None] = mapped_column(Numeric(12, 2))
    total: Mapped[float | None] = mapped_column(Numeric(12, 2))
    fecha_emision: Mapped[date | None] = mapped_column(Date)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date)
    estado_pago: Mapped[str | None] = mapped_column(String(50))
    verifactu_hash: Mapped[str | None] = mapped_column(String(64))
    verifactu_enviado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    # FIX P1-7: timestamp DEDICADO del envío del email/notificación de la factura
    # al cliente (antes se reutilizaba verifactu_enviado_at · semántica VeriFactu).
    email_enviado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class PricingModel(FullMixin, Base):
    """Catálogo de modelos económicos (Apéndice M spec v2.1).

    Tabla creada con schema pero poblada desde in-memory PRICING_CATALOG.
    Permite override / customización futura por cliente.
    """
    __tablename__ = "pricing_models"
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    aplicable_categoria: Mapped[dict | None] = mapped_column(JSONB)
    formula: Mapped[dict | None] = mapped_column(JSONB)
    rango_precio_min: Mapped[float | None] = mapped_column(Numeric(12, 2))
    rango_precio_max: Mapped[float | None] = mapped_column(Numeric(12, 2))
    hitos_pago: Mapped[dict | None] = mapped_column(JSONB)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class InvoiceLine(FullMixin, Base):
    """Líneas de factura (M15)."""
    __tablename__ = "invoice_lines"
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    cantidad: Mapped[float] = mapped_column(Numeric(10, 2), default=1.0, nullable=False)
    precio_unitario: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    hito_asociado: Mapped[str | None] = mapped_column(String(100))
    paron_asociado: Mapped[str | None] = mapped_column(String(100))
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ClientCommitment(FullMixin, Base):
    """Compromisos XYZPR del cliente vinculados a contratos (M14)."""
    __tablename__ = "client_commitments"
    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    tipo: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    parametro: Mapped[str | None] = mapped_column(String(100))
    valor_esperado: Mapped[str | None] = mapped_column(String(255))
    valor_actual: Mapped[str | None] = mapped_column(String(255))
    cumplido: Mapped[bool | None] = mapped_column(Boolean)
    ultima_verificacion_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class PaymentReminder(FullMixin, Base):
    """Recordatorios de pago automáticos (M15)."""
    __tablename__ = "payment_reminders"
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    dias_vencida: Mapped[int] = mapped_column(Integer, nullable=False)
    template_usado: Mapped[str | None] = mapped_column(String(100))
    enviado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    canal: Mapped[str | None] = mapped_column(String(50))
    contenido: Mapped[str | None] = mapped_column(Text)


class LeadStageHistory(Base):
    """Audit trail movements estado_contacto per Lead (SAN-D MB-19.1 · ADR-041).

    Append-only log per transición workflow comercial · análogo
    billing_milestones audit pattern. Permite trazabilidad granular
    Marcos: "cuándo este lead pasó de respondio a reunion_agendada · qué
    notas dejé · qué metadata adjunta".

    Mismo CheckConstraint 8 estados que leads.estado_contacto ·
    coherencia dominio comercial v2 FASE 8.5 C2.
    """

    __tablename__ = "lead_stage_history"
    __table_args__ = (
        Index(
            "ix_lead_stage_history_lead_recent",
            "lead_id", text("created_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False,
    )
    estado_anterior: Mapped[str | None] = mapped_column(String(50))
    estado_nuevo: Mapped[str] = mapped_column(String(50), nullable=False)
    cambiado_por_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True)
    )
    notas: Mapped[str | None] = mapped_column(Text)
    metadata_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
