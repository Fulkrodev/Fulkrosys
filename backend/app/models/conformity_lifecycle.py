"""M27 Conformity Lifecycle — 13 tablas que persisten la ruta formal ENS.

A diferencia del stub en-memoria previo en ``m27_conformity/api.py``,
estas tablas capturan de forma persistente:

- Declaracion vs Certificacion (conformity_routes)
- Declaracion Basica firmada (basic_declarations, E-041)
- Envios externos (conformity_submissions: Registro CCN, ENAC, AAPP)
- Cambios materiales + arbol 10-preguntas (material_changes)
- Recategorizaciones (recategorizations)
- Auditorias extraordinarias (extraordinary_audits)
- Topologia de roles ENS (role_topologies, 5 patrones)
- Excepciones CCN-STIC 801 (role_exception_memos, E-044)
- Campanas de renovacion bianual (renewal_campaigns)
- Overlays PCE cloud / µCeENS (pce_overlays)
- Estimaciones de esfuerzo (effort_estimates)
- Reuniones exploratorias F.1 (exploratory_meetings)
- Historico grafo stakeholders (stakeholders_graph_snapshots)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy import Index
from sqlalchemy.sql import text as sa_text

from backend.app.models.base import (
    Base,
    ClientReviewMixinB,
    UUIDPrimaryKeyMixin,
    client_review_b_table_args,
)


# ══════════════════════════════════════════════════════════════════════
# 1. conformity_routes
# ══════════════════════════════════════════════════════════════════════


class ConformityRouteRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "conformity_routes"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    route_type: Mapped[str] = mapped_column(String(40), nullable=False)
    route_subtype: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="planned")
    initiated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    expiration_date: Mapped[date | None] = mapped_column(Date)
    metadata_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


# ══════════════════════════════════════════════════════════════════════
# 2. conformity_submissions
# ══════════════════════════════════════════════════════════════════════


class ConformitySubmissionRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "conformity_submissions"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    submission_type: Mapped[str] = mapped_column(String(30), nullable=False)
    external_system: Mapped[str | None] = mapped_column(String(100))
    submitted_by: Mapped[str | None] = mapped_column(String(50))
    submitted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    external_ref_id: Mapped[str | None] = mapped_column(String(255))
    submission_payload_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    response_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    errors_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


# ══════════════════════════════════════════════════════════════════════
# 3. basic_declarations
# ══════════════════════════════════════════════════════════════════════


class BasicDeclarationRow(ClientReviewMixinB, UUIDPrimaryKeyMixin, Base):
    """Declaración Básica E-041 self-declaration o commitment pre-cert MEDIA/ALTA.

    Cliente review Pattern B via ClientReviewMixinB (atom 5.6.A).
    Index idx_basic_declarations_client_reviewed en BD (2 cols project_id + client_reviewed_at).

    Atom MB-7.0.bis · helper B updated a 2-col · usage clean via helper.
    """
    __tablename__ = "basic_declarations"
    __table_args__ = (
        *client_review_b_table_args("basic_declarations"),
        Index(
            "uq_basic_declarations_dpc_anniversary",
            "project_id", "anniversary_year",
            unique=True,
            postgresql_where=sa_text("declaration_type = 'dpc_anual'"),
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    declaration_type: Mapped[str] = mapped_column(
        String(40), nullable=False, default="initial",
    )
    # declaration_type values:
    #   "initial" → BASICA self-declaration E-041 (cliente firma · distintivo final)
    #   "commitment_pre_certification" → MEDIA/ALTA commitment pre-auditor ENAC
    #   "recategorization" → post-recat (existing flow)
    published_evidence_url: Mapped[str | None] = mapped_column(String(500))
    self_assessment_report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
    )
    responsible_person_name: Mapped[str | None] = mapped_column(String(255))
    responsible_person_email: Mapped[str | None] = mapped_column(String(255))
    signed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    signed_hash: Mapped[str | None] = mapped_column(String(64))
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conformity_submissions.id", ondelete="SET NULL"),
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )

    # Cliente review state heredado de ClientReviewMixinB (atom 5.6.A)
    # Readiness snapshot · audit trail compliance ENAC (atom 5.6.A · NO en mixin)
    readiness_snapshot_jsonb: Mapped[dict | None] = mapped_column(JSONB)

    # SAN-E v3.MB-6 atom 2 · DPC anual anniversary year
    # NULL para declaration_type != 'dpc_anual' (initial/commitment NO usan).
    # UNIQUE partial (project_id, anniversary_year) WHERE declaration_type='dpc_anual'
    # · evita multi-year stacking (Consideration A · audit MB-6 atom 2).
    anniversary_year: Mapped[int | None] = mapped_column(Integer)


# ══════════════════════════════════════════════════════════════════════
# 4. material_changes
# ══════════════════════════════════════════════════════════════════════


class MaterialChangeRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "material_changes"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    change_type: Mapped[str] = mapped_column(String(30), nullable=False)
    detected_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    detected_by: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    materiality_score: Mapped[float | None] = mapped_column(Numeric(3, 2))
    is_material: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    materiality_tree_answers_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    triggered_extraordinary_audit: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    extraordinary_audit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extraordinary_audits.id", ondelete="SET NULL"),
    )
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    closed_by: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


# ══════════════════════════════════════════════════════════════════════
# 5. recategorizations
# ══════════════════════════════════════════════════════════════════════


class RecategorizationRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recategorizations"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    old_category: Mapped[str] = mapped_column(String(10), nullable=False)
    new_category: Mapped[str] = mapped_column(String(10), nullable=False)
    trigger_material_change_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("material_changes.id", ondelete="SET NULL"),
    )
    analysis_report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
    )
    approved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(255))
    new_dda_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


# ══════════════════════════════════════════════════════════════════════
# 6. extraordinary_audits
# ══════════════════════════════════════════════════════════════════════


class ExtraordinaryAuditRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "extraordinary_audits"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    trigger_material_change_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("material_changes.id", ondelete="SET NULL"),
    )
    scope_description: Mapped[str | None] = mapped_column(Text)
    scheduled_for: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    performed_by: Mapped[str | None] = mapped_column(String(100))
    performed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    audit_report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
    )
    findings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="scheduled")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


# ══════════════════════════════════════════════════════════════════════
# 7. role_topologies
# ══════════════════════════════════════════════════════════════════════


class RoleTopologyRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "role_topologies"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    pattern: Mapped[str] = mapped_column(String(40), nullable=False)
    total_persons: Mapped[int] = mapped_column(Integer, nullable=False)
    ens_roles_assigned_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    exceptions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(255))
    revision_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


# ══════════════════════════════════════════════════════════════════════
# 8. role_exception_memos
# ══════════════════════════════════════════════════════════════════════


class RoleExceptionMemoRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "role_exception_memos"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    role_topology_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("role_topologies.id", ondelete="CASCADE"), nullable=False,
    )
    exception_description: Mapped[str] = mapped_column(Text, nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    compensating_controls: Mapped[str | None] = mapped_column(Text)
    approved_by: Mapped[str | None] = mapped_column(String(255))
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


# ══════════════════════════════════════════════════════════════════════
# 9. renewal_campaigns
# ══════════════════════════════════════════════════════════════════════


class RenewalCampaignRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "renewal_campaigns"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    campaign_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scheduled_for: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    auto_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dossier_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="planned")
    result_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


# ══════════════════════════════════════════════════════════════════════
# 10. pce_overlays
# ══════════════════════════════════════════════════════════════════════


class PceOverlayRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "pce_overlays"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    overlay_type: Mapped[str] = mapped_column(String(40), nullable=False)
    overlay_spec_version: Mapped[str | None] = mapped_column(String(20))
    applicability_assessment_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    extra_measures_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    compliance_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="in_progress",
    )
    assessment_report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


# ══════════════════════════════════════════════════════════════════════
# 11. effort_estimates
# ══════════════════════════════════════════════════════════════════════


class EffortEstimateRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "effort_estimates"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    phase: Mapped[str] = mapped_column(String(30), nullable=False)
    estimated_hours: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(10, 2))
    actual_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))
    variance_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    calibrated_from_similar_projects_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


# ══════════════════════════════════════════════════════════════════════
# 12. exploratory_meetings
# ══════════════════════════════════════════════════════════════════════


class ExploratoryMeetingRow(UUIDPrimaryKeyMixin, Base):
    """Reuniones exploratorias / kickoffs con clientes y leads (FASE 7).

    Path actual ``conformity_lifecycle.py`` mantenido por dominio
    compartido cross-motor (H5 audit pre-FASE 7 · ADR-024 supersedes
    ADR-004 original videocall propio: reuniones externas con
    plataformas, no videocall FULKRO).

    FASE 7 (migración ``e8b3c5d70a91_meeting_v2_metadata_contact_fk_fts``)
    amplía con:
      - metadata reunión (platform/url/etapa_k)
      - interlocutor M30 ContactQuickPicker FK (cross-motor reuse)
      - notas markdown rich + render HTML sanitizado server-side
      - SSE session id link con A18 stream (TODO-A18-LATENCY RESOLVED)
      - workflow status (scheduled/in_progress/completed/cancelled)
      - title + project_id opcional para vista histórica
    """

    __tablename__ = "exploratory_meetings"

    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "FK projects opcional. Meeting puede ser pre-proyecto "
            "(lead K.1-K.4) o post-proyecto (K.5-K.6 retainer)."
        ),
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, default="", server_default="",
    )
    lead_source: Mapped[str | None] = mapped_column(String(40))
    meeting_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    blocks_completed_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    outputs_agente_18_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    proposal_generated_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    conversion_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="proposal_pending",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )

    # FASE 7 ADR-024 — metadata reunión externa
    platform: Mapped[str | None] = mapped_column(String(20))
    # google_meet | zoom | teams | presencial | jitsi | other
    meeting_url: Mapped[str | None] = mapped_column(String(500))
    etapa_k: Mapped[str | None] = mapped_column(String(10))
    # K.1 .. K.6 | other
    interlocutor_contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_contacts.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "FK client_contacts.id (M30) si interlocutor es contacto "
            "registrado. Auto-log interaction='meeting_attended' al "
            "complete_meeting si presente."
        ),
    )

    # Notas + render
    notes_markdown: Mapped[str | None] = mapped_column(Text)
    notes_html_sanitized: Mapped[str | None] = mapped_column(Text)

    # SSE A18 stream link
    sse_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        comment="UUID generado al iniciar SSE stream A18 update.",
    )

    # Workflow status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="scheduled",
        server_default="scheduled",
    )
    # scheduled | in_progress | completed | cancelled
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


# ══════════════════════════════════════════════════════════════════════
# 13. stakeholders_graph_snapshots
# ══════════════════════════════════════════════════════════════════════


class StakeholdersGraphSnapshotRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "stakeholders_graph_snapshots"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    snapshot_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    graph_data_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False)
    changed_from_previous: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    change_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


# ══════════════════════════════════════════════════════════════════════
# 14. conformity_state_snapshots — polimórfica route_history + exports
# ══════════════════════════════════════════════════════════════════════


class ConformityStateSnapshotRow(UUIDPrimaryKeyMixin, Base):
    """Snapshots polimórficos de estado m27 (sub-fase 5.5.F.0.G).

    Reemplaza dos dicts in-memory previos en m27 ``api.py``:

    - ``snapshot_type='route_transition'`` →
        ``metadata_jsonb = {"from": str, "to": str, "reason": str}``
        (timeline transitions ``RouteState``).
    - ``snapshot_type='external_export'`` →
        ``metadata_jsonb = {"tool": str, "params": dict, "artifact": dict,
                            "proof_uploaded": bool, "proof_reference": str}``
        (exports a sistemas externos PILAR / LUCIA / INES / Registro).

    Pattern polimórfico justificado: ambos casos comparten shape
    (project_id + JSONB + timestamp), volumen bajo, semántica
    "evento auditable" similar.
    """

    __tablename__ = "conformity_state_snapshots"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    snapshot_type: Mapped[str] = mapped_column(String(40), nullable=False)
    metadata_jsonb: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
