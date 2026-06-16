"""Governance: committee, nominations, training, vendors."""
import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, String, Text, Boolean, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import (
    Base,
    ClientReviewMixinA,
    FullMixin,
    client_review_a_table_args,
)


ACTA_SUBTYPE_LABELS: dict[str, str] = {
    "kickoff": "Acta Inicio Proyecto",
    "checkpoint": "Acta Revisión Periódica",
    "audit": "Acta Auditoría ENAC",
    "cierre": "Acta Cierre Proyecto",
    "other": "Otra Acta",
}


class CommitteeMeeting(ClientReviewMixinA, FullMixin, Base):
    """Acta de Comite de Seguridad — entregable E-005.

    Modelo extendido en Sesion 6 con flujo completo de acta firmada
    por todos los asistentes via magic link APROBACION_ACTA. Cuando
    todos firman, el documento se sella con Ed25519 y se conserva
    PDF inmutable.

    SAN-E v3.MB-6 atom 5 · Actas 4 tipos signable cliente:
    - ClientReviewMixinA (9a aplicacion · pattern atomic 11a)
    - acta_subtype (5 valores · sub-Q1 future-ready)
    - admin_curation_status (3 valores · Q3-extra workflow)
    - client_signing_intent_id (sub-Q2 multi-sig · admin Ed25519 + cliente intent)

    JSONB usados:
    - asistentes:     [{"nombre","cargo","organizacion","email"}, ...]
    - orden_del_dia:  [{"punto","titulo","ponente","tiempo_min"}, ...]
    - acuerdos_jsonb: [{"numero","descripcion","owner","fecha_limite"}, ...]
    - proximos_pasos: [{"descripcion","owner","fecha_limite"}, ...]
    - firmas:         [{"asistente_idx","magic_link_id","firmado_at",
                        "ip","action_proof"}, ...]
    """
    __tablename__ = "committee_meetings"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "codigo",
            name="uq_committee_meetings_project_codigo",
        ),
        Index(
            "ix_committee_meetings_project_estado",
            "project_id", "estado",
        ),
        Index(
            "idx_committee_meetings_acta_subtype",
            "project_id", "acta_subtype",
        ),
        Index(
            "idx_committee_meetings_admin_pending",
            "project_id", "admin_curation_status",
            postgresql_where=text("admin_curation_status = 'draft'"),
        ),
        *client_review_a_table_args("committee_meetings"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)

    # Campos legacy (mantenidos para retrocompat).
    fecha: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    asistentes: Mapped[list | None] = mapped_column(JSONB)
    orden_dia: Mapped[str | None] = mapped_column(Text)
    acuerdos: Mapped[str | None] = mapped_column(Text)
    acta_path: Mapped[str | None] = mapped_column(String(500))
    firmado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # --- Sesion 6 extensions ---
    codigo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # E-005-001, E-005-002, ... (secuencia por proyecto)
    tipo_comite: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # kickoff | seguimiento_trimestral | cierre | extraordinario
    titulo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    lugar: Mapped[str | None] = mapped_column(String(300), nullable=True)
    presidente: Mapped[str | None] = mapped_column(String(200), nullable=True)
    secretario: Mapped[str | None] = mapped_column(String(200), nullable=True)
    orden_del_dia: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    acuerdos_jsonb: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    proximos_pasos: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    notas_libres: Mapped[str | None] = mapped_column(Text, nullable=True)

    docx_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hash_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    signature_ed25519: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # §5.5 audit C6 · URI canónica minio://{bucket}/{key} de la copia del acta
    # archivada al bucket WORM inmutable (fulkro-evidence-worm). NULL si MinIO no
    # está configurado (dev) — la copia local sigue siendo la fuente de lectura.
    docx_worm_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_worm_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)

    firmas: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    estado: Mapped[str | None] = mapped_column(
        String(30), nullable=True, server_default="draft",
    )
    # draft → generated → sent_for_signature → partially_signed
    #       → fully_signed → archived

    generado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    enviada_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    fully_signed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # --- MB-6 atom 5 extensions ---
    client_signing_intent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    acta_subtype: Mapped[str | None] = mapped_column(String(20), nullable=True)
    admin_curation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft",
    )
    admin_curated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    admin_curated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )

    @property
    def is_ready_for_client(self) -> bool:
        return self.admin_curation_status == "sent_to_client"

    @property
    def acta_subtype_label(self) -> str:
        if not self.acta_subtype:
            return ""
        return ACTA_SUBTYPE_LABELS.get(self.acta_subtype, self.acta_subtype)


class Nomination(FullMixin, Base):
    __tablename__ = "nominations"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    rol: Mapped[str] = mapped_column(String(100), nullable=False)
    persona: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_nombramiento: Mapped[date | None] = mapped_column()
    acta_path: Mapped[str | None] = mapped_column(String(500))


class TrainingRecord(FullMixin, Base):
    __tablename__ = "training_records"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    persona: Mapped[str] = mapped_column(String(255), nullable=False)
    modulo: Mapped[str | None] = mapped_column(String(255))
    fecha: Mapped[date | None] = mapped_column()
    resultado: Mapped[str | None] = mapped_column(String(50))
    evidencia_path: Mapped[str | None] = mapped_column(String(500))


class Vendor(FullMixin, Base):
    __tablename__ = "vendors"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    cif: Mapped[str | None] = mapped_column(String(20))
    criticidad: Mapped[str | None] = mapped_column(String(20))
    servicios: Mapped[str | None] = mapped_column(Text)
    certificaciones: Mapped[str | None] = mapped_column(Text)


class VendorContract(FullMixin, Base):
    __tablename__ = "vendor_contracts"
    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vendors.id"), nullable=False)
    nombre: Mapped[str | None] = mapped_column(String(255))
    fecha_inicio: Mapped[date | None] = mapped_column()
    fecha_fin: Mapped[date | None] = mapped_column()
    clausulas_ens_ok: Mapped[bool | None] = mapped_column(Boolean)
    contrato_path: Mapped[str | None] = mapped_column(String(500))
    adendas: Mapped[dict | None] = mapped_column(JSONB)
