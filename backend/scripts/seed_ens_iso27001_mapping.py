"""Seed ``ens_iso27001_mapping`` canónico CCN-STIC 825.

Mapeo curado entre las 73 medidas ENS RD 311/2022 Anexo II y los
controles ISO 27001:2022 Anexo A. Tipos:

* ``exact``      · cobertura ≥ 95% · medida ENS satisfecha por control ISO directo
* ``partial``    · cobertura 50-94% · control ISO cubre parte de la medida
* ``conceptual`` · cobertura < 50% · solapamiento parcial de intent

Idempotente vía ``ON CONFLICT DO NOTHING`` (uq_ens_iso_mapping_pair).

Run::

    PYTHONPATH=. python backend/scripts/seed_ens_iso27001_mapping.py

Refs: SAN-C.MB-10.7 · CCN-STIC 825
"""
from __future__ import annotations

import os
import sys

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://fulkro_app:fulkro_app_dev_password@localhost:5433/fulkro",
)


# (ens_measure_code, iso27001_control, mapping_type, coverage_percent, notes)
_MAPPINGS: list[tuple[str, str, str, int, str]] = [
    # ── Marco organizativo [org] ──
    ("org.1", "A.5.1", "exact", 100, "Política seguridad información"),
    ("org.1", "A.5.2", "exact", 95, "Roles y responsabilidades"),
    ("org.2", "A.5.1", "partial", 80, "Normativa seguridad · ISO usa political documents"),
    ("org.3", "A.5.37", "partial", 80, "Procedimientos operativos documentados"),
    ("org.4", "A.5.1", "partial", 70, "Proceso autorización vinculado a política"),

    # ── Marco operacional · planificación [op.pl] ──
    ("op.pl.1", "A.5.31", "partial", 75, "Análisis riesgos · ISO cláusula 6.1.2"),
    ("op.pl.2", "A.5.7", "partial", 70, "Arquitectura seguridad · ISO threat intel + design"),
    ("op.pl.3", "A.5.21", "partial", 80, "Adquisición + cadena suministro"),
    ("op.pl.4", "A.5.7", "conceptual", 50, "Dimensionamiento · ISO no controla específico"),
    ("op.pl.5", "A.5.21", "partial", 70, "Componentes certificados CPSTIC vs cadena suministro"),

    # ── Control acceso [op.acc] ──
    ("op.acc.1", "A.5.16", "exact", 95, "Identificación usuarios"),
    ("op.acc.2", "A.5.18", "exact", 95, "Gestión derechos acceso"),
    ("op.acc.3", "A.5.18", "partial", 80, "Segregación funciones"),
    ("op.acc.4", "A.5.17", "exact", 95, "Información autenticación secreta"),
    ("op.acc.5", "A.8.5", "exact", 100, "Autenticación segura"),
    ("op.acc.6", "A.8.5", "partial", 85, "Autenticación adicional · ISO MFA"),

    # ── Explotación [op.exp] ──
    ("op.exp.1", "A.8.9", "exact", 100, "Gestión configuración"),
    ("op.exp.2", "A.8.9", "exact", 100, "Configuración seguridad"),
    ("op.exp.3", "A.8.9", "exact", 100, "Gestión cambios configuración"),
    ("op.exp.4", "A.8.32", "exact", 100, "Gestión cambios"),
    ("op.exp.5", "A.8.8", "exact", 100, "Gestión vulnerabilidades técnicas"),
    ("op.exp.6", "A.8.7", "exact", 100, "Protección contra malware"),
    ("op.exp.7", "A.5.24", "exact", 100, "Planificación gestión incidentes"),
    ("op.exp.7", "A.5.25", "exact", 100, "Evaluación + decisión incidentes"),
    ("op.exp.7", "A.5.26", "exact", 100, "Respuesta incidentes"),
    ("op.exp.8", "A.8.15", "exact", 95, "Logging"),
    ("op.exp.9", "A.5.28", "exact", 90, "Recopilación evidencia"),
    ("op.exp.10", "A.8.16", "exact", 95, "Monitorización"),

    # ── Servicios externos [op.ext] ──
    ("op.ext.1", "A.5.19", "exact", 95, "Seguridad relaciones proveedores"),
    ("op.ext.2", "A.5.20", "exact", 95, "Acuerdos seguridad terceros"),
    ("op.ext.3", "A.5.21", "exact", 95, "Cadena suministro TIC"),
    ("op.ext.4", "A.5.22", "exact", 90, "Monitorización servicios proveedores"),

    # ── Cloud [op.nub] ──
    ("op.nub.1", "A.5.23", "exact", 95, "Servicios cloud"),

    # ── Continuidad [op.cont] ──
    ("op.cont.1", "A.5.30", "exact", 95, "Continuidad TIC"),
    ("op.cont.2", "A.8.13", "exact", 95, "Backup información"),
    ("op.cont.3", "A.8.14", "partial", 80, "Redundancia"),
    ("op.cont.4", "A.5.30", "exact", 90, "Pruebas continuidad"),

    # ── Monitorización [op.mon] ──
    ("op.mon.1", "A.8.16", "exact", 95, "Monitorización actividad"),
    ("op.mon.2", "A.8.16", "exact", 95, "Sistema detección intrusión"),
    ("op.mon.3", "A.8.34", "partial", 75, "Auditoría TIC"),

    # ── Marco protección · instalaciones [mp.if] ──
    ("mp.if.1", "A.7.1", "exact", 95, "Perímetro seguridad física"),
    ("mp.if.2", "A.7.2", "exact", 95, "Entradas físicas"),
    ("mp.if.3", "A.7.5", "partial", 80, "Protección contra amenazas físicas"),
    ("mp.if.4", "A.7.11", "exact", 95, "Servicios apoyo"),
    ("mp.if.5", "A.7.12", "exact", 90, "Cableado"),
    ("mp.if.6", "A.7.13", "exact", 95, "Mantenimiento equipos"),
    ("mp.if.7", "A.7.10", "exact", 95, "Soportes almacenamiento"),

    # ── Personal [mp.per] ──
    ("mp.per.1", "A.6.1", "exact", 95, "Selección personal"),
    ("mp.per.2", "A.6.2", "exact", 95, "Términos contratación"),
    ("mp.per.3", "A.6.3", "exact", 95, "Concienciación, educación, formación"),
    ("mp.per.4", "A.6.5", "partial", 80, "Responsabilidades fin contratación"),

    # ── Equipos [mp.eq] ──
    ("mp.eq.1", "A.7.7", "exact", 95, "Mesa limpia"),
    ("mp.eq.2", "A.7.9", "exact", 95, "Activos fuera instalaciones"),
    ("mp.eq.3", "A.7.14", "exact", 95, "Eliminación segura equipos"),
    ("mp.eq.4", "A.6.7", "partial", 80, "Trabajo remoto"),

    # ── Comunicaciones [mp.com] ──
    ("mp.com.1", "A.8.20", "exact", 95, "Seguridad redes"),
    ("mp.com.2", "A.8.24", "exact", 95, "Uso criptografía"),
    ("mp.com.3", "A.8.24", "exact", 95, "Integridad + autenticidad mensajes"),
    ("mp.com.4", "A.8.21", "partial", 80, "Segregación redes"),

    # ── Soportes información [mp.si] ──
    ("mp.si.1", "A.7.10", "exact", 95, "Marcado soportes"),
    ("mp.si.2", "A.8.24", "exact", 95, "Cifrado soportes"),
    ("mp.si.3", "A.7.10", "partial", 85, "Custodia soportes"),
    ("mp.si.4", "A.7.10", "partial", 80, "Transporte soportes"),
    ("mp.si.5", "A.8.10", "exact", 95, "Borrado destrucción"),

    # ── Aplicaciones [mp.sw] ──
    ("mp.sw.1", "A.8.25", "exact", 95, "Desarrollo seguro ciclo vida"),
    ("mp.sw.2", "A.8.29", "partial", 85, "Aceptación pruebas"),

    # ── Información [mp.info] ──
    ("mp.info.1", "A.5.12", "exact", 95, "Clasificación información"),
    ("mp.info.2", "A.5.13", "exact", 95, "Etiquetado información"),
    ("mp.info.3", "A.5.31", "exact", 95, "Firma electrónica + cumplimiento legal"),
    ("mp.info.4", "A.8.24", "exact", 95, "Sellos tiempo · usa criptografía"),
    ("mp.info.5", "A.5.33", "exact", 95, "Protección registros"),
    ("mp.info.6", "A.8.13", "exact", 95, "Backup información"),

    # ── Servicios [mp.s] ──
    ("mp.s.1", "A.5.7", "partial", 75, "Protección servicios · ISO threat intel"),
    ("mp.s.2", "A.5.30", "exact", 90, "Disponibilidad servicios"),
    ("mp.s.3", "A.8.6", "partial", 85, "Capacidades · capacity management"),
    ("mp.s.4", "A.5.30", "exact", 95, "Continuidad servicios"),
]


