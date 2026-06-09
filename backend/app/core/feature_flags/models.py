"""Feature flag overrides SQLAlchemy model (ADR-037).

Materializa ADR-036 deferred ``feature_flag_overrides``. Manual overrides
per-project o per-client que toman precedencia sobre YAML catalog
evaluation (categoria + archetype + employee_count).

Admin-only management · Q5.3 cement INVISIBLE cliente (cliente ve features
ENABLED como si fueran natural, sin labels "granted by admin").

Precedence resolve_feature_flag(project_id, feature_key):
  1. project-level override (project_id match, revoked_at IS NULL,
     expires_at > now() OR expires_at IS NULL)
  2. client-level override (client_id match · vía project.client_id)
  3. YAML catalog evaluation (categoria + archetype + employees)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class FeatureFlagOverride(FullMixin, Base):
    """Manual override de feature flag · admin-granted · audit via triggers BD."""

    __tablename__ = "feature_flag_overrides"
    __table_args__ = (
        CheckConstraint(
            "project_id IS NOT NULL OR client_id IS NOT NULL",
            name="ck_feature_flag_overrides_scope_required",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_by_user_id IS NOT NULL",
            name="ck_feature_flag_overrides_revoke_actor",
        ),
        Index(
            "ix_feature_flag_overrides_project_feature",
            "project_id", "feature_key",
        ),
        Index(
            "ix_feature_flag_overrides_client_feature",
            "client_id", "feature_key",
        ),
        Index(
            "ix_feature_flag_overrides_active",
            "feature_key",
            postgresql_where=text(
                "revoked_at IS NULL AND deleted_at IS NULL"
            ),
        ),
    )

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=True,
    )
    feature_key: Mapped[str] = mapped_column(String(120), nullable=False)
    override_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    granted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
