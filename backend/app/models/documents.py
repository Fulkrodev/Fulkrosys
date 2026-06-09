"""Documents, evidence, procedures models."""
import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text, Boolean, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import (
    Base,
    ClientReviewMixinA,
    FullMixin,
    client_review_a_table_args,
)


class Document(ClientReviewMixinA, FullMixin, Base):
    """Documento generado por motor 06 (policies E-100..E-126 + procedures + IT).

    Cliente review fields heredados de ClientReviewMixinA (atom 0.1 · pattern A).
    Cliente solo review documents niveles 1-2 CCN-STIC 805 (PSI + Normativas).
    Niveles 3-4 (Procedures + IT) mantienen client_review_status NULL.

    ``client_signing_intent_id`` linkea a signing_intents.id post-firma bulk
    (Q1.C híbrida MB-6 atom 1 · review individual + firma bulk única).
    """
    __tablename__ = "documents"
    __table_args__ = (
        *client_review_a_table_args("documents"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    tipo: Mapped[str | None] = mapped_column(String(50))
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    version_actual: Mapped[str | None] = mapped_column(String(20))
    plantilla_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    estado: Mapped[str | None] = mapped_column(String(50))
    aprobado_por: Mapped[str | None] = mapped_column(String(255))
    fecha_aprobacion: Mapped[date | None] = mapped_column()
    template_codigo: Mapped[str | None] = mapped_column(String(32))
    docx_path: Mapped[str | None] = mapped_column(String(512))
    pdf_path: Mapped[str | None] = mapped_column(String(512))
    rendered_hash: Mapped[str | None] = mapped_column(String(64))
    signature_ed25519: Mapped[str | None] = mapped_column(String(128))
    context_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    generated_by: Mapped[str | None] = mapped_column(String(255))
    generated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # SAN-E v3.MB-6 atom 1 · link bulk signing intent (Q1.C híbrida)
    # NO en ClientReviewMixinA (Pattern A puro no firma directa) · custom field
    # para soporte firma bulk única tras review individual policies E-100..E-126.
    client_signing_intent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
    )
    # --- Motor 24 IDMS additions ---
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_folders.id"), index=True,
    )
    full_text_content: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, default=0)
    storage_path: Mapped[str | None] = mapped_column(String(500))
    clasificacion: Mapped[str | None] = mapped_column(String(30), index=True)
    # "politica" | "procedimiento" | "registro" | "evidencia" | "informe" | "contrato" | "otro"

    # Flag de visibilidad: documento SOLO-INTERNO (NO visible para el cliente).
    # Default false (los documentos existentes siguen visibles · comportamiento
    # actual preservado). Marcos lo marca true para ocultar borradores/notas
    # internas del portal cliente (migración documents_interno_flag_001).
    interno: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False, default=False,
    )

    # --- Sesion 9 Paso 3.1: workflow + expiration ---
    # El campo legacy `estado` (String 50) ya existe arriba y se usa en otros
    # motores (M6 Document Factory). Para el workflow IDMS usamos los valores:
    # draft | review | approved | archived | deprecated. Enforzamos en service
    # (no CHECK constraint DB para no romper otros motores).
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_users.id"), index=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), index=True,
    )
    review_period_months: Mapped[int | None] = mapped_column(Integer)

    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document")


class DocumentVersion(FullMixin, Base):
    __tablename__ = "document_versions"
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    contenido_path: Mapped[str | None] = mapped_column(String(500))
    hash_sha256: Mapped[str | None] = mapped_column(String(64))
    generado_por: Mapped[str | None] = mapped_column(String(100))
    generado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    firmado_por: Mapped[str | None] = mapped_column(String(255))
    firmado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    firma_data: Mapped[str | None] = mapped_column(Text)
    document: Mapped["Document"] = relationship(back_populates="versions")


class Evidence(FullMixin, Base):
    __tablename__ = "evidence"
    __table_args__ = (
        # Atom 6 antivirus scan partial indexes (MB-7.0.bis aligned).
        Index(
            "idx_evidence_scan_infected",
            "project_id", "scan_status",
            postgresql_where=text("scan_status = 'infected'"),
        ),
        Index(
            "idx_evidence_scan_quarantined",
            "project_id", "scan_status",
            postgresql_where=text("scan_status = 'quarantined'"),
        ),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    measure_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ens_measures.id"))
    control_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("controls.id"))
    tipo: Mapped[str | None] = mapped_column(String(50))
    fuente: Mapped[str | None] = mapped_column(String(100))
    fichero_path: Mapped[str | None] = mapped_column(String(500))
    hash_sha256: Mapped[str | None] = mapped_column(String(64))
    fecha_evidencia: Mapped[date | None] = mapped_column()
    fecha_caducidad: Mapped[date | None] = mapped_column()
    vigente: Mapped[bool] = mapped_column(Boolean, default=True)
    firma_ed25519: Mapped[str | None] = mapped_column(Text)
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB)
    # --- Motor 7 extensions ---
    evidence_type_id: Mapped[str | None] = mapped_column(String(80), index=True)
    nombre_tipo: Mapped[str | None] = mapped_column(String(120))
    fichero_nombre_original: Mapped[str | None] = mapped_column(String(255))
    fichero_mime_type: Mapped[str | None] = mapped_column(String(100))
    fichero_tamano_bytes: Mapped[int | None] = mapped_column(Integer)
    firma_payload_sha256: Mapped[str | None] = mapped_column(String(64))
    measure_code: Mapped[str | None] = mapped_column(String(40), index=True)
    obligation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    # --- MB-6 atom 6 · ClamAV antivirus scan (ENS mp.s.5) ---
    scan_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="scanning",
    )
    # clean | scanning | infected | error | quarantined
    scan_started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    scan_completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    scan_engine_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    scan_result_jsonb: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    @property
    def is_clean(self) -> bool:
        return self.scan_status == "clean"

    @property
    def is_quarantined(self) -> bool:
        return self.scan_status == "quarantined"

    @property
    def is_scan_pending(self) -> bool:
        return self.scan_status == "scanning"

    @property
    def is_infected(self) -> bool:
        return self.scan_status in ("infected", "quarantined")


class EvidenceRenewalRequest(FullMixin, Base):
    __tablename__ = 'evidence_renewal_requests'
    evidence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('evidence.id', ondelete='CASCADE'), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    measure_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    motivo: Mapped[str] = mapped_column(String(80), nullable=False)
    estado: Mapped[str] = mapped_column(String(40), nullable=False, default='pending', index=True)
    fecha_caducidad_original: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    dias_para_caducar: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_extra_renewal: Mapped[dict | None] = mapped_column('metadata_renewal', JSONB, nullable=True)


class Procedure(FullMixin, Base):
    __tablename__ = "procedures"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    plantilla_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    estado: Mapped[str | None] = mapped_column(String(50))
    responsable: Mapped[str | None] = mapped_column(String(255))
    periodicidad: Mapped[str | None] = mapped_column(String(50))


class ProcedureExecution(FullMixin, Base):
    __tablename__ = "procedure_executions"
    procedure_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("procedures.id"), nullable=False)
    fecha_ejecucion: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    ejecutado_por: Mapped[str | None] = mapped_column(String(255))
    resultado: Mapped[str | None] = mapped_column(Text)
    evidencia_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evidence.id"))
    observaciones: Mapped[str | None] = mapped_column(Text)
