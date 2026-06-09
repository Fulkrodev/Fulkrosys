"""Seed legal_obligations_catalog from docs/catalogs/legal_obligations_v1.yaml.

Catalogo MAESTRO de obligaciones legales (RGPD/LOPDGDD/NIS2/DORA/AI_Act).
Tabla NUEVA legal_obligations_catalog (sin project_id, sin RLS, readonly global)
SEPARADA de la tabla operacional legal_obligations preexistente.

Idempotent: ON CONFLICT (codigo) DO UPDATE.

Pre-flight: warning si vinculo_medida_ens contiene codes que no existen en
ens_measures.codigo (NO error, solo warning con lista de orphans).

Usage:
    .venv/bin/python backend/scripts/seed/seed_legal_obligations_catalog.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

import yaml
from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parents[3]
YAML_PATH = REPO_ROOT / "docs" / "catalogs" / "legal_obligations_v1.yaml"
EXPECTED_COUNT = 250
EXPECTED_DISTRIBUTION = {"RGPD": 80, "LOPDGDD": 30, "NIS2": 60, "DORA": 50, "AI_Act": 30}


def load_obligations() -> list[dict]:
    with YAML_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    rows: list[dict] = []
    for o in data.get("obligations", []):
        rows.append(
            {
                "codigo": o["codigo"],
                "regulacion": o["regulacion"],
                "articulo": o.get("articulo"),
                "titulo": o["titulo"],
                "obligacion": o["obligacion"],
                "sector_aplica": json.dumps(o.get("sector_aplica", []), ensure_ascii=False),
                "ens_categoria_aplica": json.dumps(
                    o.get("ens_categoria_aplica", []), ensure_ascii=False
                ),
                "evidencia_requerida": o.get("evidencia_requerida"),
                "vinculo_medida_ens": json.dumps(
                    o.get("vinculo_medida_ens", []), ensure_ascii=False
                ),
            }
        )
    return rows


def get_database_url() -> str:
    """Prefer DATABASE_MIGRATE_URL (fulkro_migrate superuser) for catalog
    write operations · falls back to DATABASE_URL_SYNC (fulkro_app · runtime
    role · read-only on catalog tables)."""
    for var in ("DATABASE_MIGRATE_URL", "DATABASE_URL_SYNC"):
        url = os.environ.get(var)
        if url:
            return url
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for var in ("DATABASE_MIGRATE_URL", "DATABASE_URL_SYNC"):
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith(f"{var}="):
                    return line.split("=", 1)[1].strip()
    raise RuntimeError("Neither DATABASE_MIGRATE_URL nor DATABASE_URL_SYNC set")


UPSERT_SQL = text(
    """
    INSERT INTO legal_obligations_catalog
        (codigo, regulacion, articulo, titulo, obligacion,
         sector_aplica, ens_categoria_aplica, evidencia_requerida,
         vinculo_medida_ens)
    VALUES
        (:codigo, :regulacion, :articulo, :titulo, :obligacion,
         CAST(:sector_aplica AS jsonb),
         CAST(:ens_categoria_aplica AS jsonb),
         :evidencia_requerida,
         CAST(:vinculo_medida_ens AS jsonb))
    ON CONFLICT (codigo) DO UPDATE SET
        regulacion = EXCLUDED.regulacion,
        articulo = EXCLUDED.articulo,
        titulo = EXCLUDED.titulo,
        obligacion = EXCLUDED.obligacion,
        sector_aplica = EXCLUDED.sector_aplica,
        ens_categoria_aplica = EXCLUDED.ens_categoria_aplica,
        evidencia_requerida = EXCLUDED.evidencia_requerida,
        vinculo_medida_ens = EXCLUDED.vinculo_medida_ens,
        updated_at = now()
    RETURNING (xmax = 0) AS inserted
    """
)


def run(dry_run: bool) -> int:
    rows = load_obligations()
    print(f"Parsed {len(rows)} obligations from {YAML_PATH.relative_to(REPO_ROOT)}")
    if len(rows) != EXPECTED_COUNT:
        print(f"WARN: expected {EXPECTED_COUNT}, got {len(rows)}", file=sys.stderr)

    dist = dict(Counter(r["regulacion"] for r in rows))
    print(f"Distribution per regulacion: {dist}")
    if dist != EXPECTED_DISTRIBUTION:
        print(
            f"WARN: distribution {dist} != expected {EXPECTED_DISTRIBUTION}",
            file=sys.stderr,
        )

    if dry_run:
        print(f"DRY-RUN: would upsert {len(rows)} obligations. Sample:")
        for row in rows[:2]:
            print(" ", {k: (v if len(str(v)) < 100 else str(v)[:80] + "...") for k, v in row.items()})
        return 0

    engine = create_engine(get_database_url(), future=True)

    with engine.begin() as conn:
        ens_codes = {
            r[0] for r in conn.execute(text("SELECT codigo FROM ens_measures")).all()
        }
    all_referenced = set()
    for r in rows:
        all_referenced.update(json.loads(r["vinculo_medida_ens"]))
    orphans = all_referenced - ens_codes
    if orphans:
        print(
            f"WARN: {len(orphans)} measure codes referenciados pero no en "
            f"ens_measures: {sorted(orphans)}",
            file=sys.stderr,
        )
    else:
        print(f"OK pre-flight: {len(all_referenced)} measure codes referenciados, todos validos")

    inserts = updates = 0
    with engine.begin() as conn:
        for row in rows:
            result = conn.execute(UPSERT_SQL, row).scalar_one()
            if result:
                inserts += 1
            else:
                updates += 1
        total = conn.execute(text("SELECT COUNT(*) FROM legal_obligations_catalog")).scalar_one()
        per_reg = conn.execute(
            text(
                "SELECT regulacion, COUNT(*) FROM legal_obligations_catalog "
                "GROUP BY regulacion ORDER BY regulacion"
            )
        ).all()

    print(f"Upsert complete: {inserts} inserted, {updates} updated, {total} total in table")
    print(f"BD distribution: {dict(per_reg)}")
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
