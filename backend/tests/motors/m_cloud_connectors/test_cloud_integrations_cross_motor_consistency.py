"""Tests cross-motor consistency · sub-fase 1.D.J.C cierre v3.12.

Cierre 1.D.J K-full motores cloud integration · verifica coherence cross-helpers:
- All 5 helpers coexisten sin conflict (M22+M02+M27+M01+M19)
- All 5 endpoints respond consistently · project-scoped · idempotent
- K-light additive ENFORCED empíricamente via grep on motor paths:
  · 0 imports CloudResource/CloudGap en backend/app/motors/m{01,02,19,22,27}*/
  · Pattern OPS-026 DRY + ADR-014 read-only + ADR-025 reuse enforced

Si grep encuentra match en motor path → test FAIL (architectural drift).
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest

from backend.app.motors.m_cloud_connectors.integrations import (
    consolidate_discovery_with_cloud,
    enrich_asset_inventory_with_cloud,
    get_categorization_cloud_hint,
    get_conformity_cloud_score,
    get_risk_cloud_indicators,
)
from backend.tests.conftest import setup_test_project


# ============================================================
# Test 1 · All 5 helpers coexist · callable · expected types
# ============================================================


@pytest.mark.asyncio
async def test_all_5_helpers_callable_with_expected_return_types(db):
    """5 helpers integration coexisten sin conflict · expected return types."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    # M22 · DiscoveryConsolidatedView
    discovery = await consolidate_discovery_with_cloud(db, project_id=pid)
    assert hasattr(discovery, "assets")
    assert hasattr(discovery, "counts")
    assert isinstance(discovery.assets, list)
    assert "total" in discovery.counts

    # M02 · EnrichedMageritInventory
    magerit = await enrich_asset_inventory_with_cloud(db, project_id=pid)
    assert hasattr(magerit, "assets")
    assert hasattr(magerit, "counts")
    assert "cloud_verified" in magerit.counts
    assert "manual_only" in magerit.counts

    # M27 · ConformityCloudScore
    conformity = await get_conformity_cloud_score(db, project_id=pid)
    assert hasattr(conformity, "score_percentage")
    assert hasattr(conformity, "per_familia_breakdown")
    assert isinstance(conformity.score_percentage, float)
    assert isinstance(conformity.per_familia_breakdown, list)

    # M01 scaffold · returns None
    hint = await get_categorization_cloud_hint(db, project_id=pid)
    assert hint is None

    # M19 scaffold · returns empty dict
    indicators = await get_risk_cloud_indicators(db, project_id=pid)
    assert indicators == {}


# ============================================================
# Test 2 · 5 helpers idempotent · same project 2 calls = same result
# ============================================================


@pytest.mark.asyncio
async def test_all_5_helpers_idempotent_for_same_project(db):
    """Idempotent · 2 calls back-to-back same project → consistent results."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    # M22 idempotent
    d1 = await consolidate_discovery_with_cloud(db, project_id=pid)
    d2 = await consolidate_discovery_with_cloud(db, project_id=pid)
    assert d1.counts == d2.counts

    # M02 idempotent
    m1 = await enrich_asset_inventory_with_cloud(db, project_id=pid)
    m2 = await enrich_asset_inventory_with_cloud(db, project_id=pid)
    assert m1.counts == m2.counts

    # M27 idempotent
    c1 = await get_conformity_cloud_score(db, project_id=pid)
    c2 = await get_conformity_cloud_score(db, project_id=pid)
    assert c1.score_percentage == c2.score_percentage
    assert c1.measures_total_aplicable == c2.measures_total_aplicable

    # M01 + M19 scaffolds idempotent (trivially)
    assert await get_categorization_cloud_hint(db, project_id=pid) is None
    assert await get_categorization_cloud_hint(db, project_id=pid) is None
    assert await get_risk_cloud_indicators(db, project_id=pid) == {}
    assert await get_risk_cloud_indicators(db, project_id=pid) == {}


# ============================================================
# Test 3 · K-light additive ENFORCED empíricamente · grep motor paths
# ============================================================


# Motor paths que NO deben importar CloudResource/CloudGap directamente.
# Las integraciones consume via m_cloud_connectors.integrations API · NUNCA
# import direct desde motor source code · garantiza ADR-014 + ADR-025.
_TARGET_MOTOR_PATHS = (
    "backend/app/motors/m01_categorization",
    "backend/app/motors/m02_magerit",
    "backend/app/motors/m19_risk",
    "backend/app/motors/m22_discovery",
    "backend/app/motors/m27_conformity",
)

# Patterns que indicarían direct cloud import en motor source (architectural drift).
_FORBIDDEN_PATTERNS = (
    re.compile(r"from backend\.app\.motors\.m_cloud_connectors"),
    re.compile(r"import.*m_cloud_connectors"),
    re.compile(r"CloudResource\("),
    re.compile(r"CloudGap\("),
    re.compile(r"CloudConnector\(\)"),
)


def _find_motor_violations(project_root: Path) -> list[tuple[str, str, int, str]]:
    """Walks motor paths · returns violations (motor_path, file_path, line_no, snippet)."""
    violations: list[tuple[str, str, int, str]] = []
    for motor_rel in _TARGET_MOTOR_PATHS:
        motor_dir = project_root / motor_rel
        if not motor_dir.exists():
            continue
        for py_file in motor_dir.rglob("*.py"):
            try:
                lines = py_file.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for line_no, line in enumerate(lines, start=1):
                for pattern in _FORBIDDEN_PATTERNS:
                    if pattern.search(line):
                        violations.append(
                            (motor_rel, str(py_file), line_no, line.strip()),
                        )
    return violations


def test_k_light_additive_enforced_grep_motor_paths():
    """K-light additive sostener · 0 direct cloud imports en motor paths.

    Si test FAIL → architectural drift · motor source-code modified · violation
    ADR-025 + OPS-045. Action: refactor consume via integrations.py helper.
    """
    # Find project root · current file en backend/tests/motors/m_cloud_connectors/
    # → parents[4] = repo root
    project_root = Path(__file__).resolve().parents[4]

    violations = _find_motor_violations(project_root)

    assert violations == [], (
        f"K-light additive drift detected · {len(violations)} violations:\n"
        + "\n".join(
            f"  {motor} · {file}:{line_no} → {snippet[:100]}"
            for motor, file, line_no, snippet in violations[:10]
        )
    )
