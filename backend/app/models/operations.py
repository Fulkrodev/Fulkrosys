"""Operations: incidents, vulnerabilities, changes, magic links."""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, Boolean, Integer, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy import Index

from backend.app.models.base import (
    Base,
    ClientReviewMixinA,
    FullMixin,
    client_review_a_table_args,
)


class Incident(ClientReviewMixinA, FullMixin, Base):
    """Incidente seguridad · CCN-STIC 817 workflow + cliente review MixinA.

    Workflow estados (6 · CCN-STIC 817 estándar):
      created → triaged → investigated → mitigated → resolved → closed

    Cliente VE solo `resolved` + `closed` (Q4 cement MB-6 atom 3).
    Marcos gestiona estados internos (admin-only transitions).

    CCN-CERT routing tier-aware:
      - projects.lucia_enabled=False (default · ICP empresas privadas) → manual
        E-CCN-NOTIFY pdf · cliente firma + envía email incidencias@ccn-cert.cni.es
      - projects.lucia_enabled=True → auto LUCIA federation (lucia_submission_id linked)

    Note: FK lucia_submission_id existe en BD via migration (726e561c0cc6) pero
    NO declarada aquí porque lucia_submissions table es raw-SQL (sin ORM model)
    excluida via env.py _AUTOGEN_EXCLUDE_TABLES. Atom MB-7.0.bis crear ORM
    model lucia_submissions si Marcos quiere full reconciliation.
    """
    __tablename__ = "incidents"
    __table_args__ = (
        *client_review_a_table_args("incidents"),
        Index(
            "idx_incidents_workflow_state_active",
            "project_id", "workflow_state",
        ),
        # Ejecutable 8 Pasada 16 (DB-DRIFT-01): la FK incidents.lucia_submission_id ->
        # lucia_submissions.id sigue ENFORCED a nivel BD (migración 726e561c0cc6 ·
        # fk_incidents_lucia_submission_id ON DELETE SET NULL). NO se declara aquí como
        # ForeignKeyConstraint ORM porque lucia_submissions es tabla raw-SQL sin ORM model
        # (excluida en env.py _AUTOGEN_EXCLUDE_TABLES). Declararla rompía el sort de
        # Base.metadata en `alembic check` (NoReferencedTableError). Coherente con docstring.
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    fecha: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    severidad: Mapped[str | None] = mapped_column(String(20))
    descripcion: Mapped[str | None] = mapped_column(Text)
    notificado_lucia: Mapped[bool | None] = mapped_column(Boolean, default=False)
    lucia_id: Mapped[str | None] = mapped_column(String(100))
    resolucion: Mapped[str | None] = mapped_column(Text)

    # SAN-E v3.MB-6 atom 3 · workflow + routing CCN-CERT
    workflow_state: Mapped[str | None] = mapped_column(String(30))
    client_signing_intent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
    )
    # FK lucia_submissions enforced at DB level (migration 726e561c0cc6) ·
    # NO ORM ForeignKey declaration porque LuciaSubmission no tiene model class.
    lucia_submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
    )
    ccn_cert_routing_decision: Mapped[dict | None] = mapped_column(JSONB)
    reported_to_ccn_cert_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    manual_notification_doc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
    )


class Vulnerability(FullMixin, Base):
    __tablename__ = "vulnerabilities"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    fuente: Mapped[str | None] = mapped_column(String(100))
    cve: Mapped[str | None] = mapped_column(String(30))
    severidad: Mapped[str | None] = mapped_column(String(20))
    sistema_afectado: Mapped[str | None] = mapped_column(String(255))
    estado: Mapped[str | None] = mapped_column(String(50))
    fecha_deteccion: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    fecha_resolucion: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class Change(FullMixin, Base):
    __tablename__ = "changes"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    solicitante: Mapped[str | None] = mapped_column(String(255))
    aprobado_cab: Mapped[bool | None] = mapped_column(Boolean)
    fecha_implementacion: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    resultado: Mapped[str | None] = mapped_column(Text)
    # Sub-fase 5.5.F.0.H ADR-023: payload extendido m28 governance state
    # machine (state ∈ intake/assessed/closed, assessment dict,
    # proposed_date, requested_by). Reemplaza dict in-memory
    # ``_CHANGES`` previo (api.py m28). Migración b2c3d4e5f6a7.
    metadata_jsonb: Mapped[dict] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"), nullable=False,
    )


class MagicLink(FullMixin, Base):
    __tablename__ = "magic_links"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    tipo_operacion: Mapped[str] = mapped_column(String(50), nullable=False)
    scope: Mapped[dict | None] = mapped_column(JSONB)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    otp_hash: Mapped[str | None] = mapped_column(String(64))
    otp_expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
        doc="Expiración propia del OTP (corta · indep del TTL del link · §1.5). NULL=sin expiración propia (links legacy).",
    )
    expira_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    max_usos: Mapped[int | None] = mapped_column(Integer, default=1)
    usos: Mapped[int] = mapped_column(Integer, default=0)
    revocado: Mapped[bool] = mapped_column(Boolean, default=False)
    # --- Motor 12 Magic Link Engine (Bloque 13) ---
    revoked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
        doc="Timestamp de revocacion soft. Complementa boolean revocado sin romper FKs.",
    )
    otp_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        doc="Contador intentos fallidos OTP. >= 3 invalida link (rate limit seguridad).",
    )
    recipient_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        doc="Email del destinatario al que se envio el link.",
    )
    allowed_countries: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        doc="Codigos ISO paises permitidos (['ES','PT']). NULL = sin restriccion geo.",
    )
    # M30 integration (TODO-M30-M12-INTEGRATION-001 RESOLVED 2026-04-29)
    sent_to_contact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("client_contacts.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "FK client_contacts.id si magic link enviado a contacto "
            "profesional registrado M30. NULL = legacy o flow sin contact "
            "lookup. ON DELETE SET NULL preserva audit trail del link "
            "aunque se borre el contacto."
        ),
    )
    # --- FASE 4.5 sub-bloque A · ADR-011 email customization (migration f658961972a2) ---
    cc_emails: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True,
        comment="Carbon copy emails adicionales (TEXT[]). Aplicado por EmailSender al enviar el link. NULL = sin CC.",
    )
    custom_subject: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Override del subject default per purpose. NULL = usar subject definido en _PURPOSE_EMAILS dict.",
    )
    custom_body_intro: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Texto Marcos antes del cuerpo template (override prepend, no replace). NULL = sin intro custom.",
    )


class ClientInteraction(FullMixin, Base):
    __tablename__ = "client_interactions"
    magic_link_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("magic_links.id"), nullable=False)
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    geolocalizacion: Mapped[str | None] = mapped_column(String(100))
    timestamp: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    payload: Mapped[dict | None] = mapped_column(JSONB)
    firma_resultado: Mapped[str | None] = mapped_column(Text)
