"""Seed magerit_safeguards table from docs/magerit_catalog/safeguards.yaml.

Source: MAGERIT v3.0 Libro II "Catalogo de Elementos", Capitulo 6 (p.53-57).
98 safeguards in 16 families.

Idempotent: ON CONFLICT (code) DO UPDATE.
Run with --dry-run to preview without writes.

Usage:
    .venv/bin/python backend/scripts/seed/seed_magerit_safeguards_libro2_cap6.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml
from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parents[3]
YAML_PATH = REPO_ROOT / "docs" / "magerit_catalog" / "safeguards.yaml"
EXPECTED_COUNT = 98


def load_safeguards() -> list[dict]:
    with YAML_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    rows: list[dict] = []
    for fam in data.get("safeguard_families", []):
        family_code = fam["family"]
        for sg in fam.get("safeguards", []):
            rows.append(
                {
                    "code": sg["code"],
                    "name": sg["name"],
                    "family": family_code,
                    "protects_asset_types": json.dumps(sg.get("protects_assets", [])),
                    "mitigates_threats": json.dumps(sg.get("mitigates", [])),
                    "efficacy_typical": sg.get("efficacy_typical"),
                }
            )
    return rows


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL_SYNC")
    if url:
        return url
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL_SYNC="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("DATABASE_URL_SYNC not set; export it or define in .env")


UPSERT_SQL = text(
    """
    INSERT INTO magerit_safeguards
        (code, name, family, protects_asset_types, mitigates_threats, efficacy_typical)
    VALUES
        (:code, :name, :family, CAST(:protects_asset_types AS jsonb),
         CAST(:mitigates_threats AS jsonb), :efficacy_typical)
    ON CONFLICT (code) DO UPDATE SET
        name = EXCLUDED.name,
        family = EXCLUDED.family,
        protects_asset_types = EXCLUDED.protects_asset_types,
        mitigates_threats = EXCLUDED.mitigates_threats,
        efficacy_typical = EXCLUDED.efficacy_typical,
        updated_at = now()
    RETURNING (xmax = 0) AS inserted
    """
)


def run(dry_run: bool) -> int:
    rows = load_safeguards()
    print(f"Parsed {len(rows)} safeguards from {YAML_PATH.relative_to(REPO_ROOT)}")
    if len(rows) != EXPECTED_COUNT:
        print(f"WARN: expected {EXPECTED_COUNT}, got {len(rows)}", file=sys.stderr)

    if dry_run:
        print("DRY-RUN: would upsert", len(rows), "rows. Sample:")
        for row in rows[:3]:
            print(" ", row)
        return 0

    engine = create_engine(get_database_url(), future=True)
    inserts = updates = 0
    with engine.begin() as conn:
        for row in rows:
            result = conn.execute(UPSERT_SQL, row).scalar_one()
            if result:
                inserts += 1
            else:
                updates += 1
        total = conn.execute(text("SELECT COUNT(*) FROM magerit_safeguards")).scalar_one()

    print(f"Upsert complete: {inserts} inserted, {updates} updated, {total} total in table")
    if total != EXPECTED_COUNT:
        print(f"ERROR: table has {total}, expected {EXPECTED_COUNT}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate without writing")
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
