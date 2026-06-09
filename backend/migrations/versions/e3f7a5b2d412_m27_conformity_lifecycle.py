"""M27 Conformity Lifecycle — 13 tablas + overlays + topologias de rol.

Persiste la ruta formal ENS que hasta ahora solo existia en memoria en
M27. Cubre:
  conformity_routes        (ruta Declaracion vs Certificacion ENAC)
  basic_declarations       (E-041 firmada por RSEG, publicada)
  conformity_submissions   (envios a sistemas externos: Registro, ENAC, AAPP)
  material_changes         (arbol 10-preguntas + materiality_score)
  recategorizations        (basica -> media, etc.)
  extraordinary_audits     (auditorias fuera de renewal por materiality)
  role_topologies          (5 patrones: startup/pyme_*/admin)
  role_exception_memos     (excepciones conflictivas CCN-STIC 801)
  renewal_campaigns        (auto-trigger 21 meses post-certif)
  pce_overlays             (cloud_azure/aws/gcp, uceens_*)
  effort_estimates         (calibracion ex-ante vs ex-post)
  exploratory_meetings     (bloques A-F plantilla F.1, F-001 -> P-001)
  stakeholders_graph_snapshots  (historico grafo AGE)

RLS: todas project_id-scoped (clients_isolation en exploratory_meetings).

Revision ID: e3f7a5b2d412
Revises: d2e6f4a9b812
Create Date: 2026-04-22 16:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "e3f7a5b2d412"
down_revision = "d2e6f4a9b812"
branch_labels = None
depends_on = None


ROUTE_TYPES = (
    "declaracion_basica",
    "certificacion_enac",
    "overlay_pce_cloud",
    "overlay_uceens",
)
DECLARATION_TYPES = ("initial", "renewal")
SUBMISSION_TYPES = ("basic_declaration", "enac_dossier", "renewal", "overlay_assessment")
MATERIAL_CHANGE_TYPES = (
    "new_system",
    "decommission",
    "outsourcing",
    "recategorization",
    "major_config",
    "new_supplier",
    "location_change",
    "legal_change",
)
CATEGORY_VALUES = ("BASICA", "MEDIA", "ALTA")
ROLE_PATTERNS = (
    "startup_unipersonal",
    "pyme_basica",
    "pyme_media",
    "empresa_grande",
    "admin_publica",
)
CAMPAIGN_TYPES = (
    "recertification_bianual",
    "renewal_declaracion",
    "overlay_renewal",
)
OVERLAY_TYPES = (
    "cloud_azure_es",
    "cloud_aws_eu",
    "cloud_gcp_eu",
    "uceens_ayuntamiento",
    "uceens_diputacion",
    "uceens_universidad",
)
LEAD_SOURCES = (
    "ens_radar",
    "referral",
    "event",
    "inbound_blog",
    "linkedin",
    "web_form",
    "cold_outreach",
)


def _pk() -> sa.Column:
    return sa.Column(
        "id", postgresql.UUID(as_uuid=True), primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _fk(name: str, target: str, *, nullable=False, on_delete: str | None = None):
    return sa.Column(
        name, postgresql.UUID(as_uuid=True),
        sa.ForeignKey(target, ondelete=on_delete) if on_delete
        else sa.ForeignKey(target),
        nullable=nullable, index=True,
    )


def _ts(name: str, *, server_default: str | None = None, nullable=True):
    kwargs = {"nullable": nullable}
    if server_default:
        kwargs["server_default"] = sa.text(server_default)
    return sa.Column(name, sa.TIMESTAMP(timezone=True), **kwargs)


def _created_at():
    return _ts("created_at", server_default="now()", nullable=False)


def _check_in(name: str, col: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        f"{col} IN (" + ", ".join(f"'{v}'" for v in values) + ")",
        name=name,
    )


def upgrade() -> None:
    # ── 1. conformity_routes ─────────────────────────────────────────
    op.create_table(
        "conformity_routes",
        _pk(),
        _fk("project_id", "projects.id", on_delete="CASCADE"),
        sa.Column("route_type", sa.String(40), nullable=False),
        sa.Column("route_subtype", sa.String(60), nullable=True),
        sa.Column("status", sa.String(30), nullable=False,
                  server_default="planned"),
        _ts("initiated_at", server_default="now()"),
        _ts("submitted_at"),
        _ts("accepted_at"),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("metadata_jsonb", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True),
        _created_at(),
        _check_in("ck_conformity_routes_type", "route_type", ROUTE_TYPES),
    )
    op.create_index(
        "ix_conformity_routes_project_status", "conformity_routes",
        ["project_id", "status"],
    )

    # ── 2. conformity_submissions (antes que basic_declarations por FK) ─
    op.create_table(
        "conformity_submissions",
        _pk(),
        _fk("project_id", "projects.id", on_delete="CASCADE"),
        sa.Column("submission_type", sa.String(30), nullable=False),
        sa.Column("external_system", sa.String(100), nullable=True),
        sa.Column("submitted_by", sa.String(50), nullable=True),
        _ts("submitted_at"),
        sa.Column("external_ref_id", sa.String(255), nullable=True),
        sa.Column("submission_payload_jsonb",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_jsonb",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(30), nullable=False,
                  server_default="pending"),
        sa.Column("errors_jsonb",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        _created_at(),
        _check_in("ck_conformity_submissions_type", "submission_type",
                  SUBMISSION_TYPES),
    )

    # ── 3. basic_declarations ────────────────────────────────────────
    op.create_table(
        "basic_declarations",
        _pk(),
        _fk("project_id", "projects.id", on_delete="CASCADE"),
        sa.Column("declaration_type", sa.String(20), nullable=False,
                  server_default="initial"),
        sa.Column("published_evidence_url", sa.String(500), nullable=True),
        _fk("self_assessment_report_id", "documents.id",
            nullable=True, on_delete="SET NULL"),
        sa.Column("responsible_person_name", sa.String(255), nullable=True),
        sa.Column("responsible_person_email", sa.String(255), nullable=True),
        _ts("signed_at"),
        sa.Column("signed_hash", sa.String(64), nullable=True),
        _fk("submission_id", "conformity_submissions.id",
            nullable=True, on_delete="SET NULL"),
        sa.Column("status", sa.String(30), nullable=False,
                  server_default="draft"),
        _created_at(),
        _check_in("ck_basic_declarations_type", "declaration_type",
                  DECLARATION_TYPES),
    )

    # ── 4. material_changes ──────────────────────────────────────────
    op.create_table(
        "material_changes",
        _pk(),
        _fk("project_id", "projects.id", on_delete="CASCADE"),
        sa.Column("change_type", sa.String(30), nullable=False),
        _ts("detected_at", server_default="now()"),
        sa.Column("detected_by", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("materiality_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("is_material", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("materiality_tree_answers_jsonb",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("triggered_extraordinary_audit", sa.Boolean(),
                  nullable=False, server_default=sa.text("false")),
        sa.Column("extraordinary_audit_id",
                  postgresql.UUID(as_uuid=True), nullable=True),
        _ts("closed_at"),
        sa.Column("closed_by", sa.String(50), nullable=True),
        sa.Column("status", sa.String(30), nullable=False,
                  server_default="open"),
        _created_at(),
        _check_in("ck_material_changes_type", "change_type",
                  MATERIAL_CHANGE_TYPES),
    )
    op.create_index(
        "ix_material_changes_project_is_material", "material_changes",
        ["project_id", "is_material"],
    )

    # ── 5. recategorizations ────────────────────────────────────────
    op.create_table(
        "recategorizations",
        _pk(),
        _fk("project_id", "projects.id", on_delete="CASCADE"),
        sa.Column("old_category", sa.String(10), nullable=False),
        sa.Column("new_category", sa.String(10), nullable=False),
        _fk("trigger_material_change_id", "material_changes.id",
            nullable=True, on_delete="SET NULL"),
        _fk("analysis_report_id", "documents.id",
            nullable=True, on_delete="SET NULL"),
        _ts("approved_at"),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("new_dda_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False,
                  server_default="pending"),
        _created_at(),
        _check_in("ck_recategorizations_old", "old_category", CATEGORY_VALUES),
        _check_in("ck_recategorizations_new", "new_category", CATEGORY_VALUES),
    )

    # ── 6. extraordinary_audits ─────────────────────────────────────
    op.create_table(
        "extraordinary_audits",
        _pk(),
        _fk("project_id", "projects.id", on_delete="CASCADE"),
        _fk("trigger_material_change_id", "material_changes.id",
            nullable=True, on_delete="SET NULL"),
        sa.Column("scope_description", sa.Text(), nullable=True),
        _ts("scheduled_for"),
        sa.Column("performed_by", sa.String(100), nullable=True),
        _ts("performed_at"),
        _fk("audit_report_id", "documents.id",
            nullable=True, on_delete="SET NULL"),
        sa.Column("findings_count", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("status", sa.String(30), nullable=False,
                  server_default="scheduled"),
        _created_at(),
    )

    # ── 7. role_topologies ──────────────────────────────────────────
    op.create_table(
        "role_topologies",
        _pk(),
        _fk("project_id", "projects.id", on_delete="CASCADE"),
        sa.Column("pattern", sa.String(40), nullable=False),
        sa.Column("total_persons", sa.Integer(), nullable=False),
        sa.Column("ens_roles_assigned_jsonb",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("exceptions_count", sa.Integer(), nullable=False,
                  server_default="0"),
        _ts("approved_at"),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("revision_date", sa.Date(), nullable=True),
        _created_at(),
        _check_in("ck_role_topologies_pattern", "pattern", ROLE_PATTERNS),
    )

    # ── 8. role_exception_memos ─────────────────────────────────────
    op.create_table(
        "role_exception_memos",
        _pk(),
        _fk("project_id", "projects.id", on_delete="CASCADE"),
        _fk("role_topology_id", "role_topologies.id", on_delete="CASCADE"),
        sa.Column("exception_description", sa.Text(), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("compensating_controls", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        _fk("document_id", "documents.id",
            nullable=True, on_delete="SET NULL"),
        _created_at(),
    )

    # ── 9. renewal_campaigns ────────────────────────────────────────
    op.create_table(
        "renewal_campaigns",
        _pk(),
        _fk("project_id", "projects.id", on_delete="CASCADE"),
        sa.Column("campaign_type", sa.String(40), nullable=False),
        _ts("scheduled_for"),
        sa.Column("auto_triggered", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("dossier_run_id", postgresql.UUID(as_uuid=True),
                  nullable=True),
        sa.Column("status", sa.String(30), nullable=False,
                  server_default="planned"),
        sa.Column("result_jsonb",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        _created_at(),
        _check_in("ck_renewal_campaigns_type", "campaign_type", CAMPAIGN_TYPES),
    )
    op.create_index(
        "ix_renewal_campaigns_project_scheduled", "renewal_campaigns",
        ["project_id", "scheduled_for"],
    )

    # ── 10. pce_overlays ────────────────────────────────────────────
    op.create_table(
        "pce_overlays",
        _pk(),
        _fk("project_id", "projects.id", on_delete="CASCADE"),
        sa.Column("overlay_type", sa.String(40), nullable=False),
        sa.Column("overlay_spec_version", sa.String(20), nullable=True),
        sa.Column("applicability_assessment_jsonb",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("extra_measures_jsonb",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("compliance_status", sa.String(30), nullable=False,
                  server_default="in_progress"),
        _fk("assessment_report_id", "documents.id",
            nullable=True, on_delete="SET NULL"),
        _created_at(),
        _check_in("ck_pce_overlays_type", "overlay_type", OVERLAY_TYPES),
    )

    # ── 11. effort_estimates ────────────────────────────────────────
    op.create_table(
        "effort_estimates",
        _pk(),
        _fk("project_id", "projects.id", on_delete="CASCADE"),
        sa.Column("phase", sa.String(30), nullable=False),
        sa.Column("estimated_hours", sa.Numeric(6, 2), nullable=False),
        sa.Column("estimated_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("actual_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("variance_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("calibrated_from_similar_projects_jsonb",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        _created_at(),
    )

    # ── 12. exploratory_meetings ────────────────────────────────────
    op.create_table(
        "exploratory_meetings",
        _pk(),
        _fk("client_id", "clients.id", on_delete="CASCADE"),
        sa.Column("lead_source", sa.String(40), nullable=True),
        _ts("meeting_date"),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("blocks_completed_jsonb",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("outputs_agente_18_jsonb",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("proposal_generated_id", postgresql.UUID(as_uuid=True),
                  nullable=True),
        sa.Column("conversion_status", sa.String(30), nullable=False,
                  server_default="proposal_pending"),
        _created_at(),
    )

    # ── 13. stakeholders_graph_snapshots ────────────────────────────
    op.create_table(
        "stakeholders_graph_snapshots",
        _pk(),
        _fk("project_id", "projects.id", on_delete="CASCADE"),
        _ts("snapshot_date", server_default="now()"),
        sa.Column("graph_data_jsonb",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("changed_from_previous", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("change_summary", sa.Text(), nullable=True),
        _created_at(),
    )

    # ── FK circular: material_changes -> extraordinary_audits ───────
    op.create_foreign_key(
        "fk_material_changes_extraordinary_audit",
        "material_changes", "extraordinary_audits",
        ["extraordinary_audit_id"], ["id"],
        ondelete="SET NULL",
    )

    # ── RLS project-scoped + client-scoped ──────────────────────────
    PROJECT_TABLES = (
        "conformity_routes", "basic_declarations", "conformity_submissions",
        "material_changes", "recategorizations", "extraordinary_audits",
        "role_topologies", "role_exception_memos", "renewal_campaigns",
        "pce_overlays", "effort_estimates", "stakeholders_graph_snapshots",
    )
    for table in PROJECT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} "
            "USING (project_id = current_project_id() OR project_id IS NULL)"
        )

    op.execute(
        "ALTER TABLE exploratory_meetings ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE exploratory_meetings FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        "CREATE POLICY client_isolation ON exploratory_meetings "
        "USING (client_id = current_client_id())"
    )


def downgrade() -> None:
    PROJECT_TABLES = (
        "conformity_routes", "basic_declarations", "conformity_submissions",
        "material_changes", "recategorizations", "extraordinary_audits",
        "role_topologies", "role_exception_memos", "renewal_campaigns",
        "pce_overlays", "effort_estimates", "stakeholders_graph_snapshots",
    )
    for table in PROJECT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute(
        "DROP POLICY IF EXISTS client_isolation ON exploratory_meetings"
    )
    op.execute(
        "ALTER TABLE exploratory_meetings DISABLE ROW LEVEL SECURITY"
    )

    op.drop_constraint(
        "fk_material_changes_extraordinary_audit",
        "material_changes", type_="foreignkey",
    )
    op.drop_table("stakeholders_graph_snapshots")
    op.drop_table("exploratory_meetings")
    op.drop_table("effort_estimates")
    op.drop_table("pce_overlays")
    op.drop_index(
        "ix_renewal_campaigns_project_scheduled",
        table_name="renewal_campaigns",
    )
    op.drop_table("renewal_campaigns")
    op.drop_table("role_exception_memos")
    op.drop_table("role_topologies")
    op.drop_table("extraordinary_audits")
    op.drop_table("recategorizations")
    op.drop_index(
        "ix_material_changes_project_is_material",
        table_name="material_changes",
    )
    op.drop_table("material_changes")
    op.drop_table("conformity_submissions")
    op.drop_table("basic_declarations")
    op.drop_index(
        "ix_conformity_routes_project_status",
        table_name="conformity_routes",
    )
    op.drop_table("conformity_routes")
