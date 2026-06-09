"""drift_fix_drop_column_legacy_client_id

MIG-D · Mini-Sesión 11.5 · Sub-bloque 11.5.E · CAT-D drop_column.

Closes TODO-DB-DRIFT-001 categoría D drop_column (12 ops drop_column/index/constraint client_id legacy + 4 alter_column comment ens_measure_evidencia_types = 16 ops).

Decisiones per columna (Marcos approval post audit empírico exhaustivo):

🚨 RESTORE OBLIGATORIO (5 cols models-only · sin migration · alinear declaration):
  - audit_log.seq: BIGSERIAL UNIQUE para HASH CHAIN tamper-evidence audit
    (RD 311/2022 ENS). Sequence audit_log_seq_seq pre-existing
    (last_value=898766). Triggers BD `fn_audit_log_hash_chain` ORDER BY seq +
    `fn_audit_log_verify_chain` integrity verification depend de ordering.
    Migration original `d4f8b2a90001` (2026-04-20). NO regenerar sequence.
  - ens_measure_evidencia_types (4 cols `format` + `source_tool` + `automatable`
    + `audit_query`): 105 rows × 4 cols catálogo ENS audit-grade. Migration
    original `f8c1e2d4a004` (2026-04-21) declaró feature catálogo expandido
    auditor template. Drop habría perdido semántica auditor query consulta.

✅ DROP LEGACY client_id (4 cols + 4 idx + 4 FK = 12 ops migration):
  - external_pentester_handoffs.client_id (1 row 100% NULL)
  - lms_assignments.client_id (0 rows · tabla vacía)
  - verification_findings.client_id (16 NULLs)
  - verification_runs.client_id (3 NULLs)

  Justificación DROP empírica:
  - Audit-1: 100% NULL en todas las rows existentes (4 tablas).
  - Audit-2: 0 referencias en `backend/app/` filter por client_id directo.
  - Audit-3: M8 v5.1 declaró denormalización opcional (migración
    `d5f9e3a6b209`); refactor histórico consolidó vía
    `project_id → projects.client_id` JOIN. Columna directa quedó vacía.

📝 COMMENT METADATA (4 ops alter_column · añadir comments docs auditor a BD):
  - ens_measure_evidencia_types: format, source_tool, automatable, audit_query
    (modelo declara comment="...", BD no los tiene → ALTER COLUMN ... COMMENT IS).

Backup BD pre-MIG-D snapshot: /tmp/db_pre_mig_d_backup_20260430_120346.sql

Revision ID: 53dead2ba760
Revises: 2e1a80703226
Create Date: 2026-04-30 12:05:23.075469
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '53dead2ba760'
down_revision: Union[str, None] = '2e1a80703226'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================================================================
    # DROP LEGACY client_id × 4 tablas (12 ops · 100% NULL verified)
    # ==================================================================

    # external_pentester_handoffs (1 row NULL)
    op.drop_constraint(
        'external_pentester_handoffs_client_id_fkey',
        'external_pentester_handoffs',
        type_='foreignkey',
    )
    op.drop_index(
        'ix_external_pentester_handoffs_client_id',
        table_name='external_pentester_handoffs',
    )
    op.drop_column('external_pentester_handoffs', 'client_id')

    # lms_assignments (0 rows · tabla vacía)
    op.drop_constraint(
        'lms_assignments_client_id_fkey',
        'lms_assignments',
        type_='foreignkey',
    )
    op.drop_index(
        'ix_lms_assignments_client_id',
        table_name='lms_assignments',
    )
    op.drop_column('lms_assignments', 'client_id')

    # verification_findings (16 NULLs)
    op.drop_constraint(
        'verification_findings_client_id_fkey',
        'verification_findings',
        type_='foreignkey',
    )
    op.drop_index(
        'ix_verification_findings_client_id',
        table_name='verification_findings',
    )
    op.drop_column('verification_findings', 'client_id')

    # verification_runs (3 NULLs)
    op.drop_constraint(
        'verification_runs_client_id_fkey',
        'verification_runs',
        type_='foreignkey',
    )
    op.drop_index(
        'ix_verification_runs_client_id',
        table_name='verification_runs',
    )
    op.drop_column('verification_runs', 'client_id')

    # ==================================================================
    # COMMENT METADATA · ens_measure_evidencia_types (4 alter_column)
    # ==================================================================

    op.alter_column(
        'ens_measure_evidencia_types', 'format',
        existing_type=sa.VARCHAR(length=120),
        comment='Formato esperado evidencia (ej: plain/png · ext .txt,.png).',
        existing_nullable=True,
    )
    op.alter_column(
        'ens_measure_evidencia_types', 'source_tool',
        existing_type=sa.VARCHAR(length=120),
        comment='Tool/sistema generador evidencia (ej: Firewall + NAC + inspección TLS).',
        existing_nullable=True,
    )
    op.alter_column(
        'ens_measure_evidencia_types', 'automatable',
        existing_type=sa.BOOLEAN(),
        comment='¿Esta evidencia automatizable via tools/scripts?',
        existing_nullable=False,
        existing_server_default=sa.text('false'),
    )
    op.alter_column(
        'ens_measure_evidencia_types', 'audit_query',
        existing_type=sa.TEXT(),
        comment='Query auditor template (ej: ¿Puede aportar la configuración de red...?).',
        existing_nullable=True,
    )


def downgrade() -> None:
    # ==================================================================
    # COMMENT METADATA reverse · ens_measure_evidencia_types (4 ops)
    # ==================================================================

    op.alter_column(
        'ens_measure_evidencia_types', 'audit_query',
        existing_type=sa.TEXT(),
        comment=None,
        existing_nullable=True,
    )
    op.alter_column(
        'ens_measure_evidencia_types', 'automatable',
        existing_type=sa.BOOLEAN(),
        comment=None,
        existing_nullable=False,
        existing_server_default=sa.text('false'),
    )
    op.alter_column(
        'ens_measure_evidencia_types', 'source_tool',
        existing_type=sa.VARCHAR(length=120),
        comment=None,
        existing_nullable=True,
    )
    op.alter_column(
        'ens_measure_evidencia_types', 'format',
        existing_type=sa.VARCHAR(length=120),
        comment=None,
        existing_nullable=True,
    )

    # ==================================================================
    # RESTORE client_id × 4 tablas inverso (12 ops)
    # NOTA: data perdida en upgrade NO se recupera automáticamente.
    # Columnas restauradas como nullable=True con FK ON DELETE SET NULL.
    # ==================================================================

    # verification_runs
    op.add_column(
        'verification_runs',
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        'ix_verification_runs_client_id',
        'verification_runs', ['client_id'],
    )
    op.create_foreign_key(
        'verification_runs_client_id_fkey',
        'verification_runs', 'clients',
        ['client_id'], ['id'],
    )

    # verification_findings
    op.add_column(
        'verification_findings',
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        'ix_verification_findings_client_id',
        'verification_findings', ['client_id'],
    )
    op.create_foreign_key(
        'verification_findings_client_id_fkey',
        'verification_findings', 'clients',
        ['client_id'], ['id'],
    )

    # lms_assignments
    op.add_column(
        'lms_assignments',
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        'ix_lms_assignments_client_id',
        'lms_assignments', ['client_id'],
    )
    op.create_foreign_key(
        'lms_assignments_client_id_fkey',
        'lms_assignments', 'clients',
        ['client_id'], ['id'],
    )

    # external_pentester_handoffs
    op.add_column(
        'external_pentester_handoffs',
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        'ix_external_pentester_handoffs_client_id',
        'external_pentester_handoffs', ['client_id'],
    )
    op.create_foreign_key(
        'external_pentester_handoffs_client_id_fkey',
        'external_pentester_handoffs', 'clients',
        ['client_id'], ['id'],
    )
