"""
Motor 2 — MAGERIT v3 Risk Engine: SQLAlchemy models.

11 tables for the complete MAGERIT risk analysis lifecycle:
- Catalog tables (precargadas): magerit_asset_types, magerit_threats, magerit_safeguards, magerit_ens_mapping
- Analysis tables (por proyecto): magerit_analysis, magerit_assets, magerit_asset_dependencies,
  magerit_threat_assessment, magerit_safeguard_deployment, magerit_risk_calculation, magerit_treatment_plan
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, ForeignKey, Index, Numeric, String, Text, Float, Integer, Date,
    UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import (
    Base, ClientReviewMixinA, FullMixin, TimestampMixin, UUIDPrimaryKeyMixin,
)


# === CATALOG TABLES (precargadas desde YAML) ===

class MageritAssetType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Catálogo de tipos de activos MAGERIT. Libro II, Cap 2."""
    __tablename__ = "magerit_asset_types"
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_code: Mapped[str] = mapped_column(String(10), nullable=False)  # S, D, SW, HW, COM, SI, AUX, L, P
    description: Mapped[str | None] = mapped_column(Text)
    default_dimensions: Mapped[dict | None] = mapped_column(JSONB)  # {"D": true, "I": true, "C": false, ...}


class MageritThreat(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Catálogo de amenazas MAGERIT. Libro II, Cap 5."""
    __tablename__ = "magerit_threats"
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)  # N.1, I.5, E.20, A.11
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    group_code: Mapped[str] = mapped_column(String(5), nullable=False)  # N, I, E, A
    description: Mapped[str | None] = mapped_column(Text)
    affected_asset_types: Mapped[dict | None] = mapped_column(JSONB)  # ["HW", "SW", "COM"]
    affected_dimensions: Mapped[dict | None] = mapped_column(JSONB)  # ["D", "I", "C"]
    typical_frequency: Mapped[str | None] = mapped_column(String(20))  # muy_baja, baja, media, alta, muy_alta
    # --- Libro II traceability (Bloque 15) ---
    official_description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        doc="Descripcion literal del MAGERIT v3 Libro II (NIPO 630-12-171-8). "
            "Para auditoria ENAC. No sobreescribe description (version resumida para UI).",
    )
    official_source: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        doc="Referencia a seccion exacta del Libro II (ej: 'seccion 5.4.9').",
    )


class MageritSafeguard(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Catálogo de salvaguardas MAGERIT. Libro II, Cap 6."""
    __tablename__ = "magerit_safeguards"
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # H.IA, D.C, COM.FW
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    family: Mapped[str] = mapped_column(String(10), nullable=False)  # H, D, K, S, SW, HW, COM, IP, MP, AUX, L, PS, G, BC, E, NEW
    description: Mapped[str | None] = mapped_column(Text)
    protects_asset_types: Mapped[dict | None] = mapped_column(JSONB)  # ["S", "D", "SW"]
    mitigates_threats: Mapped[dict | None] = mapped_column(JSONB)  # ["A.5", "A.11"]
    efficacy_typical: Mapped[str | None] = mapped_column(String(20))  # bajo, medio, alto, muy_alto


class MageritEnsMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Mapeo salvaguardas MAGERIT → medidas ENS Anexo II."""
    __tablename__ = "magerit_ens_mapping"
    ens_measure: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)  # org.1, op.acc.5, mp.com.2
    ens_measure_name: Mapped[str | None] = mapped_column(String(255))
    magerit_safeguards: Mapped[dict | None] = mapped_column(JSONB)  # ["H.IA", "E.2"]
    confidence: Mapped[str | None] = mapped_column(String(20))  # high, medium, n/a
    notes: Mapped[str | None] = mapped_column(Text)


class MageritRiskMatrix(Base):
    """
    Official MAGERIT v3 qualitative risk matrix.
    Libro III, sec 2.1 "Análisis mediante tablas", p.7.
    25 rows: 5 impact levels × 5 probability levels → risk level.
    Precargada en migración, no modificable.
    """
    __tablename__ = "magerit_risk_matrix"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    impact_level: Mapped[str] = mapped_column(String(2), nullable=False)
    probability_level: Mapped[str] = mapped_column(String(2), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(2), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            'impact_level',
            'probability_level',
            name='uq_risk_matrix_impact_prob',
        ),
    )


# === ANALYSIS TABLES (por proyecto, con RLS) ===

class MageritAnalysis(FullMixin, Base):
    """Cabecera de un análisis de riesgos MAGERIT vinculado a un proyecto."""
    __tablename__ = "magerit_analysis"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, in_progress, completed, approved
    approved_by: Mapped[str | None] = mapped_column(String(255))
    approved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    calculation_mode: Mapped[str] = mapped_column(String(20), default="qualitative")  # qualitative, quantitative, hybrid
    methodology_version: Mapped[str] = mapped_column(String(20), default="MAGERIT v3")
    notes: Mapped[str | None] = mapped_column(Text)
    result_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    snapshot_frozen_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    signature_magic_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
        doc="FK logica (sin constraint) al magic_link de firma E-028. Re-integracion M2+M12.",
    )


class MageritAsset(ClientReviewMixinA, FullMixin, Base):
    """Activo inventariado en un análisis de riesgos.

    Cliente review Pattern A via ClientReviewMixinA (atom 5.4.A).
    CHECK ck_magerit_assets_client_review_status + Index parcial en BD.

    Atom MB-7.0.bis · manual declarations porque pattern A helper assumes
    project_id col · esta tabla usa analysis_id (link via magerit_analysis).
    """
    __tablename__ = "magerit_assets"
    __table_args__ = (
        Index(
            "idx_magerit_assets_client_review",
            "analysis_id", "client_review_status",
            postgresql_where=text("client_review_status IS NOT NULL"),
        ),
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("magerit_analysis.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # Client-specific code
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type_code: Mapped[str] = mapped_column(String(20), nullable=False)  # Reference to catalog
    description: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(255))
    # Valoración cualitativa DICAT (0-10 per valuation_scales.yaml)
    value_d: Mapped[int | None] = mapped_column(Integer)  # Disponibilidad
    value_i: Mapped[int | None] = mapped_column(Integer)  # Integridad
    value_c: Mapped[int | None] = mapped_column(Integer)  # Confidencialidad
    value_a: Mapped[int | None] = mapped_column(Integer)  # Autenticidad
    value_t: Mapped[int | None] = mapped_column(Integer)  # Trazabilidad
    # Valores acumulados (tras propagación de dependencias)
    accumulated_d: Mapped[float | None] = mapped_column(Numeric(10, 4))
    accumulated_i: Mapped[float | None] = mapped_column(Numeric(10, 4))
    accumulated_c: Mapped[float | None] = mapped_column(Numeric(10, 4))
    accumulated_a: Mapped[float | None] = mapped_column(Numeric(10, 4))
    accumulated_t: Mapped[float | None] = mapped_column(Numeric(10, 4))
    # op.pl.5 ALTA · producto/servicio CPSTIC certificado (CCN). Alimenta el gate
    # de transición a CONFORMIDAD para categoría ALTA (feature alta_productos_cpstic).
    cpstic_certified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), default=False,
    )


class MageritAssetDependency(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Dependencia entre activos (grafo dirigido). Superior depende de inferior."""
    __tablename__ = "magerit_asset_dependencies"
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("magerit_analysis.id"), nullable=False)
    superior_asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("magerit_assets.id"), nullable=False)
    inferior_asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("magerit_assets.id"), nullable=False)
    dependency_degree: Mapped[float] = mapped_column(Float, default=1.0)  # 0.0-1.0
    reason: Mapped[str | None] = mapped_column(Text)


