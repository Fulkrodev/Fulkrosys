"""san_e_mb5_6_basic_declarations_client_review

Revision ID: 24cbdeb40cfc
Revises: fc8ad935f6f6
Create Date: 2026-05-11 01:54:11.705300

ADR-020 v6 SAN-E v3.MB-5.6 (Escenario X audit-driven confirmed):
- Reutiliza BasicDeclarationRow existing · NO crear tabla paralela
- declaration_type flexible cubre BASICA (initial) y MEDIA/ALTA (commitment_pre_certification)
- Service tier-aware determina declaration_type por project.categoria_objetivo
- Pattern atoms 5.3.A / 5.4.A / 5.5.A sostenido (extender tabla existing)

5 cols NEW basic_declarations:
- client_reviewed_at + client_reviewed_by_user_id + client_concerns_note (cliente review)
- client_signing_intent_id (link signing_intents)
- readiness_snapshot_jsonb (audit trail · state DdA+MAGERIT+Pentest+evidencias)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = '24cbdeb40cfc'
down_revision: Union[str, None] = 'fc8ad935f6f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cliente review state (4 cols · pattern atoms 5.3.A / 5.4.A / 5.5.A)
    op.add_column("basic_declarations", sa.Column("client_reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("basic_declarations", sa.Column("client_reviewed_by_user_id", UUID(as_uuid=True), nullable=True))
    op.add_column("basic_declarations", sa.Column("client_concerns_note", sa.Text(), nullable=True))
    op.add_column("basic_declarations", sa.Column("client_signing_intent_id", UUID(as_uuid=True), nullable=True))

    # Readiness snapshot · audit trail compliance ENAC
    op.add_column("basic_declarations", sa.Column("readiness_snapshot_jsonb", JSONB, nullable=True))

    # Index parcial · perf cliente review queries
    op.create_index(
        "idx_basic_declarations_client_reviewed",
        "basic_declarations",
        ["project_id", "client_reviewed_at"],
        postgresql_where=sa.text("client_reviewed_at IS NOT NULL"),
    )

    # CHECK constraint update · permitir commitment_pre_certification para MEDIA/ALTA
    # Escenario X audit-driven (5.6.A.bis): declaration_type cubre 3 tiers
    # ALSO widen declaration_type column · 'commitment_pre_certification' es 29 chars (>20 default)
    op.alter_column(
        "basic_declarations",
        "declaration_type",
        type_=sa.String(40),
        existing_type=sa.String(20),
        existing_nullable=False,
    )
    op.execute(
        "ALTER TABLE basic_declarations DROP CONSTRAINT IF EXISTS ck_basic_declarations_type"
    )
    op.execute(
        "ALTER TABLE basic_declarations ADD CONSTRAINT ck_basic_declarations_type "
        "CHECK (declaration_type IN ('initial', 'renewal', 'commitment_pre_certification'))"
    )

    # GRANT runtime user
    op.execute("GRANT SELECT, UPDATE ON basic_declarations TO fulkro_app;")


def downgrade() -> None:
    # Restore original CHECK constraint (initial + renewal only)
    op.execute(
        "ALTER TABLE basic_declarations DROP CONSTRAINT IF EXISTS ck_basic_declarations_type"
    )
    op.execute(
        "ALTER TABLE basic_declarations ADD CONSTRAINT ck_basic_declarations_type "
        "CHECK (declaration_type IN ('initial', 'renewal'))"
    )
    # Restore original column type String(20)
    op.alter_column(
        "basic_declarations",
        "declaration_type",
        type_=sa.String(20),
        existing_type=sa.String(40),
        existing_nullable=False,
    )

    op.drop_index("idx_basic_declarations_client_reviewed", table_name="basic_declarations")
    op.drop_column("basic_declarations", "readiness_snapshot_jsonb")
    op.drop_column("basic_declarations", "client_signing_intent_id")
    op.drop_column("basic_declarations", "client_concerns_note")
    op.drop_column("basic_declarations", "client_reviewed_by_user_id")
    op.drop_column("basic_declarations", "client_reviewed_at")
