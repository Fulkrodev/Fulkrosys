#!/usr/bin/env python3
"""Loader de trazabilidad MAGERIT v3 Libro II (refuerzo Motor 2).

ALCANCE ESTRICTO — non-destructivo:
- Solo UPDATE a official_description y official_source
- NUNCA toca description, name, group_code, affected_asset_types,
  affected_dimensions, typical_frequency
- Idempotente: re-ejecucion actualiza los valores sin anadir filas

Uso:
    python scripts/load_magerit_libro2_traceability.py
"""
import sys
from pathlib import Path

import yaml
from sqlalchemy import create_engine, text

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CATALOG_PATH = PROJECT_ROOT / "docs" / "catalogs" / "magerit_libro2_catalog_v1.yaml"


def get_db_url():
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"')
                return url.replace("postgresql+asyncpg://", "postgresql://")
    return "postgresql://fulkro:changeme@localhost:5433/fulkro"


def main():
    if not CATALOG_PATH.exists():
        print(f"ERROR: {CATALOG_PATH} not found")
        sys.exit(1)

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = yaml.safe_load(f)

    yaml_threats = {t["codigo"]: t for t in catalog["amenazas"]}
    engine = create_engine(get_db_url())

    with engine.connect() as conn:
        updated = 0
        not_found = []

        for code, threat in yaml_threats.items():
            result = conn.execute(
                text("""
                    UPDATE magerit_threats
                    SET official_description = :desc,
                        official_source = :src,
                        updated_at = now()
                    WHERE code = :code
                """),
                {
                    "code": code,
                    "desc": threat.get("descripcion", ""),
                    "src": threat.get("fuente_oficial", "MAGERIT v3 Libro II"),
                },
            )
            if result.rowcount > 0:
                updated += 1
            else:
                not_found.append(code)

        conn.commit()

        # Integrity check — original description column untouched
        check = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE description IS NOT NULL) as with_short_desc,
                COUNT(*) FILTER (WHERE official_description IS NOT NULL) as with_libro2,
                COUNT(*) FILTER (WHERE official_source IS NOT NULL) as with_source
            FROM magerit_threats
        """))
        row = check.one()

    print(f"\n{'='*60}")
    print("MAGERIT LIBRO II TRACEABILITY LOADER — REPORT")
    print(f"{'='*60}")
    print(f"  Updated:        {updated}")
    print(f"  Not found in DB: {len(not_found)}")
    if not_found:
        print(f"  Codes: {not_found}")
    print()
    print(f"  Integrity check (all {row.total} rows):")
    print(f"    Con description original:     {row.with_short_desc}")
    print(f"    Con official_description:     {row.with_libro2}")
    print(f"    Con official_source:          {row.with_source}")
    print()

    if row.with_short_desc == 57:
        print("  INTEGRIDAD OK — descripciones cortas originales intactas")
    else:
        print(f"  REGRESION — descripciones cortas bajaron a {row.with_short_desc}/57")


if __name__ == "__main__":
    main()
