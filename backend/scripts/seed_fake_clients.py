"""Seed 3 fake clients (Básica / Media / Alta) with one project each.

Idempotent:
- Deletes previously-seeded rows (``lead_source='seed'``) together with
  their projects/evidence so a re-run produces a deterministic state
  matching the current ``CLIENTES`` data.
- All CIFs are valid per the Spanish algorithm for CIF (letter + 7 digits
  + check character).

Run:
    PYTHONPATH=. python backend/scripts/seed_fake_clients.py
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://fulkro:changeme@localhost:5433/fulkro",
)


def compute_cif_check(prefix: str, digits: str) -> str:
    """Compute the last character of a Spanish CIF.

    ``prefix`` is the single-letter first character (A/B/C/...).
    ``digits`` is the 7-digit middle section.
    Returns the check character (a digit or a letter from ``JABCDEFGHI``
    depending on the organisation type).
    """
    assert len(digits) == 7 and digits.isdigit()
    odd_sum = sum(int(digits[i]) for i in (0, 2, 4, 6))
    even_sum = 0
    for i in (1, 3, 5):
        d = int(digits[i]) * 2
        even_sum += (d // 10) + (d % 10)
    total = (odd_sum + even_sum) % 10
    check_digit = (10 - total) % 10
    LETTER_ONLY = set("NPQRSW")
    if prefix in LETTER_ONLY:
        return "JABCDEFGHI"[check_digit]
    return str(check_digit)


def build_cif(prefix: str, digits: str) -> str:
    return f"{prefix}{digits}{compute_cif_check(prefix, digits)}"


CLIENTES = [
    {
        "nombre": "MicroServicios del Sur SL",
        "cif": build_cif("B", "4185029"),  # SL (Sociedad Limitada)
        "sector": "servicios",
        "provincia": "Sevilla",
        "numero_empleados": 18,
        "email": "ceo@microservicios-sur.es",
        "categoria_objetivo": "B",
        "proyecto": "Certificación ENS Básica — 2026",
        "fase": "diagnostico",
    },
    {
        "nombre": "DataForma Galicia SL",
        "cif": build_cif("B", "7263481"),
        "sector": "salud",
        "provincia": "A Coruña",
        "numero_empleados": 85,
        "email": "direccion@dataforma.es",
        "categoria_objetivo": "M",
        "proyecto": "Certificación ENS Media — 2026",
        "fase": "implantacion",
    },
    {
        "nombre": "InfraCrítica Iberia SA",
        "cif": build_cif("A", "5193824"),  # SA (Sociedad Anónima)
        "sector": "financiero",
        "provincia": "Madrid",
        "numero_empleados": 420,
        "email": "ciso@infracritica.es",
        "categoria_objetivo": "A",
        "proyecto": "Certificación ENS Alta — 2026",
        "fase": "verificacion",
    },
]


def _purge_previous(cur) -> None:
    cur.execute(
        """
        DELETE FROM evidence
        WHERE project_id IN (
            SELECT p.id FROM projects p
            JOIN clients c ON c.id = p.client_id
            WHERE c.lead_source = 'seed'
        )
        """
    )
    cur.execute(
        """
        DELETE FROM projects
        WHERE client_id IN (SELECT id FROM clients WHERE lead_source = 'seed')
        """
    )
    cur.execute("DELETE FROM clients WHERE lead_source = 'seed'")


def main() -> int:
    today = date.today()
    with psycopg2.connect(DATABASE_URL) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            _purge_previous(cur)

            inserted_clients = 0
            inserted_projects = 0
            for c in CLIENTES:
                cur.execute(
                    """
                    INSERT INTO clients (
                        nombre, cif, sector, provincia, numero_empleados,
                        contacto_email, lead_source
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 'seed')
                    RETURNING id
                    """,
                    (
                        c["nombre"], c["cif"], c["sector"],
                        c["provincia"], c["numero_empleados"], c["email"],
                    ),
                )
                client_id = cur.fetchone()[0]
                inserted_clients += 1

                cur.execute(
                    """
                    INSERT INTO projects (
                        client_id, nombre, fase, categoria_objetivo,
                        fecha_kickoff, fecha_objetivo_certificacion,
                        estado, lifecycle_state
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'ACTIVO', 'ACTIVE')
                    """,
                    (
                        client_id, c["proyecto"], c["fase"], c["categoria_objetivo"],
                        today - timedelta(days=14),
                        today + timedelta(weeks=12),
                    ),
                )
                inserted_projects += 1
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM clients WHERE lead_source = 'seed'")
            total_clients = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM projects WHERE client_id IN "
                "(SELECT id FROM clients WHERE lead_source = 'seed')"
            )
            total_projects = cur.fetchone()[0]

    print(
        f"Seeded {inserted_clients} clients + {inserted_projects} projects. "
        f"Seed totals: {total_clients} clients / {total_projects} projects."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
