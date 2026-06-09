"""mb6_drift_cleanup_committee_meetings_index_rename

Revision ID: 5eaaaaee3714
Revises: 9d1b4035222b
Create Date: 2026-05-11

SAN-E v3.MB-6 cierre real · drift cleanup focused (atom 5 self-inflicted).

Atom 5 (fb5ef0575945) creó `idx_committee_meetings_client_review` para
ClientReviewMixinA pattern · pero el modelo declara `*client_review_a_table_args(
"committee_meetings")` que genera nombre `idx_committee_meetings_client_review_status`.

Reconciliación: RENAME BD index → match helper-generated name (model
declarative source of truth).

Pre-existing drift de atoms 5.3-5.6 (magerit_assets · magerit_threat_assessment ·
retainer_quarterly_reports · basic_declarations · verification_runs · dda_entries ·
documents · incidents) NO incluida en este cleanup · scope separado workstream
MB-7.0 si Marcos prioriza (50+ items adicionales · models necesitan ADD
__table_args__ declarations matching BD).

Reversible · downgrade restaura nombre original.
"""
from typing import Sequence, Union

from alembic import op


revision: str = '5eaaaaee3714'
down_revision: Union[str, None] = '9d1b4035222b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename committee_meetings client_review index to match
    # client_review_a_table_args("committee_meetings") helper output.
    op.execute(
        "ALTER INDEX IF EXISTS idx_committee_meetings_client_review "
        "RENAME TO idx_committee_meetings_client_review_status"
    )


def downgrade() -> None:
    op.execute(
        "ALTER INDEX IF EXISTS idx_committee_meetings_client_review_status "
        "RENAME TO idx_committee_meetings_client_review"
    )
