"""Seed ``ens_measure_guias_ccn`` with curated Medida→CCN-STIC mappings.

Curated from CCN-STIC series 800 scope and ENS Anexo II family semantics:
- 800 Glosario: reference-only (not attached to medidas; covered via lookups)
- 801 Responsabilidades y Funciones → org.*
- 802 Auditoría ENS → medidas verificables (op.exp.9, op.mon.*, mp.s.*, org.*)
- 803 Valoración de Sistemas → informational (Anexo I)
- 804 Guía de Implantación ENS → TODAS las 73 medidas (general)
- 805 Política de Seguridad → org.1, org.2
- 806 Plan de Adecuación → TODAS las 73 medidas (planning)
- 807 Criptología → mp.info.3, mp.info.4, mp.si.2, mp.com.2, mp.com.3, op.acc.5, op.acc.6
- 808 Verificación del Cumplimiento → TODAS las 73 medidas (audit-ready)

Relevance labels: ``develops`` (la guía desarrolla la medida), ``verifies``
(la guía define cómo verificarla), ``references`` (mención indirecta).

Run:
    PYTHONPATH=. python backend/scripts/seed_ens_measure_guias.py
"""
from __future__ import annotations

import os
import sys

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://fulkro:changeme@localhost:5433/fulkro",
)

# (guia_code, relevance, section_ref)
SPECIFIC_MAPPINGS: dict[str, list[tuple[str, str, str]]] = {
    # Family: org.* (Marco Organizativo)
    "org.1": [("CCN_STIC_805", "develops", "Cap. 2"), ("CCN_STIC_801", "references", "Sec. 2.1")],
    "org.2": [("CCN_STIC_805", "develops", "Cap. 3"), ("CCN_STIC_801", "develops", "Sec. 2.2")],
    "org.3": [("CCN_STIC_801", "develops", "Sec. 3"), ("CCN_STIC_806", "develops", "Anexo B")],
    "org.4": [("CCN_STIC_801", "develops", "Sec. 4")],
    # Family: op.acc.* (Control de Acceso)
    "op.acc.1": [("CCN_STIC_807", "references", "Cap. 4")],
    "op.acc.2": [("CCN_STIC_807", "references", "Cap. 4")],
    "op.acc.3": [("CCN_STIC_807", "references", "Cap. 4")],
    "op.acc.4": [("CCN_STIC_807", "references", "Cap. 4")],
    "op.acc.5": [("CCN_STIC_807", "develops", "Cap. 4.2")],
    "op.acc.6": [("CCN_STIC_807", "develops", "Cap. 4.3"), ("CCN_STIC_808", "verifies", "Sec. 5.3")],
    # O1 · "op.acc.7" NO EXISTE (op.acc llega a op.acc.6). Su mapeo a
    # CCN-STIC 808 Sec. 5.3 ya lo tiene op.acc.6, justo encima.
    # Family: op.exp.* (Explotación)
    "op.exp.1": [("CCN_STIC_808", "verifies", "Sec. 5.4")],
    "op.exp.2": [("CCN_STIC_808", "verifies", "Sec. 5.4")],
    "op.exp.3": [("CCN_STIC_808", "verifies", "Sec. 5.4")],
    "op.exp.4": [("CCN_STIC_808", "verifies", "Sec. 5.4")],
    "op.exp.5": [("CCN_STIC_808", "verifies", "Sec. 5.4")],
    "op.exp.6": [("CCN_STIC_808", "verifies", "Sec. 5.4")],
    "op.exp.7": [("CCN_STIC_808", "verifies", "Sec. 5.4"), ("CCN_STIC_802", "develops", "Cap. 3")],
    "op.exp.8": [("CCN_STIC_808", "verifies", "Sec. 5.4"), ("CCN_STIC_802", "develops", "Cap. 3.2")],
    "op.exp.9": [("CCN_STIC_802", "develops", "Cap. 4"), ("CCN_STIC_808", "verifies", "Sec. 5.4")],
    "op.exp.10": [("CCN_STIC_808", "verifies", "Sec. 5.4")],
    # REMOVED FASE 9.0 Sub-bloque 0.A Fase 1: op.exp.11 era v2017 obsoleta (no existe en RD 311/2022)
    # Family: op.mon.* (Monitorización)
    "op.mon.1": [("CCN_STIC_802", "references", "Cap. 3"), ("CCN_STIC_808", "verifies", "Sec. 5.5")],
    "op.mon.2": [("CCN_STIC_802", "develops", "Cap. 3"), ("CCN_STIC_808", "verifies", "Sec. 5.5")],
    "op.mon.3": [("CCN_STIC_808", "verifies", "Sec. 5.5")],
    # Family: mp.info.* (Protección de la Información)
    "mp.info.1": [("CCN_STIC_808", "verifies", "Sec. 5.8")],
    "mp.info.2": [("CCN_STIC_808", "verifies", "Sec. 5.8")],
    "mp.info.3": [("CCN_STIC_807", "develops", "Cap. 2"), ("CCN_STIC_808", "verifies", "Sec. 5.8")],
    "mp.info.4": [("CCN_STIC_807", "develops", "Cap. 3"), ("CCN_STIC_808", "verifies", "Sec. 5.8")],
    "mp.info.5": [("CCN_STIC_808", "verifies", "Sec. 5.8")],
    "mp.info.6": [("CCN_STIC_808", "verifies", "Sec. 5.8")],
    # Family: mp.com.* (Protección de las Comunicaciones)
    "mp.com.1": [("CCN_STIC_808", "verifies", "Sec. 5.7")],
    "mp.com.2": [("CCN_STIC_807", "develops", "Cap. 5"), ("CCN_STIC_808", "verifies", "Sec. 5.7")],
    "mp.com.3": [("CCN_STIC_807", "develops", "Cap. 5"), ("CCN_STIC_808", "verifies", "Sec. 5.7")],
    # Family: mp.si.* (Soportes de Información)
    "mp.si.1": [("CCN_STIC_808", "verifies", "Sec. 5.8")],
    "mp.si.2": [("CCN_STIC_807", "develops", "Cap. 2"), ("CCN_STIC_808", "verifies", "Sec. 5.8")],
    "mp.si.3": [("CCN_STIC_808", "verifies", "Sec. 5.8")],
    "mp.si.4": [("CCN_STIC_808", "verifies", "Sec. 5.8")],
    "mp.si.5": [("CCN_STIC_808", "verifies", "Sec. 5.8")],
    # Family: mp.s.* (Servicios)
    "mp.s.1": [("CCN_STIC_802", "references", "Cap. 3"), ("CCN_STIC_808", "verifies", "Sec. 5.9")],
    "mp.s.2": [("CCN_STIC_808", "verifies", "Sec. 5.9")],
    "mp.s.3": [("CCN_STIC_802", "develops", "Cap. 3"), ("CCN_STIC_808", "verifies", "Sec. 5.9")],
    "mp.s.4": [("CCN_STIC_808", "verifies", "Sec. 5.9")],
}

