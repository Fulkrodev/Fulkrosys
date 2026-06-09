"""san_e_atom01_dda_entries_rename_client_note

Revision ID: 03fe02eea2ef
Revises: 24cbdeb40cfc
Create Date: 2026-05-11

SAN-E v3 atom 0.1 · ClientReviewMixin pattern uniforme Pattern A.

Rename ``dda_entries.client_note`` → ``client_review_note`` to align with
MageritAsset + MageritThreatAssessment naming (atoms 5.4.A / 5.4b.A).

Pre-flight verified (audit empirico 2026-05-11):
- 73 dda_entries rows · 0 con client_note non-null (zero data loss risk)
- No FK · no index · no constraint references column client_note
- CHECK ck_dda_entries_client_review_status target distinct col (status)
- Index idx_dda_entries_client_review_status target distinct col (status)

Reversible · downgrade renames back identico.
"""
from typing import Sequence, Union

from alembic import op


revision: str = '03fe02eea2ef'
down_revision: Union[str, None] = '24cbdeb40cfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'dda_entries',
        'client_note',
        new_column_name='client_review_note',
    )


def downgrade() -> None:
    op.alter_column(
        'dda_entries',
        'client_review_note',
        new_column_name='client_note',
    )
