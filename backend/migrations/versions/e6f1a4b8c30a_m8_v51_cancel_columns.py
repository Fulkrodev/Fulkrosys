"""M8 v5.1 — Anadir columnas de cancelacion a verification_runs.

Para soportar el kill switch real (Checkpoint 2.12 spec v5.1):
- cancel_requested_at: cuando el usuario pulsa kill
- cancel_requested_by: quien lo pulso (marcos / cliente / scheduler)
- cancel_completed_at: cuando todos los subprocess hijos terminaron

El watcher cancellable de subprocess vigila ``cancel_requested_at`` y
manda SIGTERM a los process groups en ejecucion. Tras <5s envia
SIGKILL si siguen vivos. ``cancel_completed_at`` se rellena al
finalizar la limpieza.

Revision ID: e6f1a4b8c30a
Revises: d5f9e3a6b209
Create Date: 2026-04-21 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f1a4b8c30a"
down_revision: Union[str, None] = "d5f9e3a6b209"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "verification_runs",
        sa.Column(
            "cancel_requested_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
    )
    op.add_column(
        "verification_runs",
        sa.Column("cancel_requested_by", sa.Text(), nullable=True),
    )
    op.add_column(
        "verification_runs",
        sa.Column(
            "cancel_completed_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
    )
    # Indice util para el watcher: query frecuente en cada tick.
    op.create_index(
        "ix_vr_cancel_pending", "verification_runs",
        ["cancel_requested_at"],
        postgresql_where=sa.text("cancel_requested_at IS NOT NULL AND cancel_completed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_vr_cancel_pending", table_name="verification_runs")
    op.drop_column("verification_runs", "cancel_completed_at")
    op.drop_column("verification_runs", "cancel_requested_by")
    op.drop_column("verification_runs", "cancel_requested_at")
