"""ORM models · M05 in-portal signing · SAN-E v3.MB-5.2.

3 tablas:
- signing_intents · 1 row per intent firma cliente
- signing_events · INMUTABLE log + hash chain
- signing_otp_codes · ephemeral OTP storage step-up
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    text as sa_text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class SigningIntent(Base):
    __tablename__ = "signing_intents"
    __table_args__ = (
        # CHECK constraints definidos en migration 123920e86153.
        # Indexes BD declarados aquí · atom MB-7.0.bis alignment.
        Index(
            "idx_signing_intents_project_status",
            "project_id", "status",
        ),
        Index(
            "idx_signing_intents_signable",
            "signable_type", "signable_ref_id",
        ),
        Index(
            "idx_signing_intents_user",
            "created_by_user_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=sa_text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    signable_type: Mapped[str] = mapped_column(String(40), nullable=False)
    signable_ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    signable_ref_type: Mapped[str | None] = mapped_column(String(50))
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
    )
    document_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    document_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    intent_payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=sa_text("'{}'::jsonb"),
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=sa_text("'pending'"),
    )
    requires_step_up_otp: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=sa_text("false"),
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        server_default=sa_text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        server_default=sa_text("now()"),
    )


class SigningEvent(Base):
    __tablename__ = "signing_events"
    __table_args__ = (
        Index(
            "idx_signing_events_actor",
            "actor_user_id",
        ),
        Index(
            "idx_signing_events_intent",
            "signing_intent_id", "created_at",
        ),
        Index(
            "idx_signing_events_project",
            "project_id", "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=sa_text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    signing_intent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("signing_intents.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    event_payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=sa_text("'{}'::jsonb"),
    )
    signature_ed25519: Mapped[bytes | None] = mapped_column(LargeBinary)
    signature_public_key: Mapped[bytes | None] = mapped_column(LargeBinary)
    signature_message: Mapped[str | None] = mapped_column(Text)
    previous_signature_hash: Mapped[str | None] = mapped_column(String(64))
    event_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(Text)
    # Ejecutable 7.7 · canvas TIER 1 fields (NULL si OTP-only legacy path)
    signature_canvas_dataurl: Mapped[str | None] = mapped_column(Text)
    signed_name: Mapped[str | None] = mapped_column(String(120))
    signed_surname: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        server_default=sa_text("now()"),
    )


class SigningOtpCode(Base):
    __tablename__ = "signing_otp_codes"
    __table_args__ = (
        UniqueConstraint(
            "signing_intent_id", "user_id",
            name="uq_signing_otp_codes_intent_user",
        ),
        Index(
            "idx_signing_otp_codes_expires",
            "expires_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=sa_text("gen_random_uuid()"),
    )
    signing_intent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("signing_intents.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=sa_text("0"),
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=sa_text("5"),
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    consumed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        server_default=sa_text("now()"),
    )
