"""remediation_enhancement_b35_e_001 · Bloque 3+5 Enhancement Phase A refined.

Extensión Phase A refined Path B (OPS-052 13ª manifestation):
  - ADD COLUMN idempotency_key a cloud_remediation_approval_logs (prevent duplicate logs)
  - ADD COLUMN failure_category a cloud_remediation_approval_logs (transient|permanent|partial|unknown)
  - ADD COLUMN correlation_id a cloud_remediation_approval_logs (cross-references)
  - ADD COLUMN verification_pending_at a cloud_gaps (NEW state · admin post-execute reports verify)
  - ADD COLUMN verified_at a cloud_gaps (terminal · post verification success)

ADR-025 sostained · NO new tables · solo ALTER additive con DEFAULT safe backfill.
ADR-014 sostained · NO auto-execute capability · solo enrich audit metadata.
ADR-031 reinforced · audit trail ENAC-completeness per state transition.

Revision ID: remediation_enhancement_b35_e_001
Revises: cloud_remediation_orchestrator_b35_001
Create Date: 2026-05-25
"""
from typing import Sequence, Union

from alembic import op


revision: str = "remediation_enhancement_b35_e_001"
down_revision: Union[str, None] = "cloud_remediation_orchestrator_b35_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================================================================
    # 1. cloud_remediation_approval_logs · idempotency + enrichment
    # ==================================================================
    op.execute(
        """
        ALTER TABLE cloud_remediation_approval_logs
            ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(128) NULL,
            ADD COLUMN IF NOT EXISTS failure_category VARCHAR(20) NULL,
            ADD COLUMN IF NOT EXISTS correlation_id UUID NULL
        """
    )

    # UNIQUE constraint sobre (gap_id · action · idempotency_key)
    # idempotency_key NULL permite multiple logs sin key (backward-compat)
    # idempotency_key NOT NULL enforces dedup per gap+action+key tuple
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_cloud_remediation_logs_idempotency
            ON cloud_remediation_approval_logs (gap_id, action, idempotency_key)
            WHERE idempotency_key IS NOT NULL
        """
    )

    # Index per correlation_id (cross-references query)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cloud_remediation_logs_correlation
            ON cloud_remediation_approval_logs (correlation_id)
            WHERE correlation_id IS NOT NULL
        """
    )

    # Index per failure_category (admin filter failures by type)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cloud_remediation_logs_failure_category
            ON cloud_remediation_approval_logs (project_id, failure_category, created_at DESC)
            WHERE failure_category IS NOT NULL
        """
    )

    # ==================================================================
    # 2. cloud_gaps · VERIFICATION_PENDING + VERIFIED state extensions
    # ==================================================================
    op.execute(
        """
        ALTER TABLE cloud_gaps
            ADD COLUMN IF NOT EXISTS verification_pending_at TIMESTAMPTZ NULL,
            ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ NULL,
            ADD COLUMN IF NOT EXISTS verified_by_user_id UUID NULL
        """
    )

    # Index per verification_pending_at (admin dashboard pending verification feed)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cloud_gaps_verification_pending
            ON cloud_gaps (project_id, verification_pending_at)
            WHERE verification_pending_at IS NOT NULL AND verified_at IS NULL
        """
    )


def downgrade() -> None:
    # Reverse order safe
    op.execute(
        "DROP INDEX IF EXISTS ix_cloud_gaps_verification_pending"
    )
    op.execute(
        """
        ALTER TABLE cloud_gaps
            DROP COLUMN IF EXISTS verified_by_user_id,
            DROP COLUMN IF EXISTS verified_at,
            DROP COLUMN IF EXISTS verification_pending_at
        """
    )
    op.execute(
        "DROP INDEX IF EXISTS ix_cloud_remediation_logs_failure_category"
    )
    op.execute(
        "DROP INDEX IF EXISTS ix_cloud_remediation_logs_correlation"
    )
    op.execute(
        "DROP INDEX IF EXISTS ux_cloud_remediation_logs_idempotency"
    )
    op.execute(
        """
        ALTER TABLE cloud_remediation_approval_logs
            DROP COLUMN IF EXISTS correlation_id,
            DROP COLUMN IF EXISTS failure_category,
            DROP COLUMN IF EXISTS idempotency_key
        """
    )
