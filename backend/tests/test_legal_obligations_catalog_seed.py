"""Smoke test for legal_obligations_catalog seed loader.

Cross-cutting catalog (RGPD/LOPDGDD/NIS2/DORA/AI_Act) - tests viven en
backend/tests/ root (no carpeta motor especifica).
"""
from __future__ import annotations

import json
from collections import Counter

from backend.scripts.seed.seed_legal_obligations_catalog import (
    EXPECTED_COUNT,
    EXPECTED_DISTRIBUTION,
    load_obligations,
)


def test_load_returns_250_obligations():
    """v2 EXPAND 50→250 (1.C.0.C v3.9 plan EXPAND R32 sostenido)."""
    rows = load_obligations()
    assert len(rows) == EXPECTED_COUNT == 250


def test_codigos_are_unique():
    rows = load_obligations()
    codigos = [r["codigo"] for r in rows]
    assert len(codigos) == len(set(codigos)), "Duplicate codigos in YAML"


def test_distribucion_regulacion_matches():
    """v2 EXPAND distribución target: RGPD 80 · LOPDGDD 30 · NIS2 60 · DORA 50 · AI_Act 30."""
    rows = load_obligations()
    dist = dict(Counter(r["regulacion"] for r in rows))
    assert dist == EXPECTED_DISTRIBUTION, (
        f"Distribution {dist} != expected {EXPECTED_DISTRIBUTION}"
    )


def test_required_fields_present():
    rows = load_obligations()
    for row in rows:
        assert row["codigo"], "codigo missing"
        assert row["regulacion"], f"regulacion missing for {row['codigo']}"
        assert row["titulo"], f"titulo missing for {row['codigo']}"
        assert row["obligacion"], f"obligacion missing for {row['codigo']}"
        # JSON-encoded fields must be parseable
        assert isinstance(json.loads(row["sector_aplica"]), list)
        assert isinstance(json.loads(row["ens_categoria_aplica"]), list)
        assert isinstance(json.loads(row["vinculo_medida_ens"]), list)


def test_cross_mappings_ens_populated_min_threshold():
    """v2 EXPAND: ≥60% entries (~150) deben tener vinculo_medida_ens populated."""
    rows = load_obligations()
    with_ens_link = sum(
        1 for r in rows if json.loads(r["vinculo_medida_ens"])
    )
    threshold = 150  # plan v3.9 nominal ~150 cross-mappings ENS
    assert with_ens_link >= threshold, (
        f"Only {with_ens_link} entries have vinculo_medida_ens populated, "
        f"expected ≥{threshold} (60% coverage)"
    )


def test_codigo_format_consistency():
    """v2 EXPAND: codigo prefix matches regulacion (RGPD-/LOPDGDD-/NIS2-/DORA-/AIACT-)."""
    rows = load_obligations()
    prefix_map = {
        "RGPD": "RGPD",
        "LOPDGDD": "LOPDGDD",
        "NIS2": "NIS2",
        "DORA": "DORA",
        "AI_Act": "AIACT",
    }
    for row in rows:
        expected_prefix = prefix_map[row["regulacion"]]
        assert row["codigo"].startswith(expected_prefix), (
            f"codigo {row['codigo']} does not match expected prefix "
            f"{expected_prefix} for regulacion {row['regulacion']}"
        )
