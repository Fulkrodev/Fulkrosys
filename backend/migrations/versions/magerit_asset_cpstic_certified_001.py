"""m02 · magerit_assets.cpstic_certified (S13 campaña fix · desbloquea ALTA)

El gate de transición a CONFORMIDAD para categoría ALTA (feature
``alta_productos_cpstic``) era un stub ``return False`` incondicional porque la
columna ``Asset.cpstic_certified`` nunca se creó → TODO proyecto ALTA quedaba
bloqueado de forma permanente e irresoluble.

Fix: columna real ``cpstic_certified`` (BOOLEAN NOT NULL DEFAULT FALSE) en
``magerit_assets``. El completion-check de m17/workflow_blocking_service consulta
si existe ≥1 activo con cpstic_certified=TRUE para el proyecto (op.pl.5 ALTA ·
producto CPSTIC certificado CCN). Resolvable vía inventario MAGERIT (marcar el
activo) o FeatureFlagOverride N/A si CPSTIC no aplica.

Revision ID: magerit_asset_cpstic_certified_001
Revises: m28_refresh_drift_summary_fn_001
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "magerit_asset_cpstic_certified_001"
down_revision = "m28_refresh_drift_summary_fn_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "magerit_assets",
        sa.Column(
            "cpstic_certified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("magerit_assets", "cpstic_certified")
