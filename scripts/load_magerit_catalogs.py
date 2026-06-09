#!/usr/bin/env python3
"""
MAGERIT v3 Catalog Loader: YAML → DB.

Loads the 4 MAGERIT v3 catalogs from docs/magerit_catalog/ into the
corresponding SQL tables. Idempotent via INSERT ... ON CONFLICT DO UPDATE.

Usage:
    python scripts/load_magerit_catalogs.py [--dry-run] [--verbose]

Catalogs loaded (in order):
    1. asset_types.yaml   → magerit_asset_types   (codes normalized: [S.pub] → S.pub)
    2. threats.yaml       → magerit_threats
    3. safeguards.yaml    → magerit_safeguards
    4. ens_mapping.yaml   → magerit_ens_mapping
"""
import argparse
import json
import sys
import time
from pathlib import Path

import yaml
from sqlalchemy import create_engine, text

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CATALOG_DIR = PROJECT_ROOT / "docs" / "magerit_catalog"

# DB URL from .env or default
def get_db_url():
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"')
                # Convert async URL to sync
                return url.replace("postgresql+asyncpg://", "postgresql://")
    return "postgresql://fulkro:changeme@localhost:5433/fulkro"


def normalize_code(code: str) -> str:
    """Strip brackets from MAGERIT codes: [S.pub] → S.pub"""
    return code.strip("[]")


def load_asset_types(conn, verbose=False):
    """Load asset_types.yaml → magerit_asset_types."""
    data = yaml.safe_load((CATALOG_DIR / "asset_types.yaml").read_text())
    rows = []

    for category in data["asset_categories"]:
        cat_code = normalize_code(category["code"])

        # Top-level category row (self-referencing category_code)
        rows.append({
            "code": cat_code,
            "name": category["name"],
            "category_code": cat_code,
            "description": category.get("description"),
            "default_dimensions": None,
        })

        # Subtypes
        for subtype in category.get("subtypes", []):
            dims = subtype.get("dimensions", [])
            dim_json = json.dumps({d: True for d in dims}) if dims else None
            rows.append({
                "code": normalize_code(subtype["code"]),
                "name": subtype["name"],
                "category_code": cat_code,
                "description": subtype.get("description"),
                "default_dimensions": dim_json,
            })

    inserted = 0
    updated = 0
    for row in rows:
        result = conn.execute(text("""
            INSERT INTO magerit_asset_types (code, name, category_code, description, default_dimensions)
            VALUES (:code, :name, :category_code, :description, CAST(:default_dimensions AS jsonb))
            ON CONFLICT (code) DO UPDATE SET
                name = EXCLUDED.name,
                category_code = EXCLUDED.category_code,
                description = EXCLUDED.description,
                default_dimensions = EXCLUDED.default_dimensions,
                updated_at = now()
            RETURNING (xmax = 0) AS is_insert
        """), row)
        is_insert = result.scalar()
        if is_insert:
            inserted += 1
        else:
            updated += 1

    if verbose:
        print(f"[asset_types]  Loaded {len(rows)} rows ({updated} updated, {inserted} inserted)")
    return len(rows)


def load_threats(conn, verbose=False):
    """Load threats.yaml → magerit_threats."""
    data = yaml.safe_load((CATALOG_DIR / "threats.yaml").read_text())
    rows = []

    for group in data["threat_groups"]:
        group_code = group["group"]
        for threat in group.get("threats", []):
            rows.append({
                "code": threat["code"],
                "name": threat["name"],
                "group_code": group_code,
                "description": threat.get("description"),
                "affected_asset_types": json.dumps(threat.get("asset_types")) if threat.get("asset_types") else None,
                "affected_dimensions": json.dumps(threat.get("dimensions")) if threat.get("dimensions") else None,
                "typical_frequency": threat.get("typical_frequency"),
            })

    inserted = 0
    updated = 0
    for row in rows:
        result = conn.execute(text("""
            INSERT INTO magerit_threats (code, name, group_code, description,
                affected_asset_types, affected_dimensions, typical_frequency)
            VALUES (:code, :name, :group_code, :description,
                CAST(:affected_asset_types AS jsonb), CAST(:affected_dimensions AS jsonb), :typical_frequency)
            ON CONFLICT (code) DO UPDATE SET
                name = EXCLUDED.name,
                group_code = EXCLUDED.group_code,
                description = EXCLUDED.description,
                affected_asset_types = EXCLUDED.affected_asset_types,
                affected_dimensions = EXCLUDED.affected_dimensions,
                typical_frequency = EXCLUDED.typical_frequency,
                updated_at = now()
            RETURNING (xmax = 0) AS is_insert
        """), row)
        is_insert = result.scalar()
        if is_insert:
            inserted += 1
        else:
            updated += 1

    if verbose:
        print(f"[threats]      Loaded {len(rows)} rows ({updated} updated, {inserted} inserted)")
    return len(rows)


