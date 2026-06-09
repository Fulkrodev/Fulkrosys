#!/usr/bin/env python3
"""
ENS Measures Catalog Loader: YAML -> DB (Motor 3 DdA Engine).

Loads the 73 ENS Anexo II measures + reinforcements from
docs/catalogs/ens_measures_catalog_v1.yaml into ens_measures
and ens_reinforcements tables.

Source of truth for the 73 codes: magerit_ens_mapping table.
The YAML has 79 entries: the 6 extra (op.exp.11, mp.s.8, mp.s.9, mp.if.9,
mp.per.9, mp.com.9) are RD 3/2010 (derogado) legacy codes that do NOT exist in
RD 311/2022 Anexo II — their concepts live under RD 311/2022 codes already
loaded (claves criptográficas -> op.exp.10; denegación de servicio -> mp.s.4;
medios/instalaciones/personal alternativos -> op.cont.4). Only the 73 codes in
magerit_ens_mapping are loaded.

Names + per-level applicability are then forced to the authoritative RD 311/2022
Anexo II table (BOE-A-2022-7191) via apply_authoritative_overrides(), because the
YAML/magerit data still carried RD 3/2010 names and applicability (audit 2026-06-07).

Idempotent: uses INSERT ON CONFLICT DO UPDATE on ens_measures.codigo
unique constraint. Reinforcements are deleted+reinserted atomically.

Usage:
    python scripts/load_ens_measures_catalog.py [--dry-run] [--verbose]
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
CATALOG_PATH = PROJECT_ROOT / "docs" / "catalogs" / "ens_measures_catalog_v1.yaml"


def get_db_url():
    """Read sync DB URL from .env."""
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"')
                return url.replace("postgresql+asyncpg://", "postgresql://")
    return "postgresql://fulkro:changeme@localhost:5433/fulkro"


def get_magerit_ens_codes(conn) -> set:
    """Get the 73 confirmed ENS codes from magerit_ens_mapping."""
    result = conn.execute(
        text("SELECT DISTINCT ens_measure FROM magerit_ens_mapping ORDER BY ens_measure")
    )
    return {row[0] for row in result.fetchall()}


def load_measures(conn, verbose=False, dry_run=False):
    """Load ens_measures + ens_reinforcements. Returns report dict."""
    # 1. Load YAML
    if not CATALOG_PATH.exists():
        print(f"ERROR: Catalog not found at {CATALOG_PATH}")
        sys.exit(1)

    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    yaml_measures = {m["codigo"]: m for m in data["medidas"]}

    # 2. Cross-check with magerit_ens_mapping (source of truth)
    db_codes = get_magerit_ens_codes(conn)
    in_yaml_not_db = sorted(set(yaml_measures.keys()) - db_codes)
    in_db_not_yaml = sorted(db_codes - set(yaml_measures.keys()))
    intersection = sorted(set(yaml_measures.keys()) & db_codes)

    if verbose:
        print(f"YAML codes: {len(yaml_measures)}")
        print(f"DB codes (magerit_ens_mapping): {len(db_codes)}")
        print(f"Intersection: {len(intersection)}")
        if in_yaml_not_db:
            print(f"In YAML not DB (skipped): {in_yaml_not_db}")
        if in_db_not_yaml:
            print(f"In DB not YAML (loaded as TODO): {in_db_not_yaml}")

    if dry_run:
        print("[DRY RUN] Would load measures and reinforcements. Exiting.")
        return {"dry_run": True}

    # 3. Load measures (ON CONFLICT DO UPDATE for idempotency)
    measures_inserted = 0
    measures_updated = 0
    measures_todo = 0

    for code in sorted(db_codes):
        if code in yaml_measures:
            m = yaml_measures[code]
            dims = m.get("dimensiones_aplicables", [])
            params = {
                "codigo": m["codigo"],
                "nombre": m["nombre"],
                "marco": m["marco"],
                "familia": m.get("familia", m["marco"]),
                "descripcion": m.get("descripcion", ""),
                "requisito_base": m.get("descripcion", "")[:500] if m.get("descripcion") else None,
                "fuente_oficial": m.get("fuente_oficial", "CCN-STIC 804 v2017"),
                "version_ens": "RD 311/2022",
                "aplica_basica": m.get("aplica_basica", True),
                "aplica_media": m.get("aplica_media", True),
                "aplica_alta": m.get("aplica_alta", True),
                "categoria_minima": m.get("categoria_minima", "BASICA"),
                "dimensiones_aplicables": json.dumps(dims) if dims else None,
            }
        else:
            # Code in DB but not in YAML — create with TODO, aplica todas
            marco = code.split(".")[0]
            familia = ".".join(code.split(".")[:2]) if "." in code else marco
            params = {
                "codigo": code,
                "nombre": f"TODO: {code}",
                "marco": marco,
                "familia": familia,
                "descripcion": f"Medida {code} presente en magerit_ens_mapping pero sin descripcion en CCN-STIC 804 v2017. Cargar desde RD 311/2022 Anexo II.",
                "requisito_base": "TODO",
                "fuente_oficial": "RD 311/2022 Anexo II",
                "version_ens": "RD 311/2022",
                "aplica_basica": True,
                "aplica_media": True,
                "aplica_alta": True,
                "categoria_minima": "BASICA",
                "dimensiones_aplicables": None,
            }
            measures_todo += 1

        result = conn.execute(text("""
            INSERT INTO ens_measures (codigo, nombre, marco, familia, descripcion, requisito_base,
                fuente_oficial, version_ens, aplica_basica, aplica_media, aplica_alta,
                categoria_minima, dimensiones_aplicables)
            VALUES (:codigo, :nombre, :marco, :familia, :descripcion, :requisito_base,
                :fuente_oficial, :version_ens, :aplica_basica, :aplica_media, :aplica_alta,
                :categoria_minima, CAST(:dimensiones_aplicables AS jsonb))
            ON CONFLICT (codigo) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                marco = EXCLUDED.marco,
                familia = EXCLUDED.familia,
                descripcion = EXCLUDED.descripcion,
                requisito_base = EXCLUDED.requisito_base,
                fuente_oficial = EXCLUDED.fuente_oficial,
                version_ens = EXCLUDED.version_ens,
                aplica_basica = EXCLUDED.aplica_basica,
                aplica_media = EXCLUDED.aplica_media,
                aplica_alta = EXCLUDED.aplica_alta,
                categoria_minima = EXCLUDED.categoria_minima,
                dimensiones_aplicables = EXCLUDED.dimensiones_aplicables,
                updated_at = now()
            RETURNING (xmax = 0) AS is_insert
        """), params)
        is_insert = result.scalar()
        if is_insert:
            measures_inserted += 1
        else:
            measures_updated += 1

    # 4. Load reinforcements (DELETE + INSERT for idempotency)
    conn.execute(text("DELETE FROM ens_reinforcements"))

    reinforcements_created = 0
    for code in intersection:
        m = yaml_measures[code]
        refuerzos = m.get("refuerzos", {})
        if not refuerzos:
            continue

        # Get measure_id
        measure_id = conn.execute(
            text("SELECT id FROM ens_measures WHERE codigo = :c"),
            {"c": code},
        ).scalar()
        if not measure_id:
            continue  # pragma: no cover

        dims = ",".join(m.get("dimensiones_aplicables", []))

        for cat_minima, r_codes in refuerzos.items():
            for r_code in r_codes:
                conn.execute(text("""
                    INSERT INTO ens_reinforcements
                        (measure_id, codigo_refuerzo, descripcion,
                         aplica_categoria_minima, dimension_aplicable)
                    VALUES (:mid, :rc, :desc, :cat, :dim)
                """), {
                    "mid": str(measure_id),
                    "rc": r_code,
                    "desc": f"Refuerzo {r_code} de {code} - aplica desde categoria {cat_minima}",
                    "cat": cat_minima,
                    "dim": dims,
                })
                reinforcements_created += 1

    # 5. Override autoritativo RD 311/2022 Anexo II (BOE-A-2022-7191).
    #    El YAML/magerit_ens_mapping arrastraba numeración/nombres/aplicabilidad
    #    del RD 3/2010 (derogado). Esta pasada fija nombre + aplica_* + descripcion
    #    (por coincidencia de nombre) a la tabla oficial verificada. Idempotente.
    #    Ver scripts/fix_ens_measures_rd311_2022.py + anexo2_rd311_2022.py.
    authoritative = {}
    if not dry_run:
        sys.path.insert(0, str(PROJECT_ROOT))
        from scripts.fix_ens_measures_rd311_2022 import apply_authoritative_overrides

        authoritative = apply_authoritative_overrides(conn, dry_run=False)

    conn.commit()

    return {
        "measures_inserted": measures_inserted,
        "measures_updated": measures_updated,
        "measures_todo": measures_todo,
        "measures_total": measures_inserted + measures_updated,
        "reinforcements_created": reinforcements_created,
        "in_yaml_not_db": in_yaml_not_db,
        "in_db_not_yaml": in_db_not_yaml,
        "intersection": len(intersection),
        "rd311_authoritative_changed": authoritative.get("changed", 0),
    }


def main():
    parser = argparse.ArgumentParser(description="Load ENS measures catalog")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    db_url = get_db_url()
    engine = create_engine(db_url)

    t0 = time.time()
    with engine.connect() as conn:
        report = load_measures(conn, verbose=args.verbose, dry_run=args.dry_run)
    elapsed = time.time() - t0

    print("=" * 60)
    print("ENS MEASURES CATALOG LOADER — REPORT")
    print("=" * 60)
    for k, v in report.items():
        if isinstance(v, list):
            print(f"  {k}: {v}")
        else:
            print(f"  {k}: {v}")
    print(f"  elapsed: {elapsed:.2f}s")


if __name__ == "__main__":
    main()
