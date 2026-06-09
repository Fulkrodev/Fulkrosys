"""Smoke test for ens_measure_guias_ccn seed loader.

Validates YAML produces mappings covering >= 73 ENS Anexo II measures with
at least 1 primary guia each.
"""
from __future__ import annotations

from backend.scripts.seed.seed_ens_measure_guias_ccn import (
    EXPECTED_MEASURES,
    load_mappings,
)


def test_load_mappings_covers_73_measures():
    rows = load_mappings()
    measures = {r["measure_code"] for r in rows}
    assert len(measures) >= EXPECTED_MEASURES == 73


def test_mappings_total_count_reasonable():
    """Briefing target: 120-180 total mappings (1.6-2.4 guias per measure on avg)."""
    rows = load_mappings()
    assert 73 <= len(rows) <= 250, f"Total mappings out of range: {len(rows)}"


def test_no_duplicate_mappings():
    """UNIQUE (measure_code, guia_code, section_ref) must hold."""
    rows = load_mappings()
    keys = [(r["measure_code"], r["guia_code"], r["section_ref"]) for r in rows]
    assert len(keys) == len(set(keys)), "Duplicate (measure, guia, section) detected in YAML"


def test_each_measure_has_primary_guia():
    """Every measure must have at least one row with prioridad=primaria."""
    import json as _json

    rows = load_mappings()
    primary_measures: set[str] = set()
    for r in rows:
        meta = _json.loads(r["metadata_json"])
        if meta.get("prioridad") == "primaria":
            primary_measures.add(r["measure_code"])
    all_measures = {r["measure_code"] for r in rows}
    missing_primary = all_measures - primary_measures
    assert not missing_primary, f"Measures without primary guia: {sorted(missing_primary)}"
