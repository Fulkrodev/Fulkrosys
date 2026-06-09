"""Motor 22 Technical Discovery models.

DiscoveryRun orquesta ejecuciones; DiscoveryAlert captura hallazgos
derivados. Las tablas discovered_assets / discovered_identities
residen en models/onboarding.py (compartidas con M16) y son extendidas
por M22 con columnas adicionales (discovery_run_id, pkg_node_id, etc.).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Float, Integer, String, Text, Index, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB, UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class DiscoveryRun(FullMixin, Base):
    """Ejecucion de discovery tecnico sobre un proyecto."""

    __tablename__ = "discovery_runs_m22"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )

    modules: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    connector_sources: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    progress: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    started_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    triggered_by: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")

    __table_args__ = (
        Index("ix_discovery_runs_m22_project_status", "project_id", "status"),
    )


class DiscoveryAlert(Base):
    """Alerta deterministica generada durante discovery (M22)."""

    __tablename__ = "discovery_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    discovery_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovery_runs_m22.id"),
        nullable=False,
        index=True,
    )

    modulo: Mapped[str] = mapped_column(String(30), nullable=False)
    severidad: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    medidas_ens_afectadas: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    gap_volcado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gap_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )

    __table_args__ = (
        Index("ix_discovery_alerts_project_severidad", "project_id", "severidad"),
    )


class DiscoveredConfiguration(FullMixin, Base):
    """Check de configuracion de seguridad (TLS/DNS/cloud scores) (M22-B)."""

    __tablename__ = "discovered_configurations"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    discovery_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_runs_m22.id"), nullable=False, index=True
    )

    fuente_conector: Mapped[str] = mapped_column(String(50), nullable=False)
    sistema: Mapped[str] = mapped_column(String(300), nullable=False)

    control_id: Mapped[str] = mapped_column(String(100), nullable=False)
    control_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    valor_actual: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valor_esperado: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    gap_severidad: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)

    herramienta_deteccion: Mapped[str] = mapped_column(String(50), nullable=False)

    medidas_ens_afectadas: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    raw_output: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    descubierto_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=True
    )

    __table_args__ = (
        Index("ix_discovered_configurations_project_gap", "project_id", "gap_severidad"),
    )


class VulnerabilityFinding(FullMixin, Base):
    """Hallazgo de vulnerabilidad importado de scanners externos (M22-B)."""

    __tablename__ = "vulnerability_inventory"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    discovery_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_runs_m22.id"), nullable=False, index=True
    )

    fuente: Mapped[str] = mapped_column(String(50), nullable=False)

    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    cve_id: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)

    cvss_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cvss_vector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cvss_severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)

    asset_afectado: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    es_explotable: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    exploit_disponible: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    remediacion_sugerida: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    medidas_ens_afectadas: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    mitre_tactics: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="open")

    raw_finding: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    descubierto_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=True
    )

    __table_args__ = (
        Index(
            "ix_vulnerability_inventory_project_severity",
            "project_id", "cvss_severity",
        ),
    )


class DiscoveredDataStore(FullMixin, Base):
    """Almacen de datos descubierto y clasificado (M22-B)."""

    __tablename__ = "discovered_data_stores"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    discovery_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_runs_m22.id"), nullable=False, index=True
    )

    fuente_conector: Mapped[str] = mapped_column(String(50), nullable=False)

    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(300), nullable=False)
    ubicacion: Mapped[str] = mapped_column(String(500), nullable=False)

    volumen_estimado_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    clasificacion_inicial: Mapped[str] = mapped_column(
        String(30), nullable=False, default="sin_clasificar",
    )

    patrones_detectados: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    tiene_datos_personales: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    tiene_datos_salud: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    tiene_datos_financieros: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    cifrado_en_reposo: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    cifrado_en_transito: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    control_acceso: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tiene_backup: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    metadata_extra: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    pkg_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    descubierto_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=True
    )

    __table_args__ = (
        Index(
            "ix_discovered_data_stores_project_clasificacion",
            "project_id", "clasificacion_inicial",
        ),
    )


class LoggingAssessment(FullMixin, Base):
    """Evaluacion de logging/SIEM/monitorizacion del cliente (M22-C)."""

    __tablename__ = "logging_assessments"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    discovery_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_runs_m22.id"),
        nullable=False, index=True,
    )

    tiene_siem: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    siem_producto: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    fuentes_log: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    cobertura_servidores_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cobertura_red_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cobertura_aplicaciones_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cobertura_endpoints_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    retencion_minima_dias: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    retencion_maxima_dias: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cumple_retencion_ens: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    tiene_alertas_activas: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    alertas_revisadas_por: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    casos_uso_activos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    cumple_op_exp_8: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    gaps_op_exp_8: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    nivel_madurez_logging: Mapped[str] = mapped_column(String(10), nullable=False, default="L0")

    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class DataFlowDiagram(FullMixin, Base):
    """DFD generado desde assets+identities+data_stores (M22-C)."""

    __tablename__ = "data_flow_diagrams"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    discovery_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_runs_m22.id"),
        nullable=False, index=True,
    )

    nombre: Mapped[str] = mapped_column(String(300), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tipo: Mapped[str] = mapped_column(String(50), nullable=False)

    nodos: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    flujos: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    clasificacion_max_datos: Mapped[str] = mapped_column(
        String(30), nullable=False, default="sin_clasificar",
    )

    mermaid_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    observaciones_seguridad: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (
        Index("ix_data_flow_diagrams_project_tipo", "project_id", "tipo"),
    )


class ContinuityAssessment(FullMixin, Base):
    """Evaluacion de continuidad: backups/DRP/SLAs/SPOFs (M22-C)."""

    __tablename__ = "continuity_assessments"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    discovery_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_runs_m22.id"),
        nullable=False, index=True,
    )

    backups_inventario: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    tiene_backup_offsite: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    tiene_backup_cifrado: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ultima_prueba_restauracion: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    prueba_restauracion_exitosa: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    tiene_drp: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    drp_documentado: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    drp_probado: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    drp_ultima_prueba: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )

    slas_proveedores: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    spofs_detectados: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    rto_global_horas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rpo_global_horas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    nivel_madurez_continuidad: Mapped[str] = mapped_column(
        String(10), nullable=False, default="L0",
    )

    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
