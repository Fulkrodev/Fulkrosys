"""mb11_workflow_phase_10_canonical

SAN-C MB-11.1 · Workflow lifecycle 8 fases → 10 fases canonical.

Añade 2 sub-fases del Manual ENS plan v4.2:
- ``analisis_riesgos`` entre ``diagnostico`` y ``adecuacion``
- ``dda_final`` entre ``implantacion`` y ``verificacion``

Operación non-breaking: extiende CHECK constraint para admitir 10
valores. Projects existentes (todos con valores 8-fase originales)
siguen válidos. NO rewrites data, NO ALTER columna.

Pasos:
1. DROP existing CHECK constraint ``projects_fase_check`` (8 valores)
2. CREATE new CHECK constraint con 10 valores

Revision ID: mb11_wphase_10
Revises: sancensiso01
Create Date: 2026-05-05 (SAN-C MB-11.1)
"""
from typing import Sequence, Union

from alembic import op


revision: str = "mb11_wphase_10"
down_revision: Union[str, None] = "sancensiso01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PHASES_10 = (
    "pre_venta",
    "onboarding",
    "diagnostico",
    "analisis_riesgos",
    "adecuacion",
    "implantacion",
    "dda_final",
    "verificacion",
    "conformidad",
    "retainer_cierre",
)

_PHASES_8 = (
    "pre_venta",
    "onboarding",
    "diagnostico",
    "adecuacion",
    "implantacion",
    "verificacion",
    "conformidad",
    "retainer_cierre",
)


def _check_in(phases: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{p}'" for p in phases)
    return f"fase IN ({quoted})"


def upgrade() -> None:
    op.drop_constraint("projects_fase_check", "projects", type_="check")
    op.create_check_constraint(
        "projects_fase_check",
        "projects",
        _check_in(_PHASES_10),
    )


def downgrade() -> None:
    # Reverse: vuelve a CHECK 8 valores. Pre-condition: ningún project
    # con fase ∈ {analisis_riesgos, dda_final} (o downgrade falla).
    op.drop_constraint("projects_fase_check", "projects", type_="check")
    op.create_check_constraint(
        "projects_fase_check",
        "projects",
        _check_in(_PHASES_8),
    )
