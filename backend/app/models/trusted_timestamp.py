"""Sellos de tiempo RFC 3161 sobre artefactos · feat/fulkro-100 Ola D.

Tabla append-only y GENÉRICA (artifact_type/id/hash) para no tocar las tablas
inmutables que sella (signing_events tiene hash chain R6 · no admite UPDATE). Un
sello es un hecho registrado, no se modifica. Reusable cross-artefacto (firmas,
evidencias, informes).

RLS directa por project_id (current_project_id()) · fail-closed.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Index,
    LargeBinary,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, UUIDPrimaryKeyMixin


class TrustedTimestamp(UUIDPrimaryKeyMixin, Base):
    """Sello de tiempo RFC 3161 de un artefacto (append-only)."""

    __tablename__ = "trusted_timestamps"
    __table_args__ = (
        Index(
            "ix_trusted_timestamps_artifact",
            "artifact_type", "artifact_id",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    artifact_type: Mapped[str] = mapped_column(String(40), nullable=False)
    artifact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    tsa_url: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    token: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    gen_time: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"), nullable=False,
    )
