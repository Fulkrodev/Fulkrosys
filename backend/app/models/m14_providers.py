"""M14 Providers + C-002 cross-compliance · ADR-046 v3 SAN-E.MB-3.B.

Gestion de proveedores criticos del proyecto y trazabilidad de la
clausula C-002 (encargado del tratamiento + ENS Art 18 + GDPR Art 28
+ NIS2 cuando aplica).

Auto-detect cross-compliance en creacion proveedor:
- type=cloud o saas + criticality=CRITICO/ALTO → ENS Art 18 + GDPR Art 28
- type=cloud + criticality=CRITICO → +NIS2 article 21 review

Sub-lote 1.B.7.1.0 (AMEND-014 OPCION C hibrida) anade:
- ProviderAssessment · resultado cuestionario onboarding (E-601 -> E-602)
- ProviderAddendum   · ADENDA E-604 firmada + tracking MinIO + normativas
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, REAL, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column


from backend.app.models.base import Base, FullMixin


PROVIDER_TYPES = ("cloud", "saas", "on-prem", "staffing", "hardware", "consultoria")
CRITICALITIES = ("CRITICO", "ALTO", "MEDIO", "BAJO")
C002_STATUSES = ("pendiente", "firmado", "no_aplica", "revocado")
ASSESSMENT_DECISIONS = ("APROBADO", "PENDIENTE", "RECHAZADO", "CONDICIONAL")


class Provider(FullMixin, Base):
    __tablename__ = "providers"
    __table_args__ = (
        Index("ix_providers_project_criticality", "project_id", "criticality"),
        CheckConstraint(
            "type IN ('cloud','saas','on-prem','staffing','hardware','consultoria')",
            name="ck_providers_type",
        ),
        CheckConstraint(
            "criticality IN ('CRITICO','ALTO','MEDIO','BAJO')",
            name="ck_providers_criticality",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    criticality: Mapped[str] = mapped_column(String(16), nullable=False)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    last_reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ProviderC002(FullMixin, Base):
    __tablename__ = "provider_c002"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pendiente','firmado','no_aplica','revocado')",
            name="ck_provider_c002_status",
        ),
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pendiente",
    )
    generated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="SET NULL"),
        nullable=True,
    )
    gaps_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    last_gap_check_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )


class ProviderAssessment(FullMixin, Base):
    __tablename__ = "provider_assessments"
    __table_args__ = (
        Index("ix_provider_assessments_provider", "provider_id"),
        Index("ix_provider_assessments_project", "project_id"),
        CheckConstraint(
            "risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 1)",
            name="ck_provider_assessments_risk_score",
        ),
        CheckConstraint(
            "risk_level IS NULL OR risk_level IN ('CRITICO','ALTO','MEDIO','BAJO')",
            name="ck_provider_assessments_risk_level",
        ),
        CheckConstraint(
            "decision IS NULL OR decision IN "
            "('APROBADO','PENDIENTE','RECHAZADO','CONDICIONAL')",
            name="ck_provider_assessments_decision",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    assessment_date: Mapped[date] = mapped_column(Date, nullable=False)
    assessor: Mapped[str | None] = mapped_column(Text, nullable=True)
    questionnaire_version: Mapped[str] = mapped_column(
        Text, nullable=False, default="v1.0",
    )
    responses: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # #5 fundación · alinear con la BD (REAL/float4 · la migración lo creó REAL).
    risk_score: Mapped[float | None] = mapped_column(REAL, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decision_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)


class ProviderAddendum(FullMixin, Base):
    __tablename__ = "provider_addendums"
    __table_args__ = (
        Index("ix_provider_addendums_provider", "provider_id"),
        Index("ix_provider_addendums_project", "project_id"),
        UniqueConstraint(
            "project_id", "addendum_code",
            name="uq_provider_addendums_project_code",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    addendum_code: Mapped[str] = mapped_column(Text, nullable=False)
    contract_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    normativas_cubiertas: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]",
    )
    fecha_firma: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_vigor: Mapped[date | None] = mapped_column(Date, nullable=True)
    vencimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    firmado_cliente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    firmado_proveedor: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    minio_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_from_template_code: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True,
    )
