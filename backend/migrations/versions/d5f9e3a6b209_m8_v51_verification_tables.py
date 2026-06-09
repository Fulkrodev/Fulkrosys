"""M8 v5.1 — Verificacion Tecnica: 5 tablas (spec MOTOR_8_v5_1_SPEC §8.1).

Tablas creadas:
1. verification_runs              — engagements (Basica/Media/Alta)
2. verification_findings          — hallazgos individuales con ZFP
3. external_pentester_handoffs    — paquetes engagement Alta
4. false_positive_patterns        — base FP aprendidos (~500 inicial)
5. remediation_retests            — re-tests quirurgicos post-fix

Revision ID: d5f9e3a6b209
Revises: c4e8d2f5a108 (drop M8 v4.2)
Create Date: 2026-04-21 14:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d5f9e3a6b209"
down_revision: Union[str, None] = "c4e8d2f5a108"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ════════════════════════════════════════════════════════════════
    # TABLA 1: verification_runs
    # ════════════════════════════════════════════════════════════════
    op.create_table(
        "verification_runs",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id"), nullable=True, index=True,
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False, index=True,
        ),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default="pending",
        ),
        # Scope auto-derivado
        sa.Column("scope_jsonb", postgresql.JSONB(), nullable=False),
        sa.Column("scope_derived_from", postgresql.JSONB(), nullable=True),
        # Ejecucion
        sa.Column(
            "tools_config", postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "tools_used", postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("scheduled_start", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("phase1_started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("phase1_completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("phase2_started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("phase2_completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("phase3_started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # Autorizacion
        sa.Column("authorized_by", sa.Text(), nullable=True),
        sa.Column(
            "authorization_magic_link_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("magic_links.id"), nullable=True,
        ),
        sa.Column(
            "authorization_signed_at", sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        # Externo (solo Alta)
        sa.Column("external_pentester_name", sa.Text(), nullable=True),
        sa.Column("external_pentester_cert", sa.Text(), nullable=True),
        sa.Column("external_pentester_email", sa.Text(), nullable=True),
        sa.Column("external_report_original_path", sa.Text(), nullable=True),
        sa.Column(
            "external_portal_magic_link_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("magic_links.id"), nullable=True,
        ),
        # Resultados agregados
        sa.Column(
            "total_findings", sa.Integer(), server_default="0",
        ),
        sa.Column(
            "confirmed_findings", sa.Integer(), server_default="0",
        ),
        sa.Column("critical_count", sa.Integer(), server_default="0"),
        sa.Column("high_count", sa.Integer(), server_default="0"),
        sa.Column("medium_count", sa.Integer(), server_default="0"),
        sa.Column("low_count", sa.Integer(), server_default="0"),
        sa.Column("info_count", sa.Integer(), server_default="0"),
        sa.Column("security_score", sa.Integer(), nullable=True),
        # Delta con run anterior
        sa.Column(
            "previous_run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("verification_runs.id"), nullable=True,
        ),
        sa.Column("delta_new", sa.Integer(), server_default="0"),
        sa.Column("delta_resolved", sa.Integer(), server_default="0"),
        sa.Column("delta_persistent", sa.Integer(), server_default="0"),
        # Metadata + FullMixin
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.Text(), server_default="marcos"),
    )
    op.create_check_constraint(
        "chk_vr_category", "verification_runs",
        "category IN ('BASICO','MEDIO','ALTO')",
    )
    op.create_check_constraint(
        "chk_vr_mode", "verification_runs",
        "mode IN ('internal','external_handoff','external_ingest_pdf','external_ingest_form')",
    )
    op.create_check_constraint(
        "chk_vr_status", "verification_runs",
        "status IN ('pending','authorized','scheduled','phase1_running',"
        "'phase2_running','phase3_validating','completed','cancelled',"
        "'handoff_ready','handoff_sent','pentester_working',"
        "'report_received','integrated')",
    )
    op.create_index(
        "ix_vr_project_status", "verification_runs",
        ["project_id", "status"],
    )

    # ════════════════════════════════════════════════════════════════
    # TABLA 2: verification_findings
    # ════════════════════════════════════════════════════════════════
    op.create_table(
        "verification_findings",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id"), nullable=True, index=True,
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False, index=True,
        ),
        sa.Column(
            "run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("verification_runs.id"), nullable=False,
        ),
        # Identificacion
        sa.Column("finding_hash", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("cvss_score", sa.Numeric(3, 1), nullable=True),
        sa.Column("cvss_vector", sa.Text(), nullable=True),
        sa.Column("cve_id", sa.Text(), nullable=True),
        sa.Column("cwe_id", sa.Text(), nullable=True),
        # Localizacion
        sa.Column("affected_host", sa.Text(), nullable=False),
        sa.Column("affected_port", sa.Integer(), nullable=True),
        sa.Column("affected_service", sa.Text(), nullable=True),
        sa.Column("affected_service_version", sa.Text(), nullable=True),
        sa.Column("affected_url", sa.Text(), nullable=True),
        sa.Column("affected_os", sa.Text(), nullable=True),
        # Evidencia / cadena de custodia
        sa.Column(
            "tool_sources", postgresql.JSONB(), nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "raw_outputs", postgresql.JSONB(), nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "screenshots", postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
        ),
        # ZFP — los 5 gates
        sa.Column(
            "confidence_score", sa.Numeric(3, 2), nullable=False,
            server_default="0.50",
        ),
        sa.Column(
            "zfp_gate1_dedup", sa.Boolean(), server_default="false",
        ),
        sa.Column(
            "zfp_gate2_fp_filter", sa.Boolean(), server_default="false",
        ),
        sa.Column(
            "zfp_gate3_cross_tool", sa.Integer(), server_default="0",
        ),
        sa.Column(
            "zfp_gate4_retest", sa.Text(), server_default="not_tested",
        ),
        sa.Column(
            "zfp_gate5_classification", sa.Text(),
            server_default="needs_review",
        ),
        # Mapeo ENS (multi-medida)
        sa.Column(
            "ens_measures", postgresql.JSONB(), nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("ens_primary_measure", sa.Text(), nullable=True),
        # MITRE ATT&CK
        sa.Column(
            "mitre_techniques", postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
        ),
        # Remediacion
        sa.Column("remediation_summary", sa.Text(), nullable=False),
        sa.Column("remediation_guide_jsonb", postgresql.JSONB(), nullable=True),
        sa.Column("remediation_effort", sa.Text(), nullable=True),
        sa.Column("remediation_time_estimate", sa.Text(), nullable=True),
        sa.Column(
            "remediation_requires_restart", sa.Boolean(),
            server_default="false",
        ),
        sa.Column(
            "remediation_requires_maintenance_window", sa.Boolean(),
            server_default="false",
        ),
        sa.Column("remediation_priority", sa.Integer(), nullable=True),
        # Estado
        sa.Column(
            "status", sa.Text(), server_default="open",
        ),
        sa.Column("remediated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "remediated_verified", sa.Boolean(), server_default="false",
        ),
        sa.Column(
            "remediated_retest_run_id", postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("accepted_risk_justification", sa.Text(), nullable=True),
        sa.Column("accepted_risk_approved_by", sa.Text(), nullable=True),
        sa.Column("false_positive_reason", sa.Text(), nullable=True),
        # FullMixin
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "chk_vf_severity", "verification_findings",
        "severity IN ('critical','high','medium','low','info')",
    )
    op.create_check_constraint(
        "chk_vf_zfp4", "verification_findings",
        "zfp_gate4_retest IN ('not_tested','confirmed','not_confirmed','not_applicable')",
    )
    op.create_check_constraint(
        "chk_vf_zfp5", "verification_findings",
        "zfp_gate5_classification IN ('confirmed','probable','needs_review','rejected')",
    )
    op.create_check_constraint(
        "chk_vf_remed_effort", "verification_findings",
        "remediation_effort IS NULL OR remediation_effort IN "
        "('quick_win','short_term','long_term')",
    )
    op.create_check_constraint(
        "chk_vf_status", "verification_findings",
        "status IN ('open','remediated','accepted_risk','false_positive','needs_review')",
    )
    op.create_index(
        "idx_vf_run_severity", "verification_findings",
        ["run_id", "severity"],
    )
    op.create_index(
        "idx_vf_run_status", "verification_findings",
        ["run_id", "status"],
    )
    op.create_index(
        "idx_vf_finding_hash", "verification_findings",
        ["finding_hash"],
    )
    op.create_index(
        "idx_vf_ens_primary", "verification_findings",
        ["ens_primary_measure"],
    )

    # ════════════════════════════════════════════════════════════════
    # TABLA 3: external_pentester_handoffs
    # ════════════════════════════════════════════════════════════════
    op.create_table(
        "external_pentester_handoffs",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id"), nullable=True, index=True,
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False, index=True,
        ),
        sa.Column(
            "run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("verification_runs.id"), nullable=False,
        ),
        sa.Column("package_documents", postgresql.JSONB(), nullable=False),
        # VPN
        sa.Column("vpn_config_path", sa.Text(), nullable=True),
        sa.Column("vpn_credentials_encrypted", sa.Text(), nullable=True),
        # Portal
        sa.Column(
            "portal_magic_link_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("magic_links.id"), nullable=True,
        ),
        sa.Column("portal_url", sa.Text(), nullable=True),
        # Coordinacion
        sa.Column("kickoff_scheduled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "kickoff_completed", sa.Boolean(), server_default="false",
        ),
        sa.Column("deadline", sa.TIMESTAMP(timezone=True), nullable=True),
        # Entrega
        sa.Column("findings_submission_method", sa.Text(), nullable=True),
        sa.Column(
            "report_received_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "total_findings_received", sa.Integer(), nullable=True,
        ),
        sa.Column(
            "status", sa.Text(), server_default="draft",
        ),
        # FullMixin
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "chk_eph_submission", "external_pentester_handoffs",
        "findings_submission_method IS NULL OR "
        "findings_submission_method IN ('pdf','structured_form','both')",
    )
    op.create_check_constraint(
        "chk_eph_status", "external_pentester_handoffs",
        "status IN ('draft','portal_ready','sent','accepted','in_progress',"
        "'report_received','integrated','closed')",
    )

    # ════════════════════════════════════════════════════════════════
    # TABLA 4: false_positive_patterns
    # ════════════════════════════════════════════════════════════════
    op.create_table(
        "false_positive_patterns",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tool", sa.Text(), nullable=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("condition_jsonb", postgresql.JSONB(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "learned_from_project_id", postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("times_matched", sa.Integer(), server_default="0"),
        # FullMixin
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.Text(), server_default="marcos"),
    )
    op.create_index(
        "idx_fpp_tool", "false_positive_patterns",
        ["tool"],
    )

    # ════════════════════════════════════════════════════════════════
    # TABLA 5: remediation_retests
    # ════════════════════════════════════════════════════════════════
    op.create_table(
        "remediation_retests",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "finding_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("verification_findings.id"), nullable=False,
        ),
        sa.Column("triggered_by", sa.Text(), nullable=True),
        sa.Column("retest_type", sa.Text(), nullable=False),
        sa.Column("retest_command", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("result_detail", sa.Text(), nullable=True),
        sa.Column("raw_output_path", sa.Text(), nullable=True),
        sa.Column(
            "executed_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
        ),
        # Soft-delete (no necesita FullMixin completo)
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "chk_rr_triggered_by", "remediation_retests",
        "triggered_by IS NULL OR triggered_by IN "
        "('client_portal','marcos','scheduled')",
    )
    op.create_check_constraint(
        "chk_rr_result", "remediation_retests",
        "result IS NULL OR result IN "
        "('fixed','still_present','error','inconclusive')",
    )
    op.create_index(
        "idx_rr_finding", "remediation_retests", ["finding_id"],
    )


def downgrade() -> None:
    op.drop_table("remediation_retests")
    op.drop_table("false_positive_patterns")
    op.drop_table("external_pentester_handoffs")
    op.drop_table("verification_findings")
    op.drop_table("verification_runs")
