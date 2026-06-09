"""LiveRecord ORM model · sub-lote 1.C.B (registros vivos E-300..E-325).

Tabla generica con discriminator ``register_type`` para 26 registros vivos
operativos exigidos durante conformidad ENS (sub-fase 1.5 plan v2). Bloques:
Activos, Personas, Incidentes, Cambios, Proveedores, Backup, Continuidad,
Auditoria, Comite.

Schema validation (shape entry_data por register_type) ocurre en capa Pydantic
(backend/app/motors/m_live_records/schemas.py). La tabla mantiene JSONB libre
con CHECK constraint solo sobre register_type + status.

RLS project-scoped (LECCION-OPS-008). Owner fulkro_migrate · GRANT fulkro_app.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


# created_by / updated_by son UUID sin FK constraint: la plataforma tiene 2
# pools de usuarios (auth_users + client_users via ADR-013) y este pattern
# evita acoplar la tabla a uno concreto (mismo enfoque que
# incidents.client_reviewed_by_user_id).


VALID_REGISTER_TYPES: tuple[str, ...] = tuple(
    f"E-{n}" for n in range(300, 326)
)


VALID_STATUSES: tuple[str, ...] = ("active", "archived")


class LiveRecord(Base):
    """Registro vivo operativo ENS (E-300..E-325)."""

    __tablename__ = "live_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    register_type: Mapped[str] = mapped_column(String(10), nullable=False)
    entry_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'active'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    updated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "register_type ~ '^E-3(0[0-9]|1[0-9]|2[0-5])$'",
            name="ck_live_records_register_type",
        ),
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in VALID_STATUSES)})",
            name="ck_live_records_status",
        ),
        Index(
            "ix_live_records_project_type",
            "project_id",
            "register_type",
        ),
        Index(
            "ix_live_records_status_active",
            "project_id",
            "register_type",
            postgresql_where=text("status = 'active'"),
        ),
        Index(
            "ix_live_records_entry_data_gin",
            "entry_data",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<LiveRecord id={self.id} project_id={self.project_id} "
            f"register_type={self.register_type} status={self.status}>"
        )
