"""mb7_0_bis_final_alter_columns

Revision ID: 08bf3e16ef34
Revises: 6068f106de44
Create Date: 2026-05-11

SAN-E v3.atom MB-7.0.bis final · 3 NOT NULL + 3 column comments magic_links.

Resuelve drift remaining cumulative atom MB-7.0.bis:
- chat_threads.messages_count → NOT NULL (default 0)
- client_tasks.expected_evidence_count → NOT NULL (default 1)
- client_tasks.priority → NOT NULL (default 0)
- magic_links.cc_emails comment (ADR-020 EmailSender CC)
- magic_links.custom_subject comment (purpose override)
- magic_links.custom_body_intro comment (prepend text)

Reversible · downgrade restora nullable=True + removes comments.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '08bf3e16ef34'
down_revision: Union[str, None] = '6068f106de44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOT NULL chat_threads.messages_count (default 0)
    op.execute(
        "UPDATE chat_threads SET messages_count = 0 WHERE messages_count IS NULL"
    )
    op.alter_column(
        "chat_threads", "messages_count",
        nullable=False,
        existing_type=sa.Integer(),
        existing_server_default=sa.text("0"),
    )

    # NOT NULL client_tasks.expected_evidence_count + priority
    op.execute(
        "UPDATE client_tasks SET expected_evidence_count = 1 "
        "WHERE expected_evidence_count IS NULL"
    )
    op.alter_column(
        "client_tasks", "expected_evidence_count",
        nullable=False,
        existing_type=sa.Integer(),
        existing_server_default=sa.text("1"),
    )
    op.execute(
        "UPDATE client_tasks SET priority = 0 WHERE priority IS NULL"
    )
    op.alter_column(
        "client_tasks", "priority",
        nullable=False,
        existing_type=sa.Integer(),
        existing_server_default=sa.text("0"),
    )

    # Column comments magic_links (3 cols ADR-020 EmailSender pattern).
    op.execute(
        "COMMENT ON COLUMN magic_links.cc_emails IS "
        "'Carbon copy emails adicionales (TEXT[]). Aplicado por EmailSender "
        "al enviar el link. NULL = sin CC.'"
    )
    op.execute(
        "COMMENT ON COLUMN magic_links.custom_subject IS "
        "'Override del subject default per purpose. NULL = usar subject "
        "definido en _PURPOSE_EMAILS dict.'"
    )
    op.execute(
        "COMMENT ON COLUMN magic_links.custom_body_intro IS "
        "'Texto Marcos antes del cuerpo template (override prepend, no "
        "replace). NULL = sin intro custom.'"
    )


def downgrade() -> None:
    op.execute("COMMENT ON COLUMN magic_links.custom_body_intro IS NULL")
    op.execute("COMMENT ON COLUMN magic_links.custom_subject IS NULL")
    op.execute("COMMENT ON COLUMN magic_links.cc_emails IS NULL")

    op.alter_column(
        "client_tasks", "priority", nullable=True,
        existing_type=sa.Integer(),
        existing_server_default=sa.text("0"),
    )
    op.alter_column(
        "client_tasks", "expected_evidence_count", nullable=True,
        existing_type=sa.Integer(),
        existing_server_default=sa.text("1"),
    )
    op.alter_column(
        "chat_threads", "messages_count", nullable=True,
        existing_type=sa.Integer(),
        existing_server_default=sa.text("0"),
    )
