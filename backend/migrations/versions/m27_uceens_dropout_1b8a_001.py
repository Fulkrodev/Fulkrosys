"""m27_uceens_dropout_1b8a_001 · sub-lote 1.B.8.A (AMEND-016 v2).

Scope-out de overlays AAPP-only (uceens_*) del CHECK constraint y de los datos
existentes en pce_overlays. Aplica decision AMEND-016 v2 cierre OPCION C scope
target empresa privada licitando AAPP (LECCION-OPS-032 · diferimiento debe
pasar test aplicabilidad target).

Cambios:
  - DELETE rows pce_overlays WHERE overlay_type LIKE 'uceens_%' (1 row dev)
  - DROP CONSTRAINT ck_pce_overlays_type (6 valores enum original)
  - ADD CONSTRAINT ck_pce_overlays_type (3 valores cloud_*)

Mantenidos overlay types: cloud_aws_eu + cloud_azure_es + cloud_gcp_eu
Eliminados:               uceens_ayuntamiento + uceens_diputacion + uceens_universidad

Catalogs YAML asociados eliminados separadamente en mismo sub-atom 1.B.8.A
(refactor commit aparte): pce_uceens_{ayuntamiento,diputacion,universidad}.yaml.

Loader backend/app/motors/m27_conformity/catalogs/__init__.py · OVERLAY_TYPES
tuple reducida de 6 a 3 (mismo commit refactor).

Revision ID: m27_uceens_dropout_1b8a_001
Revises: providers_extensions_1b71_001
Create Date: 2026-05-18
"""
from typing import Sequence, Union

from alembic import op


revision: str = "m27_uceens_dropout_1b8a_001"
down_revision: Union[str, None] = "providers_extensions_1b71_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Scope-out uceens_* overlays + alter CHECK constraint."""
    # 1. DELETE rows que ya no son validas con la nueva constraint
    op.execute(
        "DELETE FROM pce_overlays WHERE overlay_type LIKE 'uceens_%';"
    )

    # 2. DROP old constraint (6 valores)
    op.execute(
        "ALTER TABLE pce_overlays DROP CONSTRAINT IF EXISTS ck_pce_overlays_type;"
    )

    # 3. ADD new constraint (solo 3 cloud_*)
    op.execute(
        """
        ALTER TABLE pce_overlays ADD CONSTRAINT ck_pce_overlays_type
            CHECK (overlay_type IN ('cloud_aws_eu', 'cloud_azure_es', 'cloud_gcp_eu'));
        """
    )


def downgrade() -> None:
    """Restaura los 6 valores enum (sin restaurar data · re-seed manual)."""
    op.execute(
        "ALTER TABLE pce_overlays DROP CONSTRAINT IF EXISTS ck_pce_overlays_type;"
    )
    op.execute(
        """
        ALTER TABLE pce_overlays ADD CONSTRAINT ck_pce_overlays_type
            CHECK (overlay_type IN (
                'cloud_aws_eu',
                'cloud_azure_es',
                'cloud_gcp_eu',
                'uceens_ayuntamiento',
                'uceens_diputacion',
                'uceens_universidad'
            ));
        """
    )
