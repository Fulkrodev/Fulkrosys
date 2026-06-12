"""Core models: clients, projects, systems, categorization."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    String,
    Text,
    Date,
    Integer,
    Numeric,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, FullMixin


class Client(FullMixin, Base):
    __tablename__ = "clients"
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    cif: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    # #7 · CIF normalizado para dedup robusto lead↔cliente (espejo de Lead.cif_norm).
    cif_norm: Mapped[str | None] = mapped_column(String(20), index=True)
    sector: Mapped[str | None] = mapped_column(String(100))
    provincia: Mapped[str | None] = mapped_column(String(100))
    numero_empleados: Mapped[int | None] = mapped_column(Integer)
    contacto_email: Mapped[str | None] = mapped_column(String(255))
    contacto_telefono: Mapped[str | None] = mapped_column(String(50))
    # #7.5 · datos que el wizard (StepDatosCliente) recoge y antes se tiraban.
    # Consultables para encabezado legal de contratos + paquetes ENAC/CCN-STIC-809.
    domicilio_fiscal: Mapped[str | None] = mapped_column(String(255))
    web: Mapped[str | None] = mapped_column(String(255))
    persona_contacto: Mapped[str | None] = mapped_column(String(255))
    lead_source: Mapped[str | None] = mapped_column(String(100))
    # Corporate identity (uploaded via POST /api/v1/clients/{id}/logo).
    logo_path: Mapped[str | None] = mapped_column(String(512))
    logo_mime_type: Mapped[str | None] = mapped_column(String(80))
    logo_sha256: Mapped[str | None] = mapped_column(String(64))
    # SAN-E MB-9 atom 9.1 · per-cliente branding (Q1.B + Q2.C)
    primary_color: Mapped[str | None] = mapped_column(String(7))
    secondary_color: Mapped[str | None] = mapped_column(String(7))
    footer_text: Mapped[str | None] = mapped_column(Text)
    # SAN-E MB-9.bis atom 9.bis.3 · DPA Article 28 GDPR sign tracking
    dpa_signed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    dpa_version: Mapped[str | None] = mapped_column(String(20))
    dpa_signed_minio_path: Mapped[str | None] = mapped_column(Text)
    projects: Mapped[list["Project"]] = relationship(back_populates="client")


class Project(FullMixin, Base):
    __tablename__ = "projects"
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    # Workflow phase persisted (ADR-026 · 8 fases lifecycle plan v4.2 +
    # CHECK constraint enum + NOT NULL post-migration 2ddffdcdddfc).
    # Source of truth primaria para get_current_phase() · CASCADE
    # fallback en workflow_gates.py si fase desactualizada vs motors.
    fase: Mapped[str] = mapped_column(
        String(50), server_default=text("'pre_venta'"), nullable=False,
    )
    fecha_kickoff: Mapped[date | None] = mapped_column(Date)
    fecha_objetivo_certificacion: Mapped[date | None] = mapped_column(Date)
    categoria_objetivo: Mapped[str | None] = mapped_column(String(10))
    # #7 · papel ante la AAPP, arrastrado desde Lead.papel_aapp en la promoción.
    # Criterio de categorización consumido en lógica de negocio (project-scoped).
    papel_aapp: Mapped[str | None] = mapped_column(String(40))
    # #5 (Sub-bloque E) · suelo de categoría heredado de la AAPP contratante
    # (BASICA/MEDIA/ALTA · NULL = sin herencia). Piso DURO: la categorización
    # computada (regla del máximo Anexo I RD 311/2022) solo puede SUBIR por
    # encima, nunca declararse por debajo de lo que la Administración asignó al
    # servicio. Capturado por Marcos en Fase 1 desde el pliego/contrato (decisión
    # A · criterio de consultor informado). Sibling de papel_aapp.
    categoria_heredada_aapp: Mapped[str | None] = mapped_column(String(10))
    estado: Mapped[str | None] = mapped_column(String(50), default="draft")
    # --- Motor 25 Project Lifecycle ---
    lifecycle_state: Mapped[str | None] = mapped_column(String(30), default="DRAFT")
    # DRAFT | NEGOTIATING | SIGNED | ACTIVE | CERTIFIED | RETAINER
    # | ENDED_RENEWAL_OK | ENDED_CHURN | ARCHIVED | PURGED
    # Paso 4 — campos de cierre honesto (grace period 8 meses):
    certified_at: Mapped[date | None] = mapped_column(Date)
    # Sesión 3B-2B.6 Cluster 1 Phase 2 · audit-passed admin tracking (audit Phase 0
    # DIM 4 critical gap A resolved). Marcos marca auditoría pasada · state transition
    # UNDER_REVIEW → CONFORMANT · trigger retainer offer (Phase 3 workflow hook).
    audit_passed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    audit_passed_by: Mapped[str | None] = mapped_column(String(255))
    audit_result: Mapped[str | None] = mapped_column(String(30))
    # passed | observed | correction_required | failed (DB CHECK constraint)
    audit_report_ref: Mapped[str | None] = mapped_column(String(120))
    grace_period_started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    grace_period_ends_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    sponsor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # SAN-C MB-11.6 · 6 arquetipos PYME formal classification (Manual ENS).
    archetype: Mapped[str | None] = mapped_column(String(50))
    archetype_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    # SAN-E v3.MB-6 atom 3 · LUCIA opt-in CCN-CERT federation (admin toggle)
    # Default False · ICP empresas privadas concursantes AAPP típicamente
    # SIN credentials LUCIA · fallback manual notification E-CCN-NOTIFY template.
    lucia_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"),
    )
    # SAN-E MB-8 atom 8.1 · WhatsApp Business per-project opt-in toggle
    whatsapp_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"),
    )
    # === Sub-atom 1.C.D.A.0 v3.8 · 19 dimensiones adaptación (Anexo L) ===
    # 3 dims existing arriba (categoria_objetivo · archetype · fase) + 16 nuevas
    # capturadas distribuida (m13 + m_meetings pre-venta · m16 onboarding cliente
    # · admin page consolidada source of truth). Migration projects_19dims_1c_d_a0_001.
    tamano_empleados: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pequeno'"),
    )
    madurez_ens_actual: Mapped[str] = mapped_column(
        String(2), nullable=False, server_default=text("'L0'"),
    )
    geografia_operacion: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'spain'"),
    )
    procesa_datos_sensibles_rgpd9: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"),
    )
    aplica_nis2: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'no'"),
    )
    aplica_dora: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'no'"),
    )
    aplica_ai_act: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'no'"),
    )
    dpo_designado: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'no_designado'"),
    )
    arquitectura_sistemas: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'cloud_native'"),
    )
    multi_tenancy: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'single'"),
    )
    equipo_ti_tamano: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'1_3'"),
    )
    certificaciones_previas: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"),
    )
    urgencia_certificacion: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'6m'"),
    )
    presupuesto_disponible: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'estandar'"),
    )
    compromiso_interno: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'reactivo'"),
    )
    horas_cliente_semana: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'5_15h'"),
    )
    client: Mapped["Client"] = relationship(back_populates="projects")
    systems: Mapped[list["System"]] = relationship(back_populates="project")


class System(FullMixin, Base):
    __tablename__ = "systems"
    __table_args__ = (
        UniqueConstraint('project_id', 'nombre', name='uq_systems_project_id_nombre'),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    frontera: Mapped[str | None] = mapped_column(Text)
    project: Mapped["Project"] = relationship(back_populates="systems")
    information_types: Mapped[list["InformationType"]] = relationship(back_populates="system")
    services: Mapped[list["Service"]] = relationship(back_populates="system")
    categorizations: Mapped[list["Categorization"]] = relationship(back_populates="system")
    sites: Mapped[list["SystemSite"]] = relationship(back_populates="system")
    scope_exclusions: Mapped[list["ScopeExclusion"]] = relationship(back_populates="system")


class InformationType(FullMixin, Base):
    __tablename__ = "information_types"
    system_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("systems.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    valoracion_d: Mapped[str | None] = mapped_column(String(10))
    valoracion_i: Mapped[str | None] = mapped_column(String(10))
    valoracion_c: Mapped[str | None] = mapped_column(String(10))
    valoracion_a: Mapped[str | None] = mapped_column(String(10))
    valoracion_t: Mapped[str | None] = mapped_column(String(10))
    justificacion: Mapped[str | None] = mapped_column(Text)
    system: Mapped["System"] = relationship(back_populates="information_types")


class Service(FullMixin, Base):
    __tablename__ = "services"
    __table_args__ = (
        # R05 (E-155) · clasificación CCN-STIC 803: servicio finalista (presta el
        # fin del sistema) vs instrumental (soporta a otros). Nullable: legacy +
        # categorización inicial pueden no haberlo fijado todavía.
        CheckConstraint(
            "tipo IS NULL OR tipo IN ('finalista', 'instrumental')",
            name="ck_services_tipo",
        ),
    )
    system_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("systems.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    valoracion_d: Mapped[str | None] = mapped_column(String(10))
    valoracion_i: Mapped[str | None] = mapped_column(String(10))
    valoracion_c: Mapped[str | None] = mapped_column(String(10))
    valoracion_a: Mapped[str | None] = mapped_column(String(10))
    valoracion_t: Mapped[str | None] = mapped_column(String(10))
    justificacion: Mapped[str | None] = mapped_column(Text)
    # R05 · finalista | instrumental (alcance E-155). Ver CheckConstraint arriba.
    tipo: Mapped[str | None] = mapped_column(String(20))
    system: Mapped["System"] = relationship(back_populates="services")


class Categorization(FullMixin, Base):
    __tablename__ = "categorizations"
    system_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("systems.id"), nullable=False)
    categoria_resultante: Mapped[str] = mapped_column(String(10), nullable=False)
    fecha_acta: Mapped[date | None] = mapped_column(Date)
    aprobado_por: Mapped[str | None] = mapped_column(String(255))
    version: Mapped[int | None] = mapped_column(Integer, default=1)
    input_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    signature_magic_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
        doc="FK logica (sin constraint) al magic_link de firma E-012. Re-integracion M1+M12.",
    )
    system: Mapped["System"] = relationship(back_populates="categorizations")


class SystemSite(FullMixin, Base):
    """Sede física o región cloud dentro del alcance del SGSI (R05 · E-155 §3.3).

    Modelo estructurado de ubicaciones (CCN-STIC 805/803). ``tipo`` distingue
    sede física (con dirección postal) de región cloud (proveedor/región). En
    categoría ALTA se exigen ubicaciones reales (dirección + país). Aislamiento
    RLS por proyecto vía el padre ``systems`` (mirror de ``services``).
    """
    __tablename__ = "system_sites"
    __table_args__ = (
        CheckConstraint(
            "tipo IS NULL OR tipo IN ('sede_fisica', 'region_cloud')",
            name="ck_system_sites_tipo",
        ),
    )
    system_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("systems.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str | None] = mapped_column(String(20))
    direccion: Mapped[str | None] = mapped_column(Text)
    pais: Mapped[str | None] = mapped_column(String(100))
    descripcion: Mapped[str | None] = mapped_column(Text)
    system: Mapped["System"] = relationship(back_populates="sites")


class ScopeExclusion(FullMixin, Base):
    """Exclusión justificada del alcance del SGSI (R05 · E-155 §4 · CCN-STIC 805).

    Toda exclusión del alcance debe justificarse. Antes solo vivía como nombres
    en ``contracts.alcance_snapshot``; aquí queda estructurada y editable.
    Aislamiento RLS por proyecto vía el padre ``systems``.
    """
    __tablename__ = "scope_exclusions"
    system_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("systems.id"), nullable=False)
    elemento: Mapped[str] = mapped_column(String(255), nullable=False)
    justificacion: Mapped[str | None] = mapped_column(Text)
    system: Mapped["System"] = relationship(back_populates="scope_exclusions")


class PolicyAcknowledgment(FullMixin, Base):
    """Acuse de recibo de normativa por empleado (R14 · mp.per.3 · PSI §11.b).

    Evidencia que cada persona con acceso al sistema ha recibido y aceptado las
    normativas de seguridad (uso aceptable, contraseñas, teletrabajo, etc.). El
    auditor ENAC lo exige como prueba de la medida mp.per.3 (Concienciación) y
    org.3. Project-scoped (RLS por ``project_id``/``client_id``) · lo administra
    el consultor (registra/importa los acuses firmados por el personal del
    cliente · identidad + fecha + versión del documento).
    """
    __tablename__ = "policy_acknowledgments"
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id"), nullable=False, index=True,
    )
    documento_codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    documento_version: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="1.0", default="1.0",
    )
    empleado_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    empleado_identidad: Mapped[str | None] = mapped_column(String(255))
    empleado_departamento: Mapped[str | None] = mapped_column(String(255))
    fecha_acuse: Mapped[date] = mapped_column(Date, nullable=False)
    medio: Mapped[str | None] = mapped_column(String(40))
    notas: Mapped[str | None] = mapped_column(Text)
