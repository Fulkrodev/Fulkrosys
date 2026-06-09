"""m8 autopilot canonical model · elevate Finding + Verdict + EvidenceRecord + run autopilot/manifest/ephemeral

Fase 1 del rebuild M8 Pentesting Autopilot v2.0 (docs/spec/M8_AUTOPILOT_ARCHITECTURE_v2.md).

Additive · backward-compat (todas las columnas nuevas nullable o con server_default).
NO destruye nada vivo: eleva verification_findings → Finding canónico, extiende
verification_runs, y crea m8_verdicts (advisory) + m8_evidence_records (append-only R6).

Append-only de m8_evidence_records garantizado reutilizando la infraestructura R6
existente (migración d4f8b2a90001):
  - fn_audit_track  (AFTER INSERT) → espeja cada row al audit_log hash-chaineado
  - fn_audit_log_immutable (BEFORE UPDATE/DELETE) → rechaza mutación (append-only)

RLS replica el patrón project_isolation de 33cef115cdf5 (current_project_id()).

Revision ID: m8_autopilot_canonical_001
Revises: drop_ens_radar_001
Create Date: 2026-06-08

Re-parent (merge integration-m8 · 2026-06-08): down_revision pasa de
``radar_v3_fase7_directory_match_001`` (cadena radar de main) a
``drop_ens_radar_001`` (head de batch2 que elimina el subsistema ENS Radar).
M8 es additive sobre las tablas m08 existentes y NO depende de ninguna tabla
radar, por lo que el re-parent es limpio: cadena lineal · 1 solo head ·
sin tablas radar en el esquema final.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "m8_autopilot_canonical_001"
down_revision: Union[str, None] = "drop_ens_radar_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ts(nullable: bool = True):
    return sa.Column(
        "_", postgresql.TIMESTAMP(timezone=True), nullable=nullable,
    )


def upgrade() -> None:
    # ════════════════════════════════════════════════════════════════
    # 1. verification_runs · autopilot + manifest + coverage + ephemeral
    # ════════════════════════════════════════════════════════════════
    op.add_column("verification_runs", sa.Column("run_manifest_hash", sa.Text(), nullable=True))
    op.add_column("verification_runs", sa.Column("golden_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("verification_runs", sa.Column("coverage_pct", sa.Numeric(5, 2), nullable=True))
    op.add_column("verification_runs", sa.Column("assets_in_scope", sa.Integer(), server_default="0", nullable=False))
    op.add_column("verification_runs", sa.Column("assets_scanned", sa.Integer(), server_default="0", nullable=False))
    op.add_column("verification_runs", sa.Column("autopilot_status", sa.Text(), nullable=True))
    op.add_column("verification_runs", sa.Column("autopilot_phase", sa.Text(), nullable=True))
    op.add_column("verification_runs", sa.Column("partial_run", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("verification_runs", sa.Column("tools_attempted", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.add_column("verification_runs", sa.Column("tools_failed", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.add_column("verification_runs", sa.Column("ephemeral_session_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("verification_runs", sa.Column("ephemeral_expires_at", postgresql.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("verification_runs", sa.Column("ephemeral_revoked_at", postgresql.TIMESTAMP(timezone=True), nullable=True))
    op.create_index(
        "ix_vr_autopilot_status", "verification_runs",
        ["project_id", "autopilot_status"],
        postgresql_where=sa.text("autopilot_status IS NOT NULL"),
    )

    # ════════════════════════════════════════════════════════════════
    # 2. verification_findings · Finding canónico ELEVADO
    # ════════════════════════════════════════════════════════════════
    op.add_column("verification_findings", sa.Column("epss_score", sa.Numeric(5, 4), nullable=True))
    op.add_column("verification_findings", sa.Column("verification_level", sa.Text(), server_default="unverified", nullable=False))
    op.add_column("verification_findings", sa.Column("finding_state", sa.Text(), server_default="detected", nullable=False))
    op.add_column("verification_findings", sa.Column("dedup_group_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("verification_findings", sa.Column("first_seen", postgresql.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("verification_findings", sa.Column("last_seen", postgresql.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("verification_findings", sa.Column("source_engine", sa.Text(), nullable=True))
    op.add_column("verification_findings", sa.Column("engine_version", sa.Text(), nullable=True))
    op.add_column("verification_findings", sa.Column("rule_id", sa.Text(), nullable=True))
    op.add_column("verification_findings", sa.Column("asset_node_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("verification_findings", sa.Column("sarif_ref", sa.Text(), nullable=True))
    op.add_column("verification_findings", sa.Column("risk_accepted_expires_at", postgresql.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("verification_findings", sa.Column("risk_accepted_by", sa.Text(), nullable=True))
    op.create_index("idx_vf_finding_state", "verification_findings", ["run_id", "finding_state"])
    op.create_index(
        "idx_vf_dedup_group", "verification_findings", ["dedup_group_id"],
        postgresql_where=sa.text("dedup_group_id IS NOT NULL"),
    )
    op.create_index(
        "idx_vf_asset_node", "verification_findings", ["asset_node_id"],
        postgresql_where=sa.text("asset_node_id IS NOT NULL"),
    )

    # ════════════════════════════════════════════════════════════════
    # 3. m8_verdicts · anotación agente ADVISORY (mutable · tracked)
    # ════════════════════════════════════════════════════════════════
    op.create_table(
        "m8_verdicts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("verification_runs.id"), nullable=False),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("verification_findings.id"), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("prompt_hash", sa.Text(), nullable=True),
        sa.Column("input_refs", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("triage", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("structured_output_valid", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("decision_log_ref", sa.Text(), nullable=True),
        sa.Column("human_override", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_m8_verdicts_project_id", "m8_verdicts", ["project_id"])
    op.create_index("idx_m8v_finding", "m8_verdicts", ["finding_id"])
    op.create_index("idx_m8v_run", "m8_verdicts", ["run_id"])

    # ════════════════════════════════════════════════════════════════
    # 4. m8_evidence_records · APPEND-ONLY (doc §4 · R6 pgAudit)
    # ════════════════════════════════════════════════════════════════
    op.create_table(
        "m8_evidence_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("run_manifest_hash", sa.Text(), nullable=True),
        sa.Column("ts", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("component", sa.Text(), nullable=True),
        sa.Column("input_hash", sa.Text(), nullable=True),
        sa.Column("output_hash", sa.Text(), nullable=True),
        sa.Column("ens_relevance", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_m8_evidence_records_project_id", "m8_evidence_records", ["project_id"])
    op.create_index("ix_m8_evidence_records_client_id", "m8_evidence_records", ["client_id"])
    op.create_index("idx_m8er_run", "m8_evidence_records", ["run_id"])

    # ── Append-only enforcement reutilizando R6 (d4f8b2a90001) ──────
    # fn_audit_track espeja INSERT al audit_log hash-chaineado;
    # fn_audit_log_immutable rechaza UPDATE/DELETE (write-once).
    op.execute(
        """
        DO $do$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_proc WHERE proname='fn_audit_track') THEN
            EXECUTE 'CREATE TRIGGER tg_audit_m8_evidence_records
                     AFTER INSERT ON m8_evidence_records
                     FOR EACH ROW EXECUTE FUNCTION fn_audit_track()';
          END IF;
          IF EXISTS (SELECT 1 FROM pg_proc WHERE proname='fn_audit_log_immutable') THEN
            EXECUTE 'CREATE TRIGGER tg_m8_evidence_no_update
                     BEFORE UPDATE ON m8_evidence_records
                     FOR EACH ROW EXECUTE FUNCTION fn_audit_log_immutable()';
            EXECUTE 'CREATE TRIGGER tg_m8_evidence_no_delete
                     BEFORE DELETE ON m8_evidence_records
                     FOR EACH ROW EXECUTE FUNCTION fn_audit_log_immutable()';
          END IF;
          -- verdicts mutables (human_override) · solo audit trail
          IF EXISTS (SELECT 1 FROM pg_proc WHERE proname='fn_audit_track') THEN
            EXECUTE 'CREATE TRIGGER tg_audit_m8_verdicts
                     AFTER INSERT OR UPDATE OR DELETE ON m8_verdicts
                     FOR EACH ROW EXECUTE FUNCTION fn_audit_track()';
          END IF;
        END
        $do$;
        """
    )

    # ════════════════════════════════════════════════════════════════
    # 5. RLS · replica project_isolation (33cef115cdf5 · current_project_id())
    # ════════════════════════════════════════════════════════════════
    for table in ("m8_verdicts", "m8_evidence_records"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} "
            f"USING (project_id = current_project_id())"
        )
    # evidence_records: INSERT permisivo (servicios background emiten · igual
    # que audit_log_insert_permissive · app role BYPASSRLS de todas formas)
    op.execute(
        "CREATE POLICY m8_evidence_insert_permissive ON m8_evidence_records "
        "FOR INSERT WITH CHECK (true)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS m8_evidence_insert_permissive ON m8_evidence_records")
    for table in ("m8_verdicts", "m8_evidence_records"):
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS tg_audit_m8_verdicts ON m8_verdicts")
    op.execute("DROP TRIGGER IF EXISTS tg_m8_evidence_no_delete ON m8_evidence_records")
    op.execute("DROP TRIGGER IF EXISTS tg_m8_evidence_no_update ON m8_evidence_records")
    op.execute("DROP TRIGGER IF EXISTS tg_audit_m8_evidence_records ON m8_evidence_records")

    op.drop_index("idx_m8er_run", table_name="m8_evidence_records")
    op.drop_index("ix_m8_evidence_records_client_id", table_name="m8_evidence_records")
    op.drop_index("ix_m8_evidence_records_project_id", table_name="m8_evidence_records")
    op.drop_table("m8_evidence_records")

    op.drop_index("idx_m8v_run", table_name="m8_verdicts")
    op.drop_index("idx_m8v_finding", table_name="m8_verdicts")
    op.drop_index("ix_m8_verdicts_project_id", table_name="m8_verdicts")
    op.drop_table("m8_verdicts")

    op.drop_index("idx_vf_asset_node", table_name="verification_findings")
    op.drop_index("idx_vf_dedup_group", table_name="verification_findings")
    op.drop_index("idx_vf_finding_state", table_name="verification_findings")
    for col in (
        "risk_accepted_by", "risk_accepted_expires_at", "sarif_ref", "asset_node_id",
        "rule_id", "engine_version", "source_engine", "last_seen", "first_seen",
        "dedup_group_id", "finding_state", "verification_level", "epss_score",
    ):
        op.drop_column("verification_findings", col)

    op.drop_index("ix_vr_autopilot_status", table_name="verification_runs")
    for col in (
        "ephemeral_revoked_at", "ephemeral_expires_at", "ephemeral_session_id",
        "tools_failed", "tools_attempted", "partial_run", "autopilot_phase",
        "autopilot_status", "assets_scanned", "assets_in_scope", "coverage_pct",
        "golden_run_id", "run_manifest_hash",
    ):
        op.drop_column("verification_runs", col)
