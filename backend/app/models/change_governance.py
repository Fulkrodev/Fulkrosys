"""M28 Change Governance — modelos DB-backed (sub-fase 5.5.F.0.H).

Reemplaza dict in-memory ``_TOPOLOGIES`` previo en m28/api.py con
tabla dedicada ``change_topologies``. Migración b2c3d4e5f6a7.

Cross-motor reuse (ADR-023):
- ``_RECATEGORIZATIONS`` m28 → m27 ``RecategorizationRow``
  (conformity_lifecycle.recategorizations).
- ``_EXTRAORDINARY_AUDITS`` m28 → m27 ``ExtraordinaryAuditRow``
  (conformity_lifecycle.extraordinary_audits).
- ``_CHANGES`` m28 → ``Change`` extendido (operations.changes
  + metadata_jsonb column added).

Single source truth dominio compartido m27/m28 — ver ADR-023
docs/spec/DECISIONS.md.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, UUIDPrimaryKeyMixin


class ChangeTopologyRow(UUIDPrimaryKeyMixin, Base):
    """Topología de roles ENS por proyecto (5 patterns).

    Reemplaza dict ``_TOPOLOGIES[project_id]`` previo en
    m28_change_governance/api.py. La lógica de selección de pattern
    (recommend_pattern, get_pattern, requires_memo) sigue en
    topology_service.py — esta tabla solo persiste el resultado.
    """

    __tablename__ = "change_topologies"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    pattern_id: Mapped[str] = mapped_column(String(40), nullable=False)
    detail_jsonb: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )
    requires_memo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
