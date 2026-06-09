#!/usr/bin/env python3
"""Corrige ``ens_measures`` a la tabla autoritativa del Anexo II RD 311/2022.

Auditoría 2026-06-07: el catálogo había derivado a numeración/nombres/aplicabilidad
del RD 3/2010 (derogado). Verificado contra el BOE-A-2022-7191 (Anexo II, tabla
oficial), se detectaron 23 celdas de aplicabilidad incorrectas + 11 nombres legacy
(incl. desfase de mp.info y op.exp.10 "Protección de claves criptográficas" que el
RD 3/2010 numeraba op.exp.11).

Este script es IDEMPOTENTE: actualiza nombre + aplica_basica/media/alta + descripcion
de las 73 medidas canónicas a partir de ``ANEXO_II_RD311`` (fuente única de verdad),
tomando la descripción del YAML por coincidencia de NOMBRE (resuelve el desfase).

NO crea ni borra filas (las 73 ya existen). NO toca refuerzos.

Uso:
    python scripts/fix_ens_measures_rd311_2022.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.motors.m03_dda.anexo2_rd311_2022 import (  # noqa: E402
    ANEXO_II_RD311,
    applicability_counts,
    resolve_entries,
)

CATALOG_PATH = PROJECT_ROOT / "docs" / "catalogs" / "ens_measures_catalog_v1.yaml"


def get_db_url() -> str:
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"')
                return url.replace("postgresql+asyncpg://", "postgresql://")
    return "postgresql://fulkro:changeme@localhost:5433/fulkro"


def apply_authoritative_overrides(conn, *, dry_run: bool = False) -> dict:
    """Aplica la tabla autoritativa RD 311/2022 a ens_measures. Reutilizable por el loader."""
    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    entries = resolve_entries(data["medidas"])

    changed = 0
    skipped_missing = []
    for codigo, e in entries.items():
        row = conn.execute(
            text(
                "SELECT nombre, aplica_basica, aplica_media, aplica_alta "
                "FROM ens_measures WHERE codigo = :c"
            ),
            {"c": codigo},
        ).first()
        if row is None:
            skipped_missing.append(codigo)
            continue
        cur = (row[0], bool(row[1]), bool(row[2]), bool(row[3]))
        new = (e["nombre"], e["aplica_basica"], e["aplica_media"], e["aplica_alta"])
        if cur != new:
            changed += 1
        if not dry_run:
            conn.execute(
                text(
                    "UPDATE ens_measures SET nombre = :n, descripcion = :d, "
                    "requisito_base = :rb, aplica_basica = :b, aplica_media = :m, "
                    "aplica_alta = :a, categoria_minima = :cm, "
                    "fuente_oficial = 'RD 311/2022 Anexo II (BOE-A-2022-7191)', "
                    "version_ens = 'RD 311/2022', updated_at = now() "
                    "WHERE codigo = :c"
                ),
                {
                    "c": codigo,
                    "n": e["nombre"],
                    "d": e["descripcion"],
                    "rb": (e["descripcion"] or None) and e["descripcion"][:500],
                    "b": e["aplica_basica"],
                    "m": e["aplica_media"],
                    "a": e["aplica_alta"],
                    "cm": "BASICA"
                    if e["aplica_basica"]
                    else ("MEDIA" if e["aplica_media"] else "ALTA"),
                },
            )
    return {"changed": changed, "skipped_missing": skipped_missing, "total": len(entries)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix ens_measures to RD 311/2022 Anexo II")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    engine = create_engine(get_db_url())
    with engine.begin() as conn:
        report = apply_authoritative_overrides(conn, dry_run=args.dry_run)

    b, m, a = applicability_counts()
    print("=" * 60)
    print("FIX ens_measures -> RD 311/2022 Anexo II (BOE-A-2022-7191)")
    print("=" * 60)
    print(f"  total canonical measures: {report['total']}")
    print(f"  rows changed: {report['changed']}")
    if report["skipped_missing"]:
        print(f"  MISSING in DB (not updated): {report['skipped_missing']}")
    print(f"  authoritative applicability -> BASICA {b} / MEDIA {m} / ALTA {a}")
    print(f"  mode: {'DRY-RUN (no writes)' if args.dry_run else 'APPLIED'}")


if __name__ == "__main__":
    main()
