"""Seed Apache AGE ``fulkro_kg`` graph from structured DB tables.

Nodes created:
- ``:Medida`` — one per row in ``ens_measures`` (73)
- ``:Refuerzo`` — one per row in ``ens_reinforcements`` (~24)
- ``:Categoria`` — BASICA / MEDIA / ALTA (3)
- ``:Guia`` — one per distinct ``guia_code`` in ``ens_measure_guias_ccn`` (may be 0)

Edges:
- ``(:Medida)-[:APLICA_A]->(:Categoria)`` from ``ens_measures.categoria_minima``
  (a medida with BASICA applies to all three; MEDIA to M+A; ALTA only to A)
- ``(:Medida)-[:REFUERZA]->(:Refuerzo)`` from ``ens_reinforcements`` with
  properties ``{codigo_refuerzo, aplica_categoria_minima, dimension_aplicable}``
- ``(:Medida)-[:APLICA_GUIA]->(:Guia)`` from ``ens_measure_guias_ccn`` if populated

Idempotent: drops and recreates ``fulkro_kg`` so re-runs are safe. Existing
test nodes (from earlier fulkro_kg smoke tests) are discarded.

Run:
    PYTHONPATH=. python backend/scripts/age_seed_kg.py
"""
from __future__ import annotations

import os
import sys

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://fulkro:changeme@localhost:5433/fulkro",
)
GRAPH_NAME = "fulkro_kg"

_CATEGORIES_ABOVE = {
    "BASICA": ["BASICA", "MEDIA", "ALTA"],
    "MEDIA": ["MEDIA", "ALTA"],
    "ALTA": ["ALTA"],
}


def _cypher(cur, stmt: str, return_cols: str = "v agtype"):
    """Execute a Cypher statement against ``fulkro_kg`` via AGE."""
    cur.execute(
        f"SELECT * FROM cypher(%s, $fulkro${stmt}$fulkro$) AS ({return_cols});",
        (GRAPH_NAME,),
    )
    return cur.fetchall()


def _esc(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def main() -> int:
    with psycopg2.connect(DATABASE_URL) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")

            cur.execute(
                "SELECT 1 FROM ag_catalog.ag_graph WHERE name = %s;", (GRAPH_NAME,)
            )
            if cur.fetchone():
                cur.execute("SELECT drop_graph(%s, true);", (GRAPH_NAME,))
            cur.execute("SELECT create_graph(%s);", (GRAPH_NAME,))

            for cat in ("BASICA", "MEDIA", "ALTA"):
                _cypher(
                    cur,
                    f"CREATE (c:Categoria {{nombre: '{cat}'}}) RETURN c",
                )

            cur.execute(
                """
                SELECT codigo, nombre, categoria_minima, marco
                FROM ens_measures
                ORDER BY codigo
                """
            )
            measures = cur.fetchall()
            for codigo, nombre, cat_min, marco in measures:
                stmt = (
                    f"CREATE (m:Medida {{codigo: {_esc(codigo)}, "
                    f"nombre: {_esc(nombre)}, "
                    f"categoria_minima: {_esc(cat_min)}, "
                    f"marco: {_esc(marco)}}}) RETURN m"
                )
                _cypher(cur, stmt)
                for cat in _CATEGORIES_ABOVE.get((cat_min or "BASICA").upper(), []):
                    link = (
                        f"MATCH (m:Medida {{codigo: {_esc(codigo)}}}), "
                        f"(c:Categoria {{nombre: '{cat}'}}) "
                        f"CREATE (m)-[:APLICA_A]->(c) RETURN 1"
                    )
                    _cypher(cur, link, return_cols="v agtype")

            cur.execute(
                """
                SELECT m.codigo, r.codigo_refuerzo, r.aplica_categoria_minima,
                       r.dimension_aplicable, r.descripcion
                FROM ens_reinforcements r
                JOIN ens_measures m ON m.id = r.measure_id
                """
            )
            refs = cur.fetchall()
            for codigo, ref_code, ref_cat, dim, descr in refs:
                _cypher(
                    cur,
                    (
                        f"MATCH (m:Medida {{codigo: {_esc(codigo)}}}) "
                        f"CREATE (m)-[:REFUERZA {{codigo: {_esc(ref_code)}, "
                        f"categoria: {_esc(ref_cat)}, "
                        f"dimension: {_esc(dim)}}}]"
                        f"->(r:Refuerzo {{codigo: {_esc(ref_code)}, "
                        f"medida: {_esc(codigo)}, "
                        f"categoria: {_esc(ref_cat)}, "
                        f"descripcion: {_esc((descr or '')[:240])}}}) RETURN 1"
                    ),
                )

            cur.execute(
                """
                SELECT measure_code, guia_code, section_ref
                FROM ens_measure_guias_ccn
                """
            )
            guias = cur.fetchall()
            guia_codes_seen: set[str] = set()
            for measure_code, guia_code, section_ref in guias:
                if guia_code not in guia_codes_seen:
                    _cypher(cur, f"CREATE (g:Guia {{codigo: {_esc(guia_code)}}}) RETURN g")
                    guia_codes_seen.add(guia_code)
                _cypher(
                    cur,
                    (
                        f"MATCH (m:Medida {{codigo: {_esc(measure_code)}}}), "
                        f"(g:Guia {{codigo: {_esc(guia_code)}}}) "
                        f"CREATE (m)-[:APLICA_GUIA {{section: {_esc(section_ref or '')}}}]"
                        f"->(g) RETURN 1"
                    ),
                )

            count = lambda label: _cypher(
                cur, f"MATCH (n:{label}) RETURN count(n)", return_cols="c agtype"
            )[0][0]
            print(
                f"AGE graph '{GRAPH_NAME}' seeded: "
                f"Medida={count('Medida')} · "
                f"Refuerzo={count('Refuerzo')} · "
                f"Categoria={count('Categoria')} · "
                f"Guia={count('Guia')}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
