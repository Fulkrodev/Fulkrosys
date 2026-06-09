"""Smoke test for magerit safeguards seed loader.

Validates the YAML parser produces exactly 98 unique safeguards across
16 families (MAGERIT v3 Libro II Cap.6).

DB-level count verification is exercised at seed run time by the script
itself (see ``EXPECTED_COUNT`` and the final assertion in ``run()``).
"""
from __future__ import annotations

from backend.scripts.seed.seed_magerit_safeguards_libro2_cap6 import (
    EXPECTED_COUNT,
    load_safeguards,
)


def test_load_safeguards_returns_98_entries():
    rows = load_safeguards()
    assert len(rows) == EXPECTED_COUNT == 98


def test_safeguard_codes_are_unique():
    rows = load_safeguards()
    codes = [r["code"] for r in rows]
    assert len(codes) == len(set(codes)), "Duplicated safeguard codes in YAML"


def test_safeguards_have_required_fields():
    rows = load_safeguards()
    for row in rows:
        assert row["code"], "code missing"
        assert row["name"], f"name missing for {row['code']}"
        assert row["family"], f"family missing for {row['code']}"
        # protects_asset_types and mitigates_threats are JSON strings (may be "[]")
        assert isinstance(row["protects_asset_types"], str)
        assert isinstance(row["mitigates_threats"], str)


def test_safeguards_span_16_families():
    rows = load_safeguards()
    families = {r["family"] for r in rows}
    assert len(families) == 16, f"Expected 16 families, got {len(families)}: {families}"