def load_safeguards(conn, verbose=False):
    """Load safeguards.yaml → magerit_safeguards."""
    data = yaml.safe_load((CATALOG_DIR / "safeguards.yaml").read_text())
    rows = []

    for family in data["safeguard_families"]:
        family_code = family["family"]
        for sg in family.get("safeguards", []):
            rows.append({
                "code": sg["code"],
                "name": sg["name"],
                "family": family_code,
                "description": sg.get("description"),
                "protects_asset_types": json.dumps(sg.get("protects_assets")) if sg.get("protects_assets") else None,
                "mitigates_threats": json.dumps(sg.get("mitigates")) if sg.get("mitigates") else None,
                "efficacy_typical": sg.get("efficacy_typical"),
            })

    inserted = 0
    updated = 0
    for row in rows:
        result = conn.execute(text("""
            INSERT INTO magerit_safeguards (code, name, family, description,
                protects_asset_types, mitigates_threats, efficacy_typical)
            VALUES (:code, :name, :family, :description,
                CAST(:protects_asset_types AS jsonb), CAST(:mitigates_threats AS jsonb), :efficacy_typical)
            ON CONFLICT (code) DO UPDATE SET
                name = EXCLUDED.name,
                family = EXCLUDED.family,
                description = EXCLUDED.description,
                protects_asset_types = EXCLUDED.protects_asset_types,
                mitigates_threats = EXCLUDED.mitigates_threats,
                efficacy_typical = EXCLUDED.efficacy_typical,
                updated_at = now()
            RETURNING (xmax = 0) AS is_insert
        """), row)
        is_insert = result.scalar()
        if is_insert:
            inserted += 1
        else:
            updated += 1

    if verbose:
        print(f"[safeguards]   Loaded {len(rows)} rows ({updated} updated, {inserted} inserted)")
    return len(rows)


def load_ens_mapping(conn, verbose=False):
    """Load ens_mapping.yaml → magerit_ens_mapping."""
    data = yaml.safe_load((CATALOG_DIR / "ens_mapping.yaml").read_text())
    rows = []

    for mapping in data["ens_to_magerit"]:
        safeguards = mapping.get("magerit_safeguards")
        rows.append({
            "ens_measure": mapping["measure"],
            "ens_measure_name": mapping.get("name"),
            "magerit_safeguards": json.dumps(safeguards) if safeguards else None,
            "confidence": mapping.get("confidence"),
            "notes": mapping.get("notes"),
        })

    inserted = 0
    updated = 0
    for row in rows:
        result = conn.execute(text("""
            INSERT INTO magerit_ens_mapping (ens_measure, ens_measure_name,
                magerit_safeguards, confidence, notes)
            VALUES (:ens_measure, :ens_measure_name,
                CAST(:magerit_safeguards AS jsonb), :confidence, :notes)
            ON CONFLICT (ens_measure) DO UPDATE SET
                ens_measure_name = EXCLUDED.ens_measure_name,
                magerit_safeguards = EXCLUDED.magerit_safeguards,
                confidence = EXCLUDED.confidence,
                notes = EXCLUDED.notes,
                updated_at = now()
            RETURNING (xmax = 0) AS is_insert
        """), row)
        is_insert = result.scalar()
        if is_insert:
            inserted += 1
        else:
            updated += 1

    if verbose:
        print(f"[ens_mapping]  Loaded {len(rows)} rows ({updated} updated, {inserted} inserted)")
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="Load MAGERIT v3 catalogs from YAML to DB")
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate without committing")
    parser.add_argument("--verbose", action="store_true", help="Print detailed progress")
    args = parser.parse_args()

    db_url = get_db_url()
    engine = create_engine(db_url, echo=False)

    start = time.time()
    total = 0

    with engine.begin() as conn:
        total += load_asset_types(conn, verbose=args.verbose)
        total += load_threats(conn, verbose=args.verbose)
        total += load_safeguards(conn, verbose=args.verbose)
        total += load_ens_mapping(conn, verbose=args.verbose)

        if args.dry_run:
            conn.rollback()
            print(f"DRY RUN: {total} rows parsed successfully, NOT committed.")
        else:
            elapsed = time.time() - start
            print(f"Total: {total} rows loaded in {elapsed:.1f}s")

    engine.dispose()


if __name__ == "__main__":
    main()
