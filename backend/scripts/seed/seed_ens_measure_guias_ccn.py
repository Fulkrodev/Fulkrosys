"""Seed ens_measure_guias_ccn table from docs/catalogs/ens_measure_guias_ccn_v1.yaml.

Mapping curado pragmatico: 73 medidas Anexo II RD 311/2022 -> guias CCN-STIC
primarias. NO ingesta masiva de corpus CCN-STIC (deferido post-piloto).

YAML formato bucketed: cada bucket (familia/grupo) lista measures y guias ·
loader expande cartesiano a filas (measure_code, guia_code, section_ref).

Idempotent: ON CONFLICT (measure_code, guia_code, section_ref) DO UPDATE.

Usage:
    .venv/bin/python backend/scripts/seed/seed_ens_measure_guias_ccn.py [--dry-run]
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
YAML_PATH = REPO_ROOT / "docs" / "catalogs" / "ens_measure_guias_ccn_v1.yaml"
EXPECTED_MEASURES = 73


def load_mappings() -> list[dict]:
    """Expand bucket_mappings -> flat list of (measure_code, guia_code, ...) rows."""
    with YAML_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    guia_catalog = data.get("guias_ccn_referenciadas", {})
    url_base = data.get("url_base_catalogo", "")
    rows: list[dict] = []
    for bucket in data.get("bucket_mappings", []):
        measures = bucket.get("measures", [])
        guias = bucket.get("guias", [])
        bucket_name = bucket.get("bucket", "?")
        for measure_code in measures:
            for guia in guias:
                guia_code = guia["guia_code"]
                guia_info = guia_catalog.get(guia_code, {})
                metadata = {
                    "bucket": bucket_name,
                    "prioridad": guia.get("prioridad", "primaria"),
                    "nombre_guia": guia_info.get("nombre"),
                    "url_base": url_base,
                    "url_verified": guia_info.get("url_verified", False),
                }
                rows.append(
                    {
                        "measure_code": measure_code,
                        "guia_code": guia_code,
                        "section_ref": guia.get("section_ref"),
                        "relevance": guia.get("relevance", "develops"),
                        "metadata_json": json.dumps(metadata, ensure_ascii=False),
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
    INSERT INTO ens_measure_guias_ccn
        (measure_code, guia_code, section_ref, relevance, metadata)
    VALUES
        (:measure_code, :guia_code, :section_ref, :relevance,
         CAST(:metadata_json AS jsonb))
    ON CONFLICT (measure_code, guia_code, section_ref) DO UPDATE SET
        relevance = EXCLUDED.relevance,
        metadata = EXCLUDED.metadata
    RETURNING (xmax = 0) AS inserted
    """
)


def run(dry_run: bool) -> int:
    rows = load_mappings()
    measures = {r["measure_code"] for r in rows}
    print(f"Parsed {len(rows)} mappings · {len(measures)} medidas distintas")
    if len(measures) != EXPECTED_MEASURES:
        print(
            f"WARN: expected {EXPECTED_MEASURES} medidas distintas, got {len(measures)}",
            file=sys.stderr,
        )

    if dry_run:
        print("DRY-RUN: would upsert", len(rows), "rows. Sample:")
        for row in rows[:3]:
            print(" ", row)
        return 0

    engine = create_engine(get_database_url(), future=True)

    # Pre-flight: verify all measure_codes exist in ens_measures (avoid orphans).
    with engine.begin() as conn:
        ens_codes = {
            r[0]
            for r in conn.execute(text("SELECT codigo FROM ens_measures")).all()
        }
    missing = measures - ens_codes
    if missing:
        print(
            f"ERROR: {len(missing)} measure codes NOT in ens_measures: "
            f"{sorted(missing)[:10]}...",
            file=sys.stderr,
        )
        return 1

    inserts = updates = 0
    with engine.begin() as conn:
        for row in rows:
            result = conn.execute(UPSERT_SQL, row).scalar_one()
            if result:
                inserts += 1
            else:
                updates += 1
        total = conn.execute(text("SELECT COUNT(*) FROM ens_measure_guias_ccn")).scalar_one()
        measures_covered = conn.execute(
            text("SELECT COUNT(DISTINCT measure_code) FROM ens_measure_guias_ccn")
        ).scalar_one()

    print(
        f"Upsert complete: {inserts} inserted, {updates} updated, "
        f"{total} total mappings, {measures_covered} medidas cubiertas"
    )
    if measures_covered < EXPECTED_MEASURES:
        print(
            f"ERROR: only {measures_covered} medidas covered, expected >= {EXPECTED_MEASURES}",
            file=sys.stderr,
        )
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