class MageritThreatAssessment(ClientReviewMixinA, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Valoración de (activo, amenaza): probabilidad y degradación por dimensión.

    Cliente review Pattern A via ClientReviewMixinA (atom 5.4b.A).
    CHECK ck_magerit_threat_assessment_client_review_status + Index parcial en BD.

    Atom MB-7.0.bis · manual declarations (analysis_id · NO project_id).
    """
    __tablename__ = "magerit_threat_assessment"
    __table_args__ = (
        Index(
            "idx_magerit_threat_assessment_client_review",
            "analysis_id", "client_review_status",
            postgresql_where=text("client_review_status IS NOT NULL"),
        ),
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("magerit_analysis.id"), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("magerit_assets.id"), nullable=False)
    threat_code: Mapped[str] = mapped_column(String(10), nullable=False)
    # Probabilidad (escala cualitativa: MB, B, M, A, MA)
    probability: Mapped[str] = mapped_column(String(2), nullable=False)
    # Degradación por dimensión (porcentaje 0-100)
    degradation_d: Mapped[int | None] = mapped_column(Integer)
    degradation_i: Mapped[int | None] = mapped_column(Integer)
    degradation_c: Mapped[int | None] = mapped_column(Integer)
    degradation_a: Mapped[int | None] = mapped_column(Integer)
    degradation_t: Mapped[int | None] = mapped_column(Integer)


class MageritSafeguardDeployment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Despliegue de salvaguarda en un análisis con su eficacia real."""
    __tablename__ = "magerit_safeguard_deployment"
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("magerit_analysis.id"), nullable=False)
    safeguard_code: Mapped[str] = mapped_column(String(20), nullable=False)
    # Estado de implantación
    status: Mapped[str] = mapped_column(String(50), default="planned")  # planned, partial, deployed, verified
    # Eficacia real (0-100%)
    efficacy: Mapped[int] = mapped_column(Integer, default=0)
    # Tipo de efecto: preventiva (reduce probabilidad) o paliativa (reduce degradación)
    effect_type: Mapped[str] = mapped_column(String(20), default="preventive")  # preventive, palliative, both
    responsible: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)


