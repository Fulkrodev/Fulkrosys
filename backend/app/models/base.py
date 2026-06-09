"""SQLAlchemy base classes and mixins for FULKRO."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    """Timezone-aware utcnow callable for SQLAlchemy onupdate."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all FULKRO models."""
    pass


class TimestampMixin:
    """Adds created_at and updated_at columns."""
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        onupdate=_utcnow,
        nullable=True,
    )


class SoftDeleteMixin:
    """Adds deleted_at for soft delete."""
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        default=None,
    )


class UUIDPrimaryKeyMixin:
    """Adds UUID primary key with server-side default."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


class FullMixin(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Standard mixin: UUID PK + timestamps + soft delete."""
    pass


# ══════════════════════════════════════════════════════════════════════
# Cliente in-portal review · SAN-E v3 atom 0.1 · ADR-020 v6
# 2 patterns reales detectados auditando atoms MB-5.3 a MB-5.6:
#   Pattern A · review decisional (status enum) · sin signing
#   Pattern B · review acompaña firma (signing_intent_id) · sin status
# ══════════════════════════════════════════════════════════════════════


# Enum values para CHECK constraint Pattern A · MUST coincide con BD
CLIENT_REVIEW_STATUS_VALUES = (
    "pendiente_revision",
    "revisada_ok",
    "con_pregunta",
    "suggest_change",
)


class ClientReviewMixinA:
    """Pattern A · review decisional cliente (status enum) · sin firma directa.

    4 cols + 2 helpers. Usado por DdaEntry · MageritAsset · MageritThreatAssessment.

    Mixin declara cols sin __table_args__. CHECK constraint + index partial
    están en BD (creados por migrations atoms 5.3.A / 5.4.A / 5.4b.A) y
    permanecen "shadow" al ORM. Atoms futuros MB-6 que usen este Mixin pueden
    invocar ``client_review_a_table_args(tablename)`` para declararlos en
    ``__table_args__`` del modelo hijo (alineado con BD existing).
    """

    client_review_status: Mapped[str | None] = mapped_column(String(30))
    client_review_note: Mapped[str | None] = mapped_column(Text)
    client_reviewed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    client_reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
    )

    @property
    def is_client_reviewed(self) -> bool:
        return self.client_reviewed_at is not None

    @property
    def is_client_review_ok(self) -> bool:
        return self.client_review_status == "revisada_ok"

    def to_client_review_dict(self) -> dict:
        return {
            "status": self.client_review_status,
            "note": self.client_review_note,
            "reviewed_at": (
                self.client_reviewed_at.isoformat()
                if self.client_reviewed_at else None
            ),
            "reviewed_by_user_id": (
                str(self.client_reviewed_by_user_id)
                if self.client_reviewed_by_user_id else None
            ),
        }


class ClientReviewMixinB:
    """Pattern B · review cliente acompaña firma directa · sin status enum.

    4 cols + 2 helpers. Usado por VerificationRun · BasicDeclarationRow.

    ``client_signing_intent_id`` linkea a ``signing_intents.id`` (FK lógica
    sin constraint para no acoplar motores). Cliente firma in-portal vía M05
    y deja note opcional sobre preocupaciones.

    Mixin declara cols sin __table_args__ (mismo razonamiento que MixinA).
    Atoms futuros invocan ``client_review_b_table_args(tablename)`` para
    declarar index alineado con BD.
    """

    client_concerns_note: Mapped[str | None] = mapped_column(Text)
    client_reviewed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    client_reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
    )
    client_signing_intent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
    )

    @property
    def is_client_reviewed(self) -> bool:
        return self.client_reviewed_at is not None

    @property
    def is_signed_via_intent(self) -> bool:
        return self.client_signing_intent_id is not None

    def to_client_review_dict(self) -> dict:
        return {
            "concerns_note": self.client_concerns_note,
            "reviewed_at": (
                self.client_reviewed_at.isoformat()
                if self.client_reviewed_at else None
            ),
            "reviewed_by_user_id": (
                str(self.client_reviewed_by_user_id)
                if self.client_reviewed_by_user_id else None
            ),
            "signing_intent_id": (
                str(self.client_signing_intent_id)
                if self.client_signing_intent_id else None
            ),
        }


def client_review_a_table_args(table_name: str) -> tuple:
    """Returns CHECK + partial index Pattern A · spread en __table_args__ hijo.

    Replica EXACTO los objetos BD creados por migrations 5.3.A / 5.4.A / 5.4b.A:
      - CheckConstraint ck_{table}_client_review_status (enum 4 valores)
      - Index idx_{table}_client_review_status (project_id, status) WHERE status IS NOT NULL

    Usage en modelo hijo MB-6 atom NEW:
        class MyNewModelA(ClientReviewMixinA, FullMixin, Base):
            __tablename__ = "my_new_table"
            project_id: Mapped[uuid.UUID] = mapped_column(...)
            __table_args__ = (
                *client_review_a_table_args("my_new_table"),
                # ... otros constraints
            )
    """
    values_sql = ", ".join(f"'{v}'" for v in CLIENT_REVIEW_STATUS_VALUES)
    return (
        CheckConstraint(
            f"client_review_status IS NULL OR client_review_status IN ({values_sql})",
            name=f"ck_{table_name}_client_review_status",
        ),
        Index(
            f"idx_{table_name}_client_review_status",
            "project_id",
            "client_review_status",
            postgresql_where=text("client_review_status IS NOT NULL"),
        ),
    )


def client_review_b_table_args(table_name: str) -> tuple:
    """Returns partial index Pattern B · spread en __table_args__ hijo.

    Replica EXACTO el index BD creado por migrations 5.5.A / 5.6.A:
      - Index idx_{table}_client_reviewed (project_id, client_reviewed_at) WHERE IS NOT NULL

    Atom MB-7.0.bis update · helper ahora declara 2-col (project_id +
    client_reviewed_at) matching BD reality. Previous 1-col version causaba
    "changed index" drift en alembic check.

    Pattern B no tiene CHECK constraint (sin status enum).

    Usage en modelo hijo MB-6 atom NEW:
        class MyNewModelB(ClientReviewMixinB, FullMixin, Base):
            __tablename__ = "my_new_table"
            __table_args__ = (
                *client_review_b_table_args("my_new_table"),
            )
    """
    return (
        Index(
            f"idx_{table_name}_client_reviewed",
            "project_id",
            "client_reviewed_at",
            postgresql_where=text("client_reviewed_at IS NOT NULL"),
        ),
    )
