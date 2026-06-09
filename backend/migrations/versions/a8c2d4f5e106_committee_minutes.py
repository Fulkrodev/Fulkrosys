"""M18 Sesion 6: extend committee_meetings for E-005 acta workflow.

Anade columnas necesarias para la acta firmada por todos los asistentes
via magic link APROBACION_ACTA + Ed25519 + PDF.

Mantiene retrocompat con columnas legacy (fecha, asistentes, orden_dia,
acuerdos, acta_path, firmado_at).

Revision ID: a8c2d4f5e106
Revises: f8c1e2d4a004
Create Date: 2026-04-21 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a8c2d4f5e106"
down_revision: Union[str, None] = "f8c1e2d4a004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_COLUMNS = [
    sa.Column("codigo", sa.String(length=40), nullable=True),
    sa.Column("tipo_comite", sa.String(length=40), nullable=True),
    sa.Column("titulo", sa.String(length=300), nullable=True),
    sa.Column("lugar", sa.String(length=300), nullable=True),
    sa.Column("presidente", sa.String(length=200), nullable=True),
    sa.Column("secretario", sa.String(length=200), nullable=True),
    sa.Column("orden_del_dia", postgresql.JSONB(), nullable=True),
    sa.Column("acuerdos_jsonb", postgresql.JSONB(), nullable=True),
    sa.Column("proximos_pasos", postgresql.JSONB(), nullable=True),
    sa.Column("notas_libres", sa.Text(), nullable=True),
    sa.Column("docx_path", sa.String(length=500), nullable=True),
    sa.Column("pdf_path", sa.String(length=500), nullable=True),
    sa.Column("hash_sha256", sa.String(length=64), nullable=True),
    sa.Column("signature_ed25519", sa.String(length=256), nullable=True),
    sa.Column("firmas", postgresql.JSONB(), nullable=True),
    sa.Column(
        "estado", sa.String(length=30), nullable=True,
        server_default="draft",
    ),
    sa.Column("generado_at", sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column("enviada_at", sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column("fully_signed_at", sa.TIMESTAMP(timezone=True), nullable=True),
]


def upgrade() -> None:
    for col in _NEW_COLUMNS:
        op.add_column("committee_meetings", col)

    # asistentes legacy era JSONB con tipo dict; ampliamos para soportar
    # lista de objetos {nombre, cargo, organizacion, email}. JSONB ya
    # admite ambos sin alteracion de tipo, no se requiere ALTER.

    op.create_unique_constraint(
        "uq_committee_meetings_project_codigo",
        "committee_meetings", ["project_id", "codigo"],
    )
    op.create_index(
        "ix_committee_meetings_project_estado",
        "committee_meetings", ["project_id", "estado"],
    )


def downgrade() -> None:
    op.drop_index("ix_committee_meetings_project_estado", table_name="committee_meetings")
    op.drop_constraint("uq_committee_meetings_project_codigo", "committee_meetings", type_="unique")
    for col in _NEW_COLUMNS:
        op.drop_column("committee_meetings", col.name)