UNIVERSAL_GUIDES: list[tuple[str, str, str]] = [
    ("CCN_STIC_804", "develops", "Implantación"),
    ("CCN_STIC_806", "develops", "Plan"),
    ("CCN_STIC_808", "verifies", "General"),
]


def main() -> int:
    with psycopg2.connect(DATABASE_URL) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SELECT codigo FROM ens_measures ORDER BY codigo")
            all_codes = [row[0].lower() for row in cur.fetchall()]

            inserted = 0
            for codigo in all_codes:
                rows = list(SPECIFIC_MAPPINGS.get(codigo, []))
                for guia_code, relevance, section in UNIVERSAL_GUIDES:
                    if all(g != guia_code for g, _, _ in rows):
                        rows.append((guia_code, relevance, section))
                for guia_code, relevance, section in rows:
                    cur.execute(
                        """
                        INSERT INTO ens_measure_guias_ccn
                            (measure_code, guia_code, relevance, section_ref, metadata)
                        VALUES (%s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (measure_code, guia_code, section_ref) DO NOTHING
                        """,
                        (codigo, guia_code, relevance, section, "{}"),
                    )
                    inserted += cur.rowcount
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM ens_measure_guias_ccn")
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(DISTINCT measure_code), COUNT(DISTINCT guia_code) "
                "FROM ens_measure_guias_ccn"
            )
            distinct_m, distinct_g = cur.fetchone()

    print(
        f"Seeded {inserted} new rows in ens_measure_guias_ccn. "
        f"Total: {total} · distinct medidas={distinct_m} · distinct guias={distinct_g}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
