"""pricing_config · fuente única editable de precios base ENS (P4-1)

Tabla con el precio de proyecto por categoría (BASICA/MEDIA/ALTA), editable por
Marcos desde /admin/settings/pricing. Al arranque y tras cada edición,
``pricing.repository.refresh_pricing_from_db`` la carga en
``rules.apply_pricing_overrides`` → todos los consumidores (calculator, agents)
reflejan el valor vigente. El código tiene el mismo valor como default.

Seed inicial (Marcos 2026-06-09): BASICA 3.200 · MEDIA 10.700 · ALTA 22.800.

Revision ID: pricing_config_001
Revises: document_version_unique_001
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "pricing_config_001"
down_revision: Union[str, None] = "document_version_unique_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pricing_config",
        sa.Column("categoria", sa.String(length=10), primary_key=True),
        sa.Column("precio_proyecto", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
    )
    op.execute(
        "INSERT INTO pricing_config (categoria, precio_proyecto) VALUES "
        "('BASICA', 3200.00), ('MEDIA', 10700.00), ('ALTA', 22800.00)"
    )


def downgrade() -> None:
    op.drop_table("pricing_config")
