"""Smoke test for magerit threats seed loader.

Validates the YAML parser produces exactly 57 unique threats across the
4 official MAGERIT v3 Libro II families (N:3, I:12, E:18, A:24).
"""
from __future__ import annotations

from backend.scripts.seed.seed_magerit_threats_libro2 import (
    EXPECTED_COUNT,
    EXPECTED_FAMILIES,
    load_threats,
)


def test_load_threats_returns_57_entries():
    rows = load_threats()
    assert len(rows) == EXPECTED_COUNT == 57


def test_threat_codes_are_unique():
    rows = load_threats()
    codes = [r["code"] for r in rows]
    assert len(codes) == len(set(codes)), "Duplicated threat codes in YAML"


def test_threats_have_required_fields():
    rows = load_threats()
    for row in rows:
        assert row["code"], "code missing"
        assert row["name"], f"name missing for {row['code']}"
        assert row["group_code"], f"group_code missing for {row['code']}"
        assert isinstance(row["affected_asset_types"], str)
        assert isinstance(row["affected_dimensions"], str)


def test_threats_family_distribution_matches_libro_ii():
    rows = load_threats()
    fam_counts: dict[str, int] = {}
    for r in rows:
        fam_counts[r["group_code"]] = fam_counts.get(r["group_code"], 0) + 1
    assert fam_counts == EXPECTED_FAMILIES, (
        f"Family distribution {fam_counts} != official {EXPECTED_FAMILIES}"
    )