class MageritRiskCalculation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Resultado de cálculo de riesgo para (activo, amenaza, dimensión)."""
    __tablename__ = "magerit_risk_calculation"
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("magerit_analysis.id"), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("magerit_assets.id"), nullable=False)
    threat_code: Mapped[str] = mapped_column(String(10), nullable=False)
    dimension: Mapped[str] = mapped_column(String(1), nullable=False)  # D, I, C, A, T
    # Riesgo intrínseco (antes de salvaguardas)
    impact_intrinsic: Mapped[float | None] = mapped_column(Float)
    risk_intrinsic_accumulated: Mapped[float | None] = mapped_column(Float)
    risk_intrinsic_repercuted: Mapped[float | None] = mapped_column(Float)
    # Riesgo efectivo (después de salvaguardas)
    impact_effective: Mapped[float | None] = mapped_column(Float)
    risk_effective: Mapped[float | None] = mapped_column(Float)
    # Riesgo residual (después del plan de tratamiento)
    risk_residual: Mapped[float | None] = mapped_column(Float)
    # Nivel cualitativo resultante
    risk_level: Mapped[str | None] = mapped_column(String(5))  # MC, C, I, A, D


class MageritEconomicValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Valoración económica de un activo · capa CUANTITATIVA (MAGERIT Libro III sec 2.3).

    feat/fulkro-100 Ola D · gap ALTA. Entrada económica OPCIONAL sobre el análisis
    CUALITATIVO existente (backward-compat · sin esta fila, el análisis sigue siendo
    100% cualitativo y válido). El ALE (Annual Loss Expectancy) se DERIVA on-query
    (no se persiste → sin staleness) combinando ``asset_value_eur`` × ``exposure_factor``
    con la degradación y probabilidad de las amenazas (FREQUENCY_MAP):
        SLE_dim = asset_value_eur × exposure_factor × (degradation_dim / 100)
        ARO     = FREQUENCY_MAP[probability]   (MB=0.01 … MA=365)
        ALE_dim = SLE_dim × ARO
    Determinista (R1 · sin LLM).
    """
    __tablename__ = "magerit_economic_values"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "asset_id",
            name="uq_magerit_economic_analysis_asset",
        ),
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("magerit_analysis.id"), nullable=False, index=True,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("magerit_assets.id"), nullable=False,
    )
    asset_value_eur: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    exposure_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, server_default=text("1.0"),
    )


class MageritTreatmentPlan(FullMixin, Base):
    """Plan de tratamiento para un riesgo no aceptable."""
    __tablename__ = "magerit_treatment_plan"
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("magerit_analysis.id"), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("magerit_assets.id"), nullable=False)
    threat_code: Mapped[str] = mapped_column(String(10), nullable=False)
    dimension: Mapped[str] = mapped_column(String(1), nullable=False)
    current_risk_level: Mapped[str] = mapped_column(String(5), nullable=False)  # MC, C, I, A, D
    current_risk_value: Mapped[float | None] = mapped_column(Float)
    # Decisión de tratamiento
    treatment: Mapped[str] = mapped_column(String(20), nullable=False)  # mitigar, transferir, aceptar, eliminar
    action_description: Mapped[str | None] = mapped_column(Text)
    proposed_safeguards: Mapped[dict | None] = mapped_column(JSONB)  # ["H.IA", "COM.C"]
    target_risk_level: Mapped[str | None] = mapped_column(String(5))
    responsible: Mapped[str | None] = mapped_column(String(255))
    deadline: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, in_progress, completed
