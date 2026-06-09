"""MagicLinkMigrationLog model · audit trail SAN-D MB-19.9 (ADR-042).

Append-only log per migration action ejecutada por
backend/app/scripts/migrate_magic_links_to_tasks.py.

Migration actions (CHECK constraint enforced):
- converted_to_task: ML CONTINUO migrado a ClientTask portal record.
- revoked_obsolete: ML soft-deprecated revocado sin task target
  (lead phase · no client_user yet).
- kept_one_shot: skip · purpose mantiene razón (categoría A-F ADR-042).
- pending_review: skip pero marca para revision manual.

Refs:
- backend/migrations/versions/sand_magic_link_migration.py
- ADR-042 (magic-link policy híbrida final)
- backend/app/scripts/migrate_magic_links_to_tasks.py (consumer)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class MagicLinkMigrationLog(Base):
    """Audit trail row · migration_script run output."""

    __tablename__ = "magic_link_migration_log"
    __table_args__ = (
        UniqueConstraint(
            "magic_link_id",
            name="uq_magic_link_migration_log_magic_link",
        ),
        Index(
            "ix_magic_link_migration_processed_at",
            text("processed_at DESC"),
        ),
        Index(
            "ix_magic_link_migration_purpose_action",
            "original_purpose", "migration_action",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
    )
    magic_link_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("magic_links.id"),
        nullable=False,
    )
    original_purpose: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )
    migration_action: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )
    target_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
