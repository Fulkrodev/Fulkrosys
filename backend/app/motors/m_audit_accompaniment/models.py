"""m_audit_accompaniment ORM models · Sesión 3B-4 Ejecutable 7.5 (2026-05-27).

3 tables canonical:
- audit_accompaniment_state · per-project current state + branch + metadata
- audit_accompaniment_artifacts · uploaded files per state
- audit_accompaniment_transitions · historic transitions audit trail

R6 hash chain inviolable preserved (audit_log immutable inserts via service layer).
Sub-atom 5.A audit_log 3-way OR · project_id + client_id propagated.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class AuditAccompanimentState(FullMixin, Base):
    """Per-project current state in audit accompaniment cycle.

    project_id is PK-equivalent via UNIQUE constraint (single state row per project).
    Branch immutable post-creation (BASICO vs MEDIO_ALTO derived project.categoria_objetivo).
    """

    __tablename__ = "audit_accompaniment_state"
    __table_args__ = (
        Index(
            "ix_audit_accompaniment_state_project_unique",
            "project_id",
            unique=True,
        ),
        Index(
            "ix_audit_accompaniment_state_branch",
            "category_branch",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_state: Mapped[str] = mapped_column(String(64), nullable=False)
    category_branch: Mapped[str] = mapped_column(String(16), nullable=False)
    last_advanced_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    accompaniment_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )


class AuditAccompanimentArtifact(FullMixin, Base):
    """Artifacts uploaded per state · file storage path + sha256 + uploader trail.

    artifact_type free-form string (e.g. 'declaration_pdf' · 'enac_certificate' ·
    'internal_audit_report'). Frontend uses suggested types per state UI hints
    but backend accepts any non-empty type.
    """

    __tablename__ = "audit_accompaniment_artifacts"
    __table_args__ = (
        Index(
            "ix_audit_accompaniment_artifacts_project_state",
            "project_id", "state",
        ),
        Index(
            "ix_audit_accompaniment_artifacts_uploaded_at",
            "uploaded_at",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0,
    )
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="now()",
    )
    artifact_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )


class AuditAccompanimentTransition(FullMixin, Base):
    """Historic state transitions · audit trail chronological cumulative.

    Append-only by service layer convention. Used by `get_timeline` to render
    chronological transitions in admin + cliente views.
    """

    __tablename__ = "audit_accompaniment_transitions"
    __table_args__ = (
        Index(
            "ix_audit_accompaniment_transitions_project_time",
            "project_id", "advanced_at",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_state: Mapped[str] = mapped_column(String(64), nullable=False)
    advanced_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    advanced_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="now()",
    )
    transition_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )
