"""Sesión 3B-2B.4 Phase 2.3 (OPTION 1) · expand copilot RLS para client_isolation.

Audit Phase 1.5 finding A: policy `project_isolation` quedaba over-restrictive
para NEW endpoint cross-project per cliente (Phase 2.2):
  /clients/{client_id}/copilot/conversations

Existing policy:
  USING (project_id = current_project_id() OR project_id IS NULL)

Problem: cuando endpoint sets `current_client_id` ONLY (project_id=NULL),
la policy filter `project_id = current_project_id()` falla (NULL ≠ NULL)
y `project_id IS NULL` solo deja pasar rows huérfanas · convos con
project_id set quedan invisibles.

Fix: ADD client_isolation OR clause · policy ahora permite:
- project_id = current_project_id() (existing project-scoped flows)
- project_id IS NULL (orphan rows · backward compat)
- client_id = current_client_id() (NEW · cross-project per cliente memoria)

copilot_messages mirror policy via subquery a copilot_conversations.

Defence-in-depth: endpoint también filtra WHERE client_id = :client_id
explicit (NO solo RLS · belt + suspenders).

Revision ID: copilot_rls_client_isolation_001
Revises: s3b2b4_copilot_client_id_001
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op


revision: str = "copilot_rls_client_isolation_001"
down_revision: Union[str, None] = "s3b2b4_copilot_client_id_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop existing project-only policies
    op.execute("DROP POLICY IF EXISTS project_isolation ON copilot_conversations")
    op.execute("DROP POLICY IF EXISTS project_isolation ON copilot_messages")

    # NEW · copilot_conversations · 3-way isolation (project OR null OR client)
    op.execute(
        """
        CREATE POLICY copilot_isolation ON copilot_conversations
          USING (
            project_id = current_project_id()
            OR project_id IS NULL
            OR client_id = current_client_id()
          )
        """
    )

    # NEW · copilot_messages · mirrors via subquery a parent conversation
    # (audit Phase 1.5 finding A · child rows must respect parent scope).
    op.execute(
        """
        CREATE POLICY copilot_messages_isolation ON copilot_messages
          USING (
            project_id = current_project_id()
            OR project_id IS NULL
            OR conversation_id IN (
              SELECT id FROM copilot_conversations
              WHERE client_id = current_client_id()
            )
          )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS copilot_isolation ON copilot_conversations")
    op.execute("DROP POLICY IF EXISTS copilot_messages_isolation ON copilot_messages")

    # Restore original project_isolation policy
    op.execute(
        """
        CREATE POLICY project_isolation ON copilot_conversations
          USING (project_id = current_project_id() OR project_id IS NULL)
        """
    )
    op.execute(
        """
        CREATE POLICY project_isolation ON copilot_messages
          USING (project_id = current_project_id() OR project_id IS NULL)
        """
    )
