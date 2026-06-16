"""drop dead-code: controls table + evidence.control_id FK + wbs_tasks.effort_platform

Campaña fix auditoría 2026-06-17 (D1 + D10b).

D1 · La tabla ``controls`` (modelo ORM ``Control``) era dead-code: 0 lectores en
app+tests, ningún motor inserta filas, y el único FK dependiente
(``evidence.control_id -> controls.id``) se persistía SIEMPRE como NULL
(ingestion_service.py). Se elimina la columna/FK ``evidence.control_id`` (suelta
el FK) y luego la tabla ``controls`` (sus policies RLS + índices caen con ella).

NOTA: ``evidence_requests.control_id`` (UUID, SIN FK a controls) NO se toca —
es un enlace lógico usado por request_service/request_api, no referencia
``controls``.

D10b · ``wbs_tasks.effort_platform`` (String(50)) era columna legacy superseded
por ``effort_platform_hours`` (Float); 0 lectores post-migración m17.

Revision ID: drop_deadcode_controls_effort_001
Revises: whatsapp_otp_hash_attempts_001
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "drop_deadcode_controls_effort_001"
down_revision = "whatsapp_otp_hash_attempts_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # D1 · evidence.control_id (siempre NULL) → drop columna; arrastra el FK a controls.
    op.drop_column("evidence", "control_id")
    # D1 · tabla controls dead-code → drop (policies RLS + índices caen con la tabla).
    op.drop_table("controls")
    # D10b · wbs_tasks.effort_platform legacy → drop (superseded por effort_platform_hours).
    op.drop_column("wbs_tasks", "effort_platform")


def downgrade() -> None:
    op.add_column(
        "wbs_tasks",
        sa.Column("effort_platform", sa.String(length=50), nullable=True),
    )
    op.create_table(
        "controls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dda_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("tipo", sa.String(length=50), nullable=True),
        sa.Column("estado", sa.String(length=50), nullable=True),
        sa.Column("responsable", sa.String(length=255), nullable=True),
        sa.Column("fecha_objetivo", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["dda_entry_id"], ["dda_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "evidence",
        sa.Column("control_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "evidence_control_id_fkey",
        "evidence",
        "controls",
        ["control_id"],
        ["id"],
    )
