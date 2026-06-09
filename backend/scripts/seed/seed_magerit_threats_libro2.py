"""Seed magerit_threats table from docs/catalogs/magerit_libro2_catalog_v1.yaml.

Source: MAGERIT v3.0 Libro II "Catalogo de Elementos" · 57 amenazas in 4 families
(N: Desastres naturales · I: De origen industrial · E: Errores y fallos no
intencionados · A: Ataques intencionados).

Idempotent: ON CONFLICT (code) DO UPDATE.

Usage:
    .venv/bin/python backend/scripts/seed/seed_magerit_threats_libro2.py [--dry-run]
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
YAML_PATH = REPO_ROOT / "docs" / "catalogs" / "magerit_libro2_catalog_v1.yaml"
EXPECTED_COUNT = 57
EXPECTED_FAMILIES = {"N": 3, "I": 12, "E": 18, "A": 24}


def load_threats() -> list[dict]:
    with YAML_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    rows: list[dict] = []
    for a in data.get("amenazas", []):
        rows.append(
            {
                "code": a["codigo"],
                "name": a["nombre"],
                "group_code": a["familia"],
                "description": a.get("descripcion"),
                "affected_asset_types": json.dumps(a.get("tipos_activos_afectados", [])),
                "affected_dimensions": json.dumps(a.get("dimensiones_afectadas", [])),
                "official_source": a.get("fuente_oficial"),
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
    INSERT INTO magerit_threats
        (code, name, group_code, description, affected_asset_types,
         affected_dimensions, official_source)
    VALUES
        (:code, :name, :group_code, :description,
         CAST(:affected_asset_types AS jsonb),
         CAST(:affected_dimensions AS jsonb),
         :official_source)
    ON CONFLICT (code) DO UPDATE SET
        name = EXCLUDED.name,
        group_code = EXCLUDED.group_code,
        description = EXCLUDED.description,
        affected_asset_types = EXCLUDED.affected_asset_types,
        affected_dimensions = EXCLUDED.affected_dimensions,
        official_source = EXCLUDED.official_source,
        updated_at = now()
    RETURNING (xmax = 0) AS inserted
    """
)


def run(dry_run: bool) -> int:
    rows = load_threats()
    print(f"Parsed {len(rows)} threats from {YAML_PATH.relative_to(REPO_ROOT)}")
    if len(rows) != EXPECTED_COUNT:
        print(f"WARN: expected {EXPECTED_COUNT}, got {len(rows)}", file=sys.stderr)

    fam_counts: dict[str, int] = {}
    for r in rows:
        fam_counts[r["group_code"]] = fam_counts.get(r["group_code"], 0) + 1
    if fam_counts != EXPECTED_FAMILIES:
        print(
            f"WARN: family distribution {fam_counts} != expected {EXPECTED_FAMILIES}",
            file=sys.stderr,
        )

    if dry_run:
        print(f"DRY-RUN: would upsert {len(rows)} threats. Families: {fam_counts}. Sample:")
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
        total = conn.execute(text("SELECT COUNT(*) FROM magerit_threats")).scalar_one()

    print(f"Upsert complete: {inserts} inserted, {updates} updated, {total} total in table")
    if total != EXPECTED_COUNT:
        print(f"ERROR: table has {total}, expected {EXPECTED_COUNT}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
