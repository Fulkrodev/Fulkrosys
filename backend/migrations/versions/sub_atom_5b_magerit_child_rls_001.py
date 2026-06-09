"""sub_atom_5b_magerit_child_rls_001 · Sub-atom 5.B Ejecutable 2

Habilita Row Level Security en 6 child tables magerit con FK indirecto
analysis_id → magerit_analysis.project_id. Pattern EXISTS 1-level via
parent magerit_analysis (que ya tiene RLS project_isolation simple
desde 33cef115cdf5 SAN-B.MB-2.1).

Cobertura RLS empirical post Sub-atom 5.B: parent magerit_analysis +
6 child tables = 7 tablas magerit todas RLS isolated.

Correcciones briefing SUPER MEGA PROMPT (Ejecutable 2 doc baseline):
- 6 child tables (briefing claim 11 INCORRECTO empirical)
- EXISTS subquery 1-level via analysis_id (NO 3-way OR Sub-atom 5.A ·
  magerit NO tiene client_id propagation directo · solo analysis_id FK)
- Pattern current_project_id() helper (NO current_setting tenant_id cast)

Tables cubiertas:
- magerit_assets (FK analysis_id)
- magerit_asset_dependencies (FK analysis_id + 2× magerit_assets.id)
- magerit_threat_assessment (FK analysis_id + asset_id)
- magerit_safeguard_deployment (FK analysis_id)
- magerit_risk_calculation (FK analysis_id + asset_id)
- magerit_treatment_plan (FK analysis_id + asset_id)

Multi-parent merge: down_revision tuple consolida 3 alembic heads
existing en single revision (cluster6_client_mfa_001 + radar_v9_perfect_f_001
+ remediation_enhancement_b35_e_001 · detectados empirical via
alembic heads WSL2 native).

Catalog tables EXCLUDED (no tenant · precargados YAML/seed):
- magerit_asset_types, magerit_threats, magerit_safeguards,
  magerit_ens_mapping, magerit_risk_matrix

Refs: SUPER_MEGA_PROMPT_AUDIT_BASELINE_2026-05-27.md Ejecutable 2
"""
from typing import Sequence, Union

from alembic import op


revision: str = "sub_atom_5b_magerit_child_rls_001"
# Multi-parent merge · consolida 3 heads existing en single revision
down_revision: Union[str, Sequence[str], None] = (
    "cluster6_client_mfa_001",
    "radar_v9_perfect_f_001",
    "remediation_enhancement_b35_e_001",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 6 child tables magerit con FK analysis_id indirecto
# (replica precedent 33cef115cdf5 lines 91-149 EXISTS pattern 1-level)
MAGERIT_CHILD_TABLES: tuple[str, ...] = (
    "magerit_assets",
    "magerit_asset_dependencies",
    "magerit_threat_assessment",
    "magerit_safeguard_deployment",
    "magerit_risk_calculation",
    "magerit_treatment_plan",
)


def upgrade() -> None:
    """Enable RLS + project_isolation policy via EXISTS 1-level subquery
    contra magerit_analysis.project_id = current_project_id()."""
    for table in MAGERIT_CHILD_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} USING ("
            "EXISTS (SELECT 1 FROM magerit_analysis ma "
            f"WHERE ma.id = {table}.analysis_id "
            "AND ma.project_id = current_project_id()))"
        )


def downgrade() -> None:
    """Reverso completo · tablas vuelven a estado pre-Sub-atom 5.B."""
    for table in MAGERIT_CHILD_TABLES:
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
