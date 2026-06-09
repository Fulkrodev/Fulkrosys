"""Seed ``ens_measure_refuerzos`` + ``ens_measure_dimensiones`` canónicos.

Fuente: BOE-A-2022-7191 (RD 311/2022 · Anexo II) · ya ingerido como
``knowledge_documents.title='RD 311/2022 - Esquema Nacional de Seguridad'``
con 73 chunks ``measure_code IS NOT NULL`` (uno por medida) y 51 chunks
con menciones explícitas de refuerzos R1-R5.

Estrategia: parser determinista del corpus oficial (no LLM, no invención).
Cada fila lleva ``source_chunk_id`` FK al chunk fuente para trazabilidad
ENAC ("muéstrame de dónde sale esto").

Parser usa la sección **Aplicación de la medida** del Anexo II que tiene
formato canónico inequívoco::

    Aplicación de la medida.
    – (Categoría|Nivel) (BÁSICA|BAJO): {measure_code}.
    – (Categoría|Nivel) (MEDIA|MEDIO): {measure_code} + R1.
    – (Categoría|Nivel) (ALTA|ALTO): {measure_code} + R1 + R2 + R3.

Y la sección **dimensiones** del header::

    dimensiones (Todas|<letras CIDAT>) (categoría|nivel) ...

Cada fila almacena:

``ens_measure_refuerzos``:
    measure_code · refuerzo_level (``+R1``) · applicable_categories JSONB
    (``{"BASICA": "required", "MEDIA": "required", "ALTA": "required"}``) ·
    description (título canónico Anexo II) · source_chunk_id FK ·
    metadata JSONB (source BOE).

``ens_measure_dimensiones``:
    measure_code · refuerzo_level (NULL para base) · dimension (1 char CIDAT) ·
    metadata JSONB.

Idempotente: borra filas con metadata->>'source' = 'BOE-A-2022-7191 Anexo II'
antes de re-insertar (necesario porque ON CONFLICT no funciona con NULL en
unique constraints btree de Postgres).

Run::

    PYTHONPATH=. python backend/scripts/seed_ens_measure_refuerzos.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://fulkro_app:fulkro_app_dev_password@localhost:5433/fulkro",
)

# UUID del documento RD 311/2022 ingerido en knowledge_documents.
RD_311_DOC_ID = "642e417e-e2c7-4a5c-b263-a6aac74943c5"

CIDAT_DIMENSIONS = ["D", "I", "C", "A", "T"]
CATEGORY_MAP = {
    "BÁSICA": "BASICA",
    "BASICA": "BASICA",
    "BAJO": "BASICA",
    "MEDIA": "MEDIA",
    "MEDIO": "MEDIA",
    "ALTA": "ALTA",
    "ALTO": "ALTA",
}

SOURCE_TAG = "BOE-A-2022-7191 Anexo II"


# ── Parser: header dimensiones ────────────────────────────────────────

DIM_HEADER_RE = re.compile(
    r"dimensiones\s+(?P<dims>.+?)\s+(?:categoría|nivel)\s+"
    r"(?:BÁSICA|BAJO)\s+(?:MEDIA|MEDIO)\s+(?:ALTA|ALTO)",
    re.IGNORECASE,
)

REFUERZO_HEADER_RE = re.compile(
    r"Refuerzo\s+R(?P<level>\d+)\s*[-–]\s*(?P<title>[^\n.]+?)\s*[.\n]",
    re.IGNORECASE,
)

# Sección "Aplicación de la medida" — fuente canónica de categorías.
# Boundary: newline (NO punto · el measure_code contiene puntos: 'mp.com.2').
APPLICATION_LINE_RE = re.compile(
    r"(?:Categoría|Nivel)\s+(?P<cat>BÁSICA|BASICA|BAJO|MEDIA|MEDIO|ALTA|ALTO)\s*:\s*"
    r"(?P<rest>[^\n]+)",
    re.IGNORECASE,
)


def extract_dimensions(dims_text: str) -> list[str]:
    """Convierte 'Todas' o 'C I T A' en lista canónica CIDAT."""
    text = dims_text.strip()
    if "todas" in text.lower():
        return list(CIDAT_DIMENSIONS)
    found: list[str] = []
    seen: set[str] = set()
    for token in text.replace("\n", " ").split():
        upper = token.upper()
        if upper in CIDAT_DIMENSIONS and upper not in seen:
            seen.add(upper)
            found.append(upper)
    return found


def extract_refuerzos_from_application(rest: str) -> tuple[bool, list[int]]:
    """Parsea el lado derecho de 'Categoría X: <medida> + R1 + R2.'.

    Returns:
        (applies, [refuerzo_levels])

    Casos:
        '<medida>'                  → (True, [])     # base solo
        '<medida> + R1'             → (True, [1])
        '<medida> + R1 + R2 + R3'   → (True, [1, 2, 3])
        'n.a.'                      → (False, [])
        'no aplica'                 → (False, [])
        '+ [R1 o R2 o R3]'          → (True, [1, 2, 3]) marcado optional via metadata
    """
    text = rest.strip().lower()
    if not text or text in {"n.a.", "no aplica", "n/a"}:
        return (False, [])

    refuerzos: list[int] = []
    # Capturar todos los R\d+ (incluyendo dentro de [ ])
    for m in re.finditer(r"r(\d+)", text):
        try:
            level = int(m.group(1))
            if 1 <= level <= 9 and level not in refuerzos:
                refuerzos.append(level)
        except ValueError:
            continue

    return (True, refuerzos)


def extract_refuerzo_titles(content: str) -> dict[int, str]:
    """Devuelve {nivel_int: título_canónico} desde headers ``Refuerzo R{N}-{título}.``."""
    titles: dict[int, str] = {}
    for m in REFUERZO_HEADER_RE.finditer(content):
        try:
            level = int(m.group("level"))
        except ValueError:
            continue
        if level > 9:
            continue  # Anexo II oficial no tiene R10+
        title = m.group("title").strip()
        if level not in titles and title:
            titles[level] = title
    return titles


def parse_chunk(measure_code: str, content: str) -> dict[str, Any]:
    """Parsea un chunk del Anexo II en estructura normalizada.

    Returns dict con keys:
        measure_code      : str
        dimensions        : list[str] CIDAT
        categories        : dict[str, dict] · "BASICA"/"MEDIA"/"ALTA" →
                            {"applies": bool, "refuerzos": list[int]}
        refuerzo_titles   : dict[int, str]
    """
    out: dict[str, Any] = {
        "measure_code": measure_code,
        "dimensions": [],
        "categories": {"BASICA": None, "MEDIA": None, "ALTA": None},
        "refuerzo_titles": {},
    }

    # Dimensiones
    dim_match = DIM_HEADER_RE.search(content)
    if dim_match:
        out["dimensions"] = extract_dimensions(dim_match.group("dims"))

    # Categorías desde "Aplicación de la medida"
    for m in APPLICATION_LINE_RE.finditer(content):
        cat_raw = m.group("cat").upper().replace("Á", "A")
        cat_norm = CATEGORY_MAP.get(cat_raw)
        if not cat_norm:
            continue
        applies, refuerzos = extract_refuerzos_from_application(m.group("rest"))
        out["categories"][cat_norm] = {
            "applies": applies,
            "refuerzos": refuerzos,
        }

    # Refuerzo titles
    out["refuerzo_titles"] = extract_refuerzo_titles(content)
    return out


# ── Seed builder ──────────────────────────────────────────────────────


def build_refuerzo_rows(
    parsed: dict[str, Any], chunk_id: str
) -> list[tuple[str, str, dict, str, str, dict]]:
    """Genera filas para ``ens_measure_refuerzos``.

    Una fila por cada nivel de refuerzo declarado en headers Refuerzo R{N}.
    ``applicable_categories`` indica en qué categorías está requerido.
    """
    measure_code = parsed["measure_code"]
    titles = parsed["refuerzo_titles"]

    rows: list[tuple[str, str, dict, str, str, dict]] = []
    for level in sorted(titles.keys()):
        applicable: dict[str, str] = {}
        for cat_name, cat_data in parsed["categories"].items():
            if cat_data is None or not cat_data["applies"]:
                continue
            if level in cat_data["refuerzos"]:
                applicable[cat_name] = "required"

        description = titles.get(level, "").strip()
        refuerzo_level = f"+R{level}"
        metadata = {"source": SOURCE_TAG, "parser": "seed_ens_measure_refuerzos.py"}
        rows.append(
            (
                measure_code,
                refuerzo_level,
                applicable,
                description,
                chunk_id,
                metadata,
            )
        )
    return rows


def build_dimension_rows(parsed: dict[str, Any]) -> list[tuple[str, None, str]]:
    """Genera filas para ``ens_measure_dimensiones`` (medida base solo).

    Refuerzos heredan dimensiones de medida base por defecto. Si un refuerzo
    declara dimensiones distintas (caso raro · ej. mp.info.3 R1), se podría
    extender con filas refuerzo_level='+RN' aquí · por ahora medida-base.
    """
    return [(parsed["measure_code"], None, dim) for dim in parsed["dimensions"]]


# ── Main ──────────────────────────────────────────────────────────────


def _delete_existing_seed(cur: Any) -> None:
    """Borra filas previas del mismo source para garantizar idempotencia."""
    cur.execute(
        "DELETE FROM ens_measure_refuerzos WHERE metadata ->> 'source' = %s",
        (SOURCE_TAG,),
    )
    cur.execute(
        "DELETE FROM ens_measure_dimensiones WHERE metadata ->> 'source' = %s",
        (SOURCE_TAG,),
    )


def main() -> int:
    with psycopg2.connect(DATABASE_URL) as conn:
        conn.autocommit = False

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, measure_code, content
                FROM knowledge_chunks
                WHERE document_id = %s
                  AND measure_code IS NOT NULL
                ORDER BY measure_code
                """,
                (RD_311_DOC_ID,),
            )
            chunks = cur.fetchall()

        if not chunks:
            print(
                "ERROR: 0 chunks RD 311/2022 con measure_code en BD. "
                "El corpus no está ingerido. Abortando.",
                file=sys.stderr,
            )
            return 1

        refuerzos_inserted = 0
        dimensions_inserted = 0
        measures_with_refuerzos = 0
        measures_with_dims = 0

        with conn.cursor() as cur:
            _delete_existing_seed(cur)

            for chunk_id, measure_code, content in chunks:
                parsed = parse_chunk(measure_code, content or "")

                refuerzo_rows = build_refuerzo_rows(parsed, chunk_id)
                if refuerzo_rows:
                    measures_with_refuerzos += 1
                for row in refuerzo_rows:
                    cur.execute(
                        """
                        INSERT INTO ens_measure_refuerzos
                            (measure_code, refuerzo_level, applicable_categories,
                             description, source_chunk_id, metadata)
                        VALUES (%s, %s, %s::jsonb, %s, %s, %s::jsonb)
                        """,
                        (
                            row[0],
                            row[1],
                            json.dumps(row[2]),
                            row[3],
                            row[4],
                            json.dumps(row[5]),
                        ),
                    )
                    refuerzos_inserted += 1

                dim_rows = build_dimension_rows(parsed)
                if dim_rows:
                    measures_with_dims += 1
                for measure, level, dim in dim_rows:
                    cur.execute(
                        """
                        INSERT INTO ens_measure_dimensiones
                            (measure_code, refuerzo_level, dimension, metadata)
                        VALUES (%s, %s, %s, %s::jsonb)
                        """,
                        (
                            measure,
                            level,
                            dim,
                            json.dumps({"source": SOURCE_TAG}),
                        ),
                    )
                    dimensions_inserted += 1

        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM ens_measure_refuerzos")
            total_refuerzos = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM ens_measure_dimensiones")
            total_dims = cur.fetchone()[0]

    print(
        f"Seed OK · {measures_with_refuerzos} medidas con refuerzos · "
        f"{refuerzos_inserted} filas refuerzos · "
        f"{measures_with_dims} medidas con dimensiones · "
        f"{dimensions_inserted} filas dimensiones. "
        f"Totales BD: {total_refuerzos} refuerzos · {total_dims} dimensiones."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
