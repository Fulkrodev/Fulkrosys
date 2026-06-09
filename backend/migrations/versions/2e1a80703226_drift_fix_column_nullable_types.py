"""drift_fix_column_nullable_types

MIG-C · Mini-Sesión 11.5 · Sub-bloque 11.5.D · CAT-D alter_column subset.

Closes TODO-DB-DRIFT-001 categoría D alter_column (35 ALTER NOT NULL + 2 ALTER TYPE = 37 ops).

Scope (37 ops):
  D.1b · ALTER COLUMN SET NOT NULL (35 ops):
    - external_pentester_handoffs (2): kickoff_completed BOOLEAN + status TEXT
    - false_positive_patterns (1): times_matched INTEGER
    - pricing_catalog (2): version VARCHAR(20) + is_active BOOLEAN
    - remediation_retests (1): executed_at TIMESTAMP
    - retainer_quarterly_reports (6): activities_completed/activities_pending/activities_overdue/incidents_detected/normativa_changes_relevant/vulns_critical INTEGER
    - verification_findings (11): screenshots/zfp_gate1_dedup/zfp_gate2_fp_filter/zfp_gate3_cross_tool/zfp_gate4_retest/zfp_gate5_classification/mitre_techniques/remediation_requires_restart/remediation_requires_maintenance_window/status/remediated_verified
    - verification_runs (12): tools_config/tools_used JSONB + total_findings/confirmed_findings/critical_count/high_count/medium_count/low_count/info_count/delta_new/delta_resolved/delta_persistent INTEGER

  D.3b · ALTER COLUMN TYPE String(20) (2 ops):
    - collaborative_workspaces.estado VARCHAR(50) → String(20) (0 rows, safe)
    - retainer_activities.estado VARCHAR(50) → String(20) (max_len=10, safe)

Audit empírico pre-migration:
  - 35 SQL count(*) FILTER (WHERE col IS NULL) per columna = 0 NULLs en BD verificados (pricing_catalog 10 rows, false_positive_patterns 120 rows, verification_findings 16 rows, verification_runs 3 rows, etc.)
  - 2 max(length(estado)) verificados < 20 chars (safe shrink)

Excluidos MIG-C (movidos otras MIGs):
  - 29 ops models-only D.1a (BD NOT NULL → modelo nullable=True; alineado en commit predecesor sin migration)
  - 4 ops models-only D.4 (comment metadata; alineado en commit predecesor sin migration)
  - 9 drop_column + 5 idx + 4 FK acoplados → MIG-D
  - 1 tabla evidence_renewal_requests → MIG-E
  - RLS/triggers/funciones → MIG-F

Revision ID: 2e1a80703226
Revises: 97cf56901d4a
Create Date: 2026-04-30 11:20:45.584025
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '2e1a80703226'
down_revision: Union[str, None] = '97cf56901d4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================================================================
    # D.1b · ALTER COLUMN SET NOT NULL (35 ops · 0 NULLs verified)
    # ==================================================================

    # external_pentester_handoffs (2)
    op.alter_column('external_pentester_handoffs', 'kickoff_completed',
                    existing_type=sa.BOOLEAN(),
                    nullable=False,
                    existing_server_default=sa.text('false'))
    op.alter_column('external_pentester_handoffs', 'status',
                    existing_type=sa.TEXT(),
                    nullable=False,
                    existing_server_default=sa.text("'draft'::text"))

    # false_positive_patterns (1)
    op.alter_column('false_positive_patterns', 'times_matched',
                    existing_type=sa.INTEGER(),
                    nullable=False,
                    existing_server_default=sa.text('0'))

    # pricing_catalog (2)
    op.alter_column('pricing_catalog', 'version',
                    existing_type=sa.VARCHAR(length=20),
                    nullable=False)
    op.alter_column('pricing_catalog', 'is_active',
                    existing_type=sa.BOOLEAN(),
                    nullable=False)

    # remediation_retests (1)
    op.alter_column('remediation_retests', 'executed_at',
                    existing_type=postgresql.TIMESTAMP(timezone=True),
                    nullable=False,
                    existing_server_default=sa.text('now()'))

    # retainer_quarterly_reports (6 INTEGER counters)
    for col in ['activities_completed', 'activities_pending', 'activities_overdue',
                'incidents_detected', 'normativa_changes_relevant', 'vulns_critical']:
        op.alter_column('retainer_quarterly_reports', col,
                        existing_type=sa.INTEGER(),
                        nullable=False,
                        existing_server_default=sa.text('0'))

    # verification_findings (11 cols)
    op.alter_column('verification_findings', 'screenshots',
                    existing_type=postgresql.JSONB(astext_type=sa.Text()),
                    nullable=False,
                    existing_server_default=sa.text("'[]'::jsonb"))
    op.alter_column('verification_findings', 'zfp_gate1_dedup',
                    existing_type=sa.BOOLEAN(),
                    nullable=False,
                    existing_server_default=sa.text('false'))
    op.alter_column('verification_findings', 'zfp_gate2_fp_filter',
                    existing_type=sa.BOOLEAN(),
                    nullable=False,
                    existing_server_default=sa.text('false'))
    op.alter_column('verification_findings', 'zfp_gate3_cross_tool',
                    existing_type=sa.INTEGER(),
                    nullable=False,
                    existing_server_default=sa.text('0'))
    op.alter_column('verification_findings', 'zfp_gate4_retest',
                    existing_type=sa.TEXT(),
                    nullable=False,
                    existing_server_default=sa.text("'not_tested'::text"))
    op.alter_column('verification_findings', 'zfp_gate5_classification',
                    existing_type=sa.TEXT(),
                    nullable=False,
                    existing_server_default=sa.text("'needs_review'::text"))
    op.alter_column('verification_findings', 'mitre_techniques',
                    existing_type=postgresql.JSONB(astext_type=sa.Text()),
                    nullable=False,
                    existing_server_default=sa.text("'[]'::jsonb"))
    op.alter_column('verification_findings', 'remediation_requires_restart',
                    existing_type=sa.BOOLEAN(),
                    nullable=False,
                    existing_server_default=sa.text('false'))
    op.alter_column('verification_findings', 'remediation_requires_maintenance_window',
                    existing_type=sa.BOOLEAN(),
                    nullable=False,
                    existing_server_default=sa.text('false'))
    op.alter_column('verification_findings', 'status',
                    existing_type=sa.TEXT(),
                    nullable=False,
                    existing_server_default=sa.text("'open'::text"))
    op.alter_column('verification_findings', 'remediated_verified',
                    existing_type=sa.BOOLEAN(),
                    nullable=False,
                    existing_server_default=sa.text('false'))

    # verification_runs (12 cols)
    op.alter_column('verification_runs', 'tools_config',
                    existing_type=postgresql.JSONB(astext_type=sa.Text()),
                    nullable=False,
                    existing_server_default=sa.text("'{}'::jsonb"))
    op.alter_column('verification_runs', 'tools_used',
                    existing_type=postgresql.JSONB(astext_type=sa.Text()),
                    nullable=False,
                    existing_server_default=sa.text("'[]'::jsonb"))
    for col in ['total_findings', 'confirmed_findings', 'critical_count',
                'high_count', 'medium_count', 'low_count', 'info_count',
                'delta_new', 'delta_resolved', 'delta_persistent']:
        op.alter_column('verification_runs', col,
                        existing_type=sa.INTEGER(),
                        nullable=False,
                        existing_server_default=sa.text('0'))

    # ==================================================================
    # D.3b · ALTER COLUMN TYPE String(20) (2 ops · max_len verified safe)
    # ==================================================================

    op.alter_column('collaborative_workspaces', 'estado',
                    existing_type=sa.VARCHAR(length=50),
                    type_=sa.String(length=20),
                    existing_nullable=True)
    op.alter_column('retainer_activities', 'estado',
                    existing_type=sa.VARCHAR(length=50),
                    type_=sa.String(length=20),
                    existing_nullable=True)


def downgrade() -> None:
    # ==================================================================
    # D.3b reverse · ALTER COLUMN TYPE VARCHAR(50) (2 ops)
    # ==================================================================

    op.alter_column('retainer_activities', 'estado',
                    existing_type=sa.String(length=20),
                    type_=sa.VARCHAR(length=50),
                    existing_nullable=True)
    op.alter_column('collaborative_workspaces', 'estado',
                    existing_type=sa.String(length=20),
                    type_=sa.VARCHAR(length=50),
                    existing_nullable=True)

    # ==================================================================
    # D.1b reverse · ALTER COLUMN DROP NOT NULL (35 ops)
    # ==================================================================

    # verification_runs (12 cols inverso)
    for col in ['delta_persistent', 'delta_resolved', 'delta_new',
                'info_count', 'low_count', 'medium_count', 'high_count',
                'critical_count', 'confirmed_findings', 'total_findings']:
        op.alter_column('verification_runs', col,
                        existing_type=sa.INTEGER(),
                        nullable=True,
                        existing_server_default=sa.text('0'))
    op.alter_column('verification_runs', 'tools_used',
                    existing_type=postgresql.JSONB(astext_type=sa.Text()),
                    nullable=True,
                    existing_server_default=sa.text("'[]'::jsonb"))
    op.alter_column('verification_runs', 'tools_config',
                    existing_type=postgresql.JSONB(astext_type=sa.Text()),
                    nullable=True,
                    existing_server_default=sa.text("'{}'::jsonb"))

    # verification_findings (11 cols inverso)
    op.alter_column('verification_findings', 'remediated_verified',
                    existing_type=sa.BOOLEAN(),
                    nullable=True,
                    existing_server_default=sa.text('false'))
    op.alter_column('verification_findings', 'status',
                    existing_type=sa.TEXT(),
                    nullable=True,
                    existing_server_default=sa.text("'open'::text"))
    op.alter_column('verification_findings', 'remediation_requires_maintenance_window',
                    existing_type=sa.BOOLEAN(),
                    nullable=True,
                    existing_server_default=sa.text('false'))
    op.alter_column('verification_findings', 'remediation_requires_restart',
                    existing_type=sa.BOOLEAN(),
                    nullable=True,
                    existing_server_default=sa.text('false'))
    op.alter_column('verification_findings', 'mitre_techniques',
                    existing_type=postgresql.JSONB(astext_type=sa.Text()),
                    nullable=True,
                    existing_server_default=sa.text("'[]'::jsonb"))
    op.alter_column('verification_findings', 'zfp_gate5_classification',
                    existing_type=sa.TEXT(),
                    nullable=True,
                    existing_server_default=sa.text("'needs_review'::text"))
    op.alter_column('verification_findings', 'zfp_gate4_retest',
                    existing_type=sa.TEXT(),
                    nullable=True,
                    existing_server_default=sa.text("'not_tested'::text"))
    op.alter_column('verification_findings', 'zfp_gate3_cross_tool',
                    existing_type=sa.INTEGER(),
                    nullable=True,
                    existing_server_default=sa.text('0'))
    op.alter_column('verification_findings', 'zfp_gate2_fp_filter',
                    existing_type=sa.BOOLEAN(),
                    nullable=True,
                    existing_server_default=sa.text('false'))
    op.alter_column('verification_findings', 'zfp_gate1_dedup',
                    existing_type=sa.BOOLEAN(),
                    nullable=True,
                    existing_server_default=sa.text('false'))
    op.alter_column('verification_findings', 'screenshots',
                    existing_type=postgresql.JSONB(astext_type=sa.Text()),
                    nullable=True,
                    existing_server_default=sa.text("'[]'::jsonb"))

    # retainer_quarterly_reports (6 INTEGER counters inverso)
    for col in ['vulns_critical', 'normativa_changes_relevant', 'incidents_detected',
                'activities_overdue', 'activities_pending', 'activities_completed']:
        op.alter_column('retainer_quarterly_reports', col,
                        existing_type=sa.INTEGER(),
                        nullable=True,
                        existing_server_default=sa.text('0'))

    # remediation_retests (1)
    op.alter_column('remediation_retests', 'executed_at',
                    existing_type=postgresql.TIMESTAMP(timezone=True),
                    nullable=True,
                    existing_server_default=sa.text('now()'))

    # pricing_catalog (2)
    op.alter_column('pricing_catalog', 'is_active',
                    existing_type=sa.BOOLEAN(),
                    nullable=True)
    op.alter_column('pricing_catalog', 'version',
                    existing_type=sa.VARCHAR(length=20),
                    nullable=True)

    # false_positive_patterns (1)
    op.alter_column('false_positive_patterns', 'times_matched',
                    existing_type=sa.INTEGER(),
                    nullable=True,
                    existing_server_default=sa.text('0'))

    # external_pentester_handoffs (2)
    op.alter_column('external_pentester_handoffs', 'status',
                    existing_type=sa.TEXT(),
                    nullable=True,
                    existing_server_default=sa.text("'draft'::text"))
    op.alter_column('external_pentester_handoffs', 'kickoff_completed',
                    existing_type=sa.BOOLEAN(),
                    nullable=True,
                    existing_server_default=sa.text('false'))
