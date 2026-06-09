"""san_c_ens_iso27001_mapping

Revision ID: sancensiso01
Revises: sancauditsch1
Create Date: 2026-05-05 17:00:00.000000

Crea tabla ``ens_iso27001_mapping`` (CCN-STIC 825) · SAN-C.MB-10.7.

Mapping canónico ENS medida ↔ ISO 27001:2022 Anexo A control · permite
calcular % cobertura ENS automática para clientes con ISO 27001 vigente.

Refs: SAN-C.MB-10.7 · CCN-STIC 825
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "sancensiso01"
down_revision: Union[str, None] = "sancauditsch1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ens_iso27001_mapping",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("ens_measure_code", sa.String(length=20), nullable=False),
        sa.Column(
            "iso27001_control",
            sa.String(length=20),
            nullable=False,
            comment="ISO 27001:2022 Anexo A · A.5.1, A.6.2, etc.",
        ),
        sa.Column(
            "mapping_type",
            sa.String(length=20),
            nullable=False,
            comment="exact/partial/conceptual",
        ),
        sa.Column(
            "coverage_percent",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "metadata_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ens_measure_code",
            "iso27001_control",
            name="uq_ens_iso_mapping_pair",
        ),
    )
    op.create_index(
        "ix_ens_iso_mapping_ens_code",
        "ens_iso27001_mapping",
        ["ens_measure_code"],
    )
    op.create_index(
        "ix_ens_iso_mapping_iso_code",
        "ens_iso27001_mapping",
        ["iso27001_control"],
    )

    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ens_iso27001_mapping TO fulkro_app"
    )

    # Read-only para todos los tenants · es catálogo canónico cross-tenant
    # (no se aplica RLS · cada cliente ve el mismo mapping)


def downgrade() -> None:
    op.drop_index("ix_ens_iso_mapping_iso_code", table_name="ens_iso27001_mapping")
    op.drop_index("ix_ens_iso_mapping_ens_code", table_name="ens_iso27001_mapping")
    op.drop_table("ens_iso27001_mapping")
