"""Motor 30 — Client Contacts: SQLAlchemy ORM models.

2 tablas:
  - ``client_contacts`` — agenda contactos por cliente (no portal users).
  - ``client_contact_interactions`` — timeline cross-motor.

Convenciones FULKRO:
  - ``FullMixin`` (UUID PK + created_at + updated_at + deleted_at).
  - FK ``client_id`` ON DELETE CASCADE (eliminar cliente borra contactos).
  - FK ``contact_id`` ON DELETE CASCADE en interactions.
  - FK ``client_user_id`` opcional (vínculo bidireccional con portal).
  - Indexes: ``(client_id, email)`` UNIQUE + GIN search en notas + DESC
    timeline + filtro ``(client_id, is_active)``.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, FullMixin


class ClientContact(FullMixin, Base):
    """Contacto profesional asociado a un cliente.

    Distinct de ``ClientUser`` (motor 21 portal cliente, login + password).
    Un ``ClientContact`` PUEDE estar vinculado a un ``ClientUser`` vía
    ``client_user_id`` cuando ``has_portal_access=True`` — un contacto
    es la representación "agenda + rol", el client_user es "credenciales
    + sesión portal".
    """

    __tablename__ = "client_contacts"
    __table_args__ = (
        UniqueConstraint(
            "client_id", "email", name="uq_client_contacts_client_email",
        ),
        Index(
            "ix_client_contacts_client_active",
            "client_id", "is_active",
        ),
        # SAN-E MB-3.C atom · indexes ENS roles + project scope.
        Index(
            "idx_client_contacts_role_ens_required",
            "client_id", "role_ens_required",
        ),
        Index(
            "ix_client_contacts_project",
            "project_id",
        ),
        Index(
            "uq_client_contacts_one_portal_per_project",
            "project_id",
            unique=True,
            postgresql_where=text("has_portal_access = true"),
        ),
        # GIN full-text sobre notes_marcos creado en migración con
        # ``USING gin (to_tsvector('spanish', notes_marcos))``. Aquí se
        # declara como Index sin op_class para que Alembic no intente
        # autogenerar una versión btree incompatible.
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )

    # SAN-E.MB-3.C · scope opcional proyecto. Constraint v3 (DB partial UNIQUE):
    # 1 contacto con has_portal_access=true por project_id. NULL = scope cliente.
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Identidad
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))

    # Rol
    role_title: Mapped[str] = mapped_column(String(150), nullable=False)
    role_category: Mapped[str] = mapped_column(String(50), nullable=False)
    # 14 categorías plan v4.2: sponsor, rseg, ciso, cto, cio, dpo, legal,
    # compras, rrhh, operaciones, tecnico, auditor_interno,
    # consultor_externo, usuario_final, otros.

    # Roles especiales (uno o varios pueden estar activos a la vez)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    is_signatory: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    has_portal_access: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    client_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_users.id", ondelete="SET NULL"),
    )

    # Sub-atom 1.C.F.3 · FK a departments(id) ON DELETE SET NULL.
    # Borrar área des-asigna empleados (NO los borra). Cross-project
    # validation en service-layer (department.project_id == contact.project_id).
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
    )

    # SAN-E v3.MB-5.0.bis · ADR-020 v5 stakeholders ENS_REQUIRED · INVISIBLE cliente
    role_ens_required: Mapped[str | None] = mapped_column(String(30))
    # 'sponsor' | 'responsable_informacion' | 'responsable_servicio' |
    # 'responsable_seguridad' | 'responsable_sistema' | 'administrador_seguridad' |
    # None. CHECK constraint en BD ck_client_contacts_role_ens_required.
    # NOTA: distinto de role_category (CRM/CCN-STIC 801 catalogo). Este campo es
    # exclusivo RD 311/2022 art. 11 + sponsor para auto-populate docs ENS via M6.
    contact_role_notes: Mapped[str | None] = mapped_column(Text)
    # Notas Marcos sobre el contacto/rol · admin-only.

    # Notas + preferencias
    notes_marcos: Mapped[str | None] = mapped_column(Text)
    preferred_communication: Mapped[str | None] = mapped_column(String(20))
    # email | phone | whatsapp | linkedin_dm | portal_inbox
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Europe/Madrid",
        server_default="Europe/Madrid",
    )

    # Estado actividad (semantic distinto a soft-delete heredado de
    # FullMixin → ``deleted_at`` queda NULL en deactivate; sólo se
    # rellena si el contacto se marca para purga real).
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true",
    )
    inactive_reason: Mapped[str | None] = mapped_column(String(200))
    inactive_since: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )

    # Auditoría aplicación (audit_log trigger persiste row-level)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="SET NULL"),
    )

    interactions: Mapped[list["ClientContactInteraction"]] = relationship(
        back_populates="contact",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ClientContactInteraction(FullMixin, Base):
    """Entrada de timeline para un contacto.

    Auto-poblada por servicios cross-motor (A18 reuniones, M29 mensajes,
    M12 magic links, M14 contratos) vía
    ``ClientContactService.log_interaction``.
    """

    __tablename__ = "client_contact_interactions"
    __table_args__ = (
        Index(
            "ix_client_contact_interactions_contact_created_desc",
            "contact_id", "created_at",
        ),
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    interaction_type: Mapped[str] = mapped_column(
        String(40), nullable=False,
    )
    # meeting | message | magic_link | contract_signature | email | other
    source_motor: Mapped[str | None] = mapped_column(String(20))
    # a18 | m29 | m12 | m14 | manual | otro
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    summary: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSONB)
    # Atributo Python ``details`` mapeado a columna JSONB ``details``.
    # SQLAlchemy reserva ``metadata``; usamos ``details`` para evitar el
    # choque y mantener semántica clara.

    contact: Mapped["ClientContact"] = relationship(
        back_populates="interactions",
    )
