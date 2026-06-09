"""Onboarding and discovery models."""
import uuid
from datetime import datetime

from typing import Optional

from sqlalchemy import ForeignKey, String, Text, Boolean, Integer, DateTime, Index, LargeBinary, UniqueConstraint, func, text as sa_text
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class OnboardingSession(FullMixin, Base):
    __tablename__ = "onboarding_sessions"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    # #7 · formaliza la traza lead↔onboarding (antes solo indirecta vía project_id
    # compartido). Nullable: las sesiones in-portal post-firma no nacen de un lead.
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("leads.id"), nullable=True, index=True,
    )
    sector: Mapped[str | None] = mapped_column(String(100))
    rol_receptor: Mapped[str | None] = mapped_column(String(100))
    interlocutor_nombre: Mapped[str | None] = mapped_column(String(255))
    interlocutor_email: Mapped[str | None] = mapped_column(String(255))
    plantilla_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    magic_link_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("magic_links.id"))
    preguntas: Mapped[dict | None] = mapped_column(JSONB)
    respuestas: Mapped[dict | None] = mapped_column(JSONB)
    conectores_autorizados: Mapped[dict | None] = mapped_column(JSONB)
    estado: Mapped[str | None] = mapped_column(String(50))
    iniciado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # --- Motor 16 M16-A additions ---
    template_id_str: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    total_questions: Mapped[int | None] = mapped_column(Integer, nullable=True, server_default="0")
    answered_questions: Mapped[int | None] = mapped_column(Integer, nullable=True, server_default="0")
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True, index=True)
    language: Mapped[str | None] = mapped_column(String(5), nullable=True, server_default="es")
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # --- Motor 16 M16-B client auth ---
    client_auth_secret_hash: Mapped[str | None] = mapped_column(String(120), nullable=True)
    client_auth_issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OnboardingResponse(Base):
    """Individual response from client to an onboarding question."""
    __tablename__ = "onboarding_responses"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("onboarding_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    question_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(50), nullable=False)
    answer_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    __table_args__ = (
        Index('ix_onboarding_responses_session_question', 'session_id', 'question_id', unique=True),
    )


class DiscoveredAsset(FullMixin, Base):
    __tablename__ = "discovered_assets"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    onboarding_session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("onboarding_sessions.id"))
    fuente_conector: Mapped[str | None] = mapped_column(String(100))
    tipo_magerit: Mapped[str | None] = mapped_column(String(50))
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    identificador: Mapped[str | None] = mapped_column(String(255))
    criticidad_propuesta: Mapped[str | None] = mapped_column(String(20))
    propietario_inferido: Mapped[str | None] = mapped_column(String(255))
    ubicacion: Mapped[str | None] = mapped_column(String(255))
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB)
    descubierto_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # --- Motor 22 M22-A additions ---
    discovery_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_runs_m22.id"), nullable=True, index=True,
    )
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    pkg_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class DiscoveredIdentity(FullMixin, Base):
    __tablename__ = "discovered_identities"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    fuente_conector: Mapped[str | None] = mapped_column(String(100))
    directorio: Mapped[str | None] = mapped_column(String(100))
    username: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    es_privilegiada: Mapped[bool | None] = mapped_column(Boolean)
    mfa_activo: Mapped[bool | None] = mapped_column(Boolean)
    ultima_actividad: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    dias_inactiva: Mapped[int | None] = mapped_column(Integer)
    grupos: Mapped[dict | None] = mapped_column(JSONB)
    permisos_efectivos: Mapped[dict | None] = mapped_column(JSONB)
    alertas: Mapped[dict | None] = mapped_column(JSONB)
    descubierto_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # --- Motor 22 M22-A additions ---
    discovery_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_runs_m22.id"), nullable=True, index=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    tipo_cuenta: Mapped[str | None] = mapped_column(String(30), nullable=True)
    es_activa: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    password_policy_compliant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    pkg_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class ConnectorConfig(Base):
    """OAuth/PAT connector configuration per project (M16-C)."""
    __tablename__ = "connector_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    encrypted_credentials: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    scopes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="configured")
    last_discovery_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    discovery_result_summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa_text("now()"), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=sa_text("now()"), nullable=True)

    __table_args__ = (
        Index("ix_connector_configs_project_provider", "project_id", "provider", unique=True),
    )


class OAuthStateToken(Base):
    """Anti-CSRF state token per OAuth flow (SAN-E v3.MB-4.2.bis · Q2-A).

    1-time use · 10min TTL · scope client_user_id + project_id.
    """
    __tablename__ = "oauth_state_tokens"
    __table_args__ = (
        Index(
            "ix_oauth_state_client_project",
            "client_user_id", "project_id",
        ),
        Index(
            "ix_oauth_state_expires",
            "expires_at",
        ),
        UniqueConstraint(
            "state_token",
            name="oauth_state_tokens_state_token_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state_token: Mapped[str] = mapped_column(String(128), nullable=False)
    client_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("client_users.id", ondelete="CASCADE"), nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False,
    )
    connector_type: Mapped[str] = mapped_column(String(32), nullable=False)
    redirect_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    code_verifier: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa_text("now()"), nullable=False,
    )
