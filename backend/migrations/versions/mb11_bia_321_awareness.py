"""mb11_bia_321_awareness

SAN-C MB-11.5 · BIA + awareness tables (3-2-1 backup policy stateless,
sin tabla nueva · evalúa contra payload o backup_jobs metadata).

Tablas creadas:
- ``bia_analyses`` · Business Impact Analysis structured per servicio crítico
- ``awareness_sessions`` · Sesiones formación seguridad cliente
- ``awareness_attendance`` · Registro asistencia sesiones (magic-link)

Revision ID: mb11_bia_aware
Revises: mb11_archetype
Create Date: 2026-05-05 (SAN-C MB-11.5)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "mb11_bia_aware"
down_revision: Union[str, None] = "mb11_archetype"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bia_analyses",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column("service_name", sa.String(200), nullable=False),
        sa.Column("rto_hours", sa.Integer, nullable=False),
        sa.Column("rpo_hours", sa.Integer, nullable=False),
        sa.Column("daily_impact_eur", sa.Numeric(12, 2), nullable=True),
        sa.Column("stakeholders", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("minimum_resources", postgresql.JSONB, nullable=True),
        sa.Column("last_reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_bia_analyses_project_id", "bia_analyses", ["project_id"],
    )

    op.create_table(
        "awareness_sessions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("scheduled_date", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("topics", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("mandatory", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_awareness_sessions_project_id",
        "awareness_sessions",
        ["project_id"],
    )

    op.create_table(
        "awareness_attendance",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "session_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("awareness_sessions.id"), nullable=False,
        ),
        sa.Column("attendee_email", sa.String(200), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("attended_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("magic_link_token", sa.String(100), nullable=True),
    )
    op.create_index(
        "ix_awareness_attendance_session_id",
        "awareness_attendance",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_awareness_attendance_session_id", table_name="awareness_attendance")
    op.drop_table("awareness_attendance")
    op.drop_index("ix_awareness_sessions_project_id", table_name="awareness_sessions")
    op.drop_table("awareness_sessions")
    op.drop_index("ix_bia_analyses_project_id", table_name="bia_analyses")
    op.drop_table("bia_analyses")
