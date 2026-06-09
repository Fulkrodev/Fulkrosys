"""M28 Project Role Assignments · ADR-046 v3 SAN-E.MB-3.E.

Asignacion granular role_code → contact (M30) per project. Distinct de
RoleTopologyRow (model agregado pattern startup/pyme/empresa) ·
project_role_assignments persiste persona-rol concreta.

Roles soportados: ENS canonicos CCN-STIC 801 + cross-compliance (DPO, CISO).
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
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


# ENS_REQUIRED roles (CCN-STIC 801)
ENS_REQUIRED_ROLES = (
    "sponsor",
    "responsable_informacion",
    "responsable_servicio",
    "responsable_seguridad",
    "responsable_sistema",
)

# Cross-compliance roles (no ENS pero requeridos otras frameworks)
CROSS_COMPLIANCE_ROLES = (
    "dpo",
    "ciso",
    "responsable_proteccion_datos",
    "auditor",
    "punto_contacto_ccn",
    "miembro_comite_seguridad",
)

ALL_ROLE_CODES = ENS_REQUIRED_ROLES + CROSS_COMPLIANCE_ROLES


class ProjectRoleAssignment(FullMixin, Base):
    __tablename__ = "project_role_assignments"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "role_code",
            name="uq_role_assignment_project_role",
        ),
        Index(
            "ix_role_assignment_project",
            "project_id",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_code: Mapped[str] = mapped_column(String(64), nullable=False)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    is_cross_compliance: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    assigned_by: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
