"""M16 Sesion 6: lms_assignments table for mini-LMS workflow.

Una sola tabla por proyecto que registra asignaciones de cursos LMS
a empleados/asistentes con tracking de finalizacion + score quiz +
rutas a evidencias E-502 (asistencia) y E-503 (cuestionario).

Revision ID: b9d3e6f7a207
Revises: a8c2d4f5e106
Create Date: 2026-04-21 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b9d3e6f7a207"
down_revision: Union[str, None] = "a8c2d4f5e106"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lms_assignments",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id"), nullable=True, index=True,
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False, index=True,
        ),
        sa.Column("course_codigo", sa.String(length=20), nullable=False),
        sa.Column("course_titulo", sa.String(length=300), nullable=False),
        sa.Column("course_duracion_minutos", sa.Integer(), nullable=False),
        sa.Column("asistente_nombre", sa.String(length=200), nullable=False),
        sa.Column("asistente_email", sa.String(length=255), nullable=False),
        sa.Column("asistente_cargo", sa.String(length=200), nullable=True),
        sa.Column("asistente_organizacion", sa.String(length=200), nullable=True),
        sa.Column(
            "estado", sa.String(length=20), nullable=False,
            server_default="assigned",
        ),
        sa.Column("asignado_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("iniciado_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completado_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("due_date", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("quiz_score", sa.Float(), nullable=True),
        sa.Column("quiz_pass", sa.Boolean(), nullable=True),
        sa.Column("quiz_respuestas", postgresql.JSONB(), nullable=True),
        sa.Column("quiz_correcciones", postgresql.JSONB(), nullable=True),
        sa.Column("e502_path", sa.String(length=500), nullable=True),
        sa.Column("e502_hash", sa.String(length=64), nullable=True),
        sa.Column("e503_path", sa.String(length=500), nullable=True),
        sa.Column("e503_hash", sa.String(length=64), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        # FullMixin columns
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_lms_project_asistente_course",
        "lms_assignments",
        ["project_id", "asistente_email", "course_codigo"],
    )
    op.create_index(
        "ix_lms_project_estado",
        "lms_assignments",
        ["project_id", "estado"],
    )


def downgrade() -> None:
    op.drop_index("ix_lms_project_estado", table_name="lms_assignments")
    op.drop_constraint(
        "uq_lms_project_asistente_course",
        "lms_assignments", type_="unique",
    )
    op.drop_table("lms_assignments")
