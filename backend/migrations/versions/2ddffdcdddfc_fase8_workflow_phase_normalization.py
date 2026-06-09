"""fase8_workflow_phase_normalization

FASE 8 · Sub-bloque 8.A.0.MIG · Normalización projects.fase pre derive_state.

Audit empírico pre-impl (LECCIÓN-OPS-003 · ADR-026):
- 13 projects total · 3 valores reales mayúsculas (IMPLANTACION/VERIFICACION/DIAGNOSTICO) · 10 NULLs
- Plan v4.2 declara 8 fases lifecycle lowercase (pre_venta/onboarding/diagnostico/adecuacion/implantacion/verificacion/conformidad/retainer_cierre)
- ADR-026 supersedes ADR-007 nomenclatura

Pasos ordering crítico (1→2→3→4):
1. Normalize lowercase existing values (preserva semántica)
2. Backfill NULLs → 'pre_venta' (10 rows)
3. ALTER NOT NULL + server_default 'pre_venta' (post-backfill safe)
4. CHECK constraint enum 8 fases

Si CHECK primero o NOT NULL primero → falla por NULLs existing. Pattern correcto:
normalize + backfill ANTES restrict.

Revision ID: 2ddffdcdddfc
Revises: 53dead2ba760
Create Date: 2026-04-30 13:12:42.276983
"""
from typing import Sequence, Union

from alembic import op


revision: str = '2ddffdcdddfc'
down_revision: Union[str, None] = '53dead2ba760'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PASO 1: normalize existing values lowercase (preserve semantics)
    op.execute("""
        UPDATE projects
        SET fase = lower(fase)
        WHERE fase IS NOT NULL
    """)

    # PASO 2: backfill 10 NULLs → 'pre_venta' (semantic correcto inicial)
    op.execute("""
        UPDATE projects
        SET fase = 'pre_venta'
        WHERE fase IS NULL
    """)

    # PASO 3: alter column NOT NULL + server_default (post-backfill safe)
    op.alter_column(
        'projects', 'fase',
        nullable=False,
        server_default='pre_venta',
    )

    # PASO 4: CHECK constraint enum 8 fases lifecycle plan v4.2
    op.create_check_constraint(
        'projects_fase_check',
        'projects',
        "fase IN ('pre_venta', 'onboarding', 'diagnostico', "
        "'adecuacion', 'implantacion', 'verificacion', "
        "'conformidad', 'retainer_cierre')",
    )


def downgrade() -> None:
    # Reverse symmetric (preserve normalize lowercase, data integrity)
    op.drop_constraint('projects_fase_check', 'projects', type_='check')
    op.alter_column(
        'projects', 'fase',
        nullable=True,
        server_default=None,
    )
    # NO reverse normalize (lowercase preservation correct semantically)
