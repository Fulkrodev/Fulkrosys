"""change_request code unique index · red de seguridad race CR-NNN (P1-8)

Additive. Índice ÚNICO sobre ``change_requests (project_id, code)`` para que un
código CR-NNN duplicado (carrera entre los 2 generadores m17/m19) falle ruidoso
(IntegrityError) en vez de duplicar en silencio. Complementa el
``pg_advisory_xact_lock`` por project_id de ``core/sequences.next_change_request_code``.

Revision ID: change_request_code_unique_001
Revises: invoice_correlative_unique_001
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op


revision: str = "change_request_code_unique_001"
down_revision: Union[str, None] = "invoice_correlative_unique_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_change_requests_project_code
        ON change_requests (project_id, code)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_change_requests_project_code")