def main() -> int:
    with psycopg2.connect(DATABASE_URL) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            for ens, iso, mt, cov, notes in _MAPPINGS:
                cur.execute(
                    """
                    INSERT INTO ens_iso27001_mapping
                        (ens_measure_code, iso27001_control,
                         mapping_type, coverage_percent, notes,
                         metadata_jsonb)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (ens_measure_code, iso27001_control)
                    DO UPDATE SET
                        mapping_type = EXCLUDED.mapping_type,
                        coverage_percent = EXCLUDED.coverage_percent,
                        notes = EXCLUDED.notes,
                        metadata_jsonb = EXCLUDED.metadata_jsonb
                    """,
                    (
                        ens, iso, mt, cov, notes,
                        '{"source": "CCN-STIC-825 v1.0"}',
                    ),
                )
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM ens_iso27001_mapping")
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT count(DISTINCT ens_measure_code) FROM ens_iso27001_mapping"
            )
            unique_ens = cur.fetchone()[0]
            cur.execute(
                "SELECT count(DISTINCT iso27001_control) FROM ens_iso27001_mapping"
            )
            unique_iso = cur.fetchone()[0]

    print(
        f"Seed OK · {total} mappings · {unique_ens} medidas ENS distintas · "
        f"{unique_iso} controles ISO 27001 distintos."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
