"""san_e_mb6_atom1_policies_client_signoff

Revision ID: bc70b4b0d8d0
Revises: 03fe02eea2ef
Create Date: 2026-05-11

SAN-E v3.MB-6 atom 1 · Policies CCN-STIC 805 cliente review + bulk signoff.

ADR-020 v6 · Opción Q3.A: extender ``documents`` tabla con cliente review fields
(NO crear policy_signoffs paralela). Pattern atom 5.X.A consolidado 6ª aplicación.

5 cols nuevas documents (Pattern A híbrido · review individual + firma bulk):
  - client_review_status (String 30 · CHECK enum 4 valores) · review decisional cliente
  - client_review_note (Text) · justificación con_pregunta/suggest_change
  - client_reviewed_at (TIMESTAMP tz) · last review timestamp
  - client_reviewed_by_user_id (UUID) · cliente user que revisó
  - client_signing_intent_id (UUID) · link a signing_intents post-firma bulk

CHECK constraint + index parcial alineado pattern atoms 5.3.A / 5.4.A:
  - ck_documents_client_review_status (enum 4 valores)
  - idx_documents_client_review_status (project_id, client_review_status) WHERE NOT NULL

Documents niveles 3-4 procedures + IT mantendrán client_review_status NULL forever
(filter WHERE template_codigo IN niveles 1+2 en queries cliente).

Reversible · downgrade drops cols + index + constraint.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'bc70b4b0d8d0'
down_revision: Union[str, None] = '03fe02eea2ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'documents',
        sa.Column('client_review_status', sa.String(30), nullable=True),
    )
    op.add_column(
        'documents',
        sa.Column('client_review_note', sa.Text(), nullable=True),
    )
    op.add_column(
        'documents',
        sa.Column(
            'client_reviewed_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        'documents',
        sa.Column(
            'client_reviewed_by_user_id',
            UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        'documents',
        sa.Column(
            'client_signing_intent_id',
            UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        'ck_documents_client_review_status',
        'documents',
        "client_review_status IS NULL OR client_review_status IN "
        "('pendiente_revision', 'revisada_ok', 'con_pregunta', 'suggest_change')",
    )

    op.create_index(
        'idx_documents_client_review_status',
        'documents',
        ['project_id', 'client_review_status'],
        unique=False,
        postgresql_where=sa.text('client_review_status IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('idx_documents_client_review_status', table_name='documents')
    op.drop_constraint(
        'ck_documents_client_review_status', 'documents', type_='check',
    )
    op.drop_column('documents', 'client_signing_intent_id')
    op.drop_column('documents', 'client_reviewed_by_user_id')
    op.drop_column('documents', 'client_reviewed_at')
    op.drop_column('documents', 'client_review_note')
    op.drop_column('documents', 'client_review_status')
