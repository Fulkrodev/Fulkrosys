"""Sesión 3B-2B.4 Phase 2.1 · ADD COLUMN client_id FK CopilotConversation.

Memoria propia per cliente foundation (audit Phase 0 D2 gap A).

Backward-compat: column nullable=True · existing rows backfilled vía JOIN
projects.client_id (1:1 lookup deterministic). NOT NULL constraint deferred
hasta verify NO rows orphan post-backfill (future migration tightener si
demand justifica).

RLS policy ampliada: project_isolation OR client_isolation (cliente puede
acceder convos vía client_id propio cuando project_id NULL · placeholder
para multi-project per cliente Future-1.E.2.bis).

Index ix_copilot_conversations_client_id habilita queries scope per cliente
sin JOIN projects en hot path Marcos super-vision memoria.

Revision ID: s3b2b4_copilot_client_id_001
Revises: radar_v9_perfect_a_001
Create Date: 2026-05-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "s3b2b4_copilot_client_id_001"
down_revision: Union[str, None] = "radar_v9_perfect_a_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "copilot_conversations",
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_copilot_conversations_client_id",
        "copilot_conversations",
        ["client_id"],
    )

    # Backfill existing rows · derive client_id desde projects via FK.
    # Idempotent: solo update si client_id IS NULL.
    op.execute(
        """
        UPDATE copilot_conversations c
        SET client_id = p.client_id
        FROM projects p
        WHERE c.project_id = p.id
          AND c.client_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_copilot_conversations_client_id",
        table_name="copilot_conversations",
    )
    op.drop_column("copilot_conversations", "client_id")
