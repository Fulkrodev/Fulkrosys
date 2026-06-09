"""Seed ``ens_measure_evidencia_types`` with one row per ENS medida.

Sources:
- ``backend/app/motors/m07_evidence/catalog/evidence_types.json`` provides
  12 high-quality evidence type definitions pre-mapped to 20 measures.
- For the remaining measures we generate a generic-but-plausible entry
  based on the ENS family (org, op.acc, op.exp, mp.info, …).

End state: at least one row per medida (73 rows minimum, 100+ after
fan-out of the JSON mappings). Idempotent via
``ON CONFLICT (measure_code, evidence_type) DO UPDATE`` on the unique
constraint.

Every row has: measure_code, evidence_type, description,
freshness_days, applicable_categories, is_mandatory, format,
source_tool, automatable, audit_query.

Run:
    PYTHONPATH=. python backend/scripts/seed_ens_evidence_catalog.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://fulkro:changeme@localhost:5433/fulkro",
)

ROOT = Path(__file__).resolve().parents[2]
CATALOG_JSON = ROOT / "backend/app/motors/m07_evidence/catalog/evidence_types.json"


# Family → (source_tool, default format, generic type slug, audit prompt template)
FAMILIAS: dict[str, dict[str, str]] = {
    "org": {
        "source_tool": "Gestor documental del cliente",
        "format": "PDF firmado + control de versiones",
        "type": "documento_gobernanza",
        "automatable": False,
        "query": (
            "¿Puede mostrar el documento formalmente aprobado de la medida "
            "{codigo} ({nombre}), con firma del órgano competente y control "
            "de versiones vigentes?"
        ),
    },
    "op.pl": {
        "source_tool": "Herramientas internas de planificación",
        "format": "PDF firmado + hojas de cálculo fuente",
        "type": "planificacion",
        "automatable": False,
        "query": (
            "¿Puede mostrar la planificación/análisis que soporta la medida "
            "{codigo} ({nombre}) y la trazabilidad de las decisiones tomadas?"
        ),
    },
    "op.acc": {
        "source_tool": "IdP, gestor de identidades, AD/LDAP",
        "format": "Captura PNG + export CSV de políticas",
        "type": "configuracion_acceso",
        "automatable": True,
        "query": (
            "¿Puede mostrar la política activa y la cobertura real (usuarios, "
            "aplicaciones) de {codigo} ({nombre}) en el periodo auditado?"
        ),
    },
    "op.exp": {
        "source_tool": "SIEM / EDR / gestor de parches",
        "format": "Export CSV/JSON + capturas de configuración",
        "type": "registro_operacional",
        "automatable": True,
        "query": (
            "¿Puede aportar los registros (logs, métricas, tickets) que "
            "soportan la aplicación efectiva de {codigo} ({nombre})?"
        ),
    },
    "op.ext": {
        "source_tool": "Registro de proveedores + contratos",
        "format": "PDF del contrato + SLA firmado",
        "type": "contrato_externo",
        "automatable": False,
        "query": (
            "¿Puede aportar el contrato y las cláusulas ENS/RGPD del "
            "proveedor/servicio relativo a {codigo} ({nombre})?"
        ),
    },
    "op.nub": {
        "source_tool": "Consola del proveedor cloud + CASB",
        "format": "Export de configuración + informe SOC 2 del proveedor",
        "type": "configuracion_cloud",
        "automatable": True,
        "query": (
            "¿Puede mostrar la configuración securizada y el informe de "
            "conformidad del proveedor cloud para la medida {codigo}?"
        ),
    },
    "op.cont": {
        "source_tool": "Plan de continuidad + informes de prueba",
        "format": "Informe de prueba firmado + vídeo/capturas de ejecución",
        "type": "prueba_continuidad",
        "automatable": False,
        "query": (
            "¿Puede mostrar el informe de la última prueba de continuidad "
            "que soporta la medida {codigo} ({nombre}), con RTO/RPO medidos?"
        ),
    },
    "op.mon": {
        "source_tool": "SIEM + sistema de ticketing",
        "format": "Dashboard + export de alertas + métricas semanales",
        "type": "monitorizacion",
        "automatable": True,
        "query": (
            "¿Puede mostrar la cobertura del sistema de monitorización "
            "respecto a {codigo} ({nombre}), los KPIs del periodo y el "
            "tratamiento de las alertas generadas?"
        ),
    },
    "mp.if": {
        "source_tool": "Sistema de control de acceso físico + CCTV",
        "format": "Logs de acceso + fotografías + plano de instalación",
        "type": "seguridad_fisica",
        "automatable": True,
        "query": (
            "¿Puede aportar los registros de control de acceso físico y las "
            "evidencias físicas que soportan la medida {codigo} ({nombre})?"
        ),
    },
    "mp.per": {
        "source_tool": "Portal de formación + registro de asistencia",
        "format": "Registro firmado + certificados de formación",
        "type": "formacion_personal",
        "automatable": True,
        "query": (
            "¿Puede aportar el registro de formación/concienciación del "
            "personal con cobertura y resultado asociado a {codigo}?"
        ),
    },
    "mp.eq": {
        "source_tool": "Inventario + EDR + sistema de despliegue",
        "format": "Export del inventario + hardening baseline",
        "type": "configuracion_equipo",
        "automatable": True,
        "query": (
            "¿Puede mostrar la configuración hardened de los equipos "
            "afectados por {codigo} ({nombre}) y su cobertura real?"
        ),
    },
    "mp.com": {
        "source_tool": "Firewall + NAC + inspección TLS",
        "format": "Export de reglas + informe de testssl/analizador",
        "type": "configuracion_red",
        "automatable": True,
        "query": (
            "¿Puede aportar la configuración de red (reglas, segmentación, "
            "cifrado) que implementa {codigo} y su verificación técnica?"
        ),
    },
    "mp.si": {
        "source_tool": "Cifrado de discos + KMS + gestor de soportes",
        "format": "Export KMS + inventario de soportes + política de borrado",
        "type": "proteccion_soporte",
        "automatable": True,
        "query": (
            "¿Puede mostrar la protección (cifrado, retirada, destrucción) "
            "de los soportes de información para {codigo}?"
        ),
    },
    "mp.sw": {
        "source_tool": "Repositorio código + SAST/SCA + pipelines CI/CD",
        "format": "Informe SAST + informe SCA + evidencia del pipeline",
        "type": "desarrollo_seguro",
        "automatable": True,
        "query": (
            "¿Puede mostrar el cumplimiento del ciclo de desarrollo seguro "
            "(SAST, SCA, aprobación) asociado a la medida {codigo}?"
        ),
    },
    "mp.info": {
        "source_tool": "KMS + sello de tiempo cualificado + DLP",
        "format": "Export claves + registros de firma + informe DLP",
        "type": "proteccion_informacion",
        "automatable": True,
        "query": (
            "¿Puede aportar la evidencia de cifrado, firma y sellado de "
            "tiempo asociada a {codigo} ({nombre})?"
        ),
    },
    "mp.s": {
        "source_tool": "WAF + anti-DDoS + gestor de correo",
        "format": "Export de configuración + informes de bloqueo",
        "type": "proteccion_servicios",
        "automatable": True,
        "query": (
            "¿Puede mostrar la protección efectiva del servicio frente a "
            "las amenazas cubiertas por {codigo}?"
        ),
    },
}


def _family_for(codigo: str) -> str:
    if codigo.startswith("org."):
        return "org"
    # mp.info comes before mp.i
    for prefix in ("op.acc", "op.exp", "op.ext", "op.nub", "op.cont",
                   "op.mon", "op.pl", "mp.info", "mp.if", "mp.per",
                   "mp.eq", "mp.com", "mp.si", "mp.sw", "mp.s"):
        if codigo.startswith(f"{prefix}."):
            return prefix
    return "org"


def _generic_type_for(codigo: str, nombre: str) -> dict:
    fam = _family_for(codigo)
    meta = FAMILIAS[fam]
    return {
        "evidence_type": meta["type"],
        "description": (
            f"Evidencia documental y técnica de implantación efectiva de la "
            f"medida {codigo} ({nombre}) del Anexo II del RD 311/2022, con "
            f"trazabilidad al periodo auditado."
        ),
        "freshness_days": 365,
        "applicable_categories": ["BASICA", "MEDIA", "ALTA"],
        "is_mandatory": True,
        "format": meta["format"],
        "source_tool": meta["source_tool"],
        "automatable": bool(meta.get("automatable", False)),
        "audit_query": meta["query"].format(codigo=codigo, nombre=nombre),
    }


def _from_json_entry(t: dict, measure_code: str, nombre: str) -> dict:
    """Adapt a ``m07_evidence/catalog/evidence_types.json`` entry."""
    is_mandatory = bool(t.get("obligatorio", True))
    fam = _family_for(measure_code)
    meta = FAMILIAS[fam]
    categoria = t.get("categoria", "").lower() or meta["type"]
    mime = t.get("mime_types_permitidos") or []
    ext = t.get("extensiones_permitidas") or []
    fmt_parts: list[str] = []
    if mime:
        fmt_parts.append("/".join(m.split("/")[-1] for m in mime))
    if ext:
        fmt_parts.append("ext. " + ",".join(ext))
    fmt = " · ".join(fmt_parts) or meta["format"]
    return {
        "evidence_type": categoria,
        "description": t.get("descripcion") or f"Evidencia para {measure_code}",
        "freshness_days": int(t.get("caducidad_dias") or 365),
        "applicable_categories": ["BASICA", "MEDIA", "ALTA"],
        "is_mandatory": is_mandatory,
        "format": fmt,
        "source_tool": meta["source_tool"],
        "automatable": bool(meta.get("automatable", False)),
        "audit_query": meta["query"].format(codigo=measure_code, nombre=nombre),
    }


def main() -> int:
    with psycopg2.connect(DATABASE_URL) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(
                "SELECT codigo, nombre FROM ens_measures "
                "WHERE deleted_at IS NULL ORDER BY codigo"
            )
            medidas = [(r[0], r[1]) for r in cur.fetchall()]
        assert len(medidas) >= 73, f"expected ≥73 medidas, got {len(medidas)}"

        json_data = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
        json_types = json_data.get("types", [])

        inserted = 0
        updated = 0

        with conn.cursor() as cur:
            # Primero, insertar por medida un entry genérico (cobertura
            # universal), para garantizar que las 73 están cubiertas.
            for codigo, nombre in medidas:
                row = _generic_type_for(codigo, nombre)
                cur.execute(
                    """
                    INSERT INTO ens_measure_evidencia_types
                        (measure_code, evidence_type, description,
                         freshness_days, applicable_categories, is_mandatory,
                         format, source_tool, automatable, audit_query)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                    ON CONFLICT (measure_code, evidence_type)
                    DO UPDATE SET
                        description = EXCLUDED.description,
                        freshness_days = EXCLUDED.freshness_days,
                        applicable_categories = EXCLUDED.applicable_categories,
                        is_mandatory = EXCLUDED.is_mandatory,
                        format = EXCLUDED.format,
                        source_tool = EXCLUDED.source_tool,
                        automatable = EXCLUDED.automatable,
                        audit_query = EXCLUDED.audit_query
                    RETURNING (xmax = 0) AS was_insert
                    """,
                    (
                        codigo, row["evidence_type"], row["description"],
                        row["freshness_days"],
                        json.dumps(row["applicable_categories"]),
                        row["is_mandatory"], row["format"],
                        row["source_tool"], row["automatable"],
                        row["audit_query"],
                    ),
                )
                was_insert = cur.fetchone()[0]
                if was_insert:
                    inserted += 1
                else:
                    updated += 1

            # Segundo, añadir los 12 entries ricos del JSON para las
            # medidas que los tengan asociados (pueden coexistir con el
            # genérico gracias al UNIQUE(measure_code, evidence_type)).
            codigo_to_nombre = dict(medidas)
            for t in json_types:
                for codigo in t.get("medidas_asociadas", []):
                    if codigo not in codigo_to_nombre:
                        continue
                    row = _from_json_entry(t, codigo, codigo_to_nombre[codigo])
                    cur.execute(
                        """
                        INSERT INTO ens_measure_evidencia_types
                            (measure_code, evidence_type, description,
                             freshness_days, applicable_categories, is_mandatory,
                             format, source_tool, automatable, audit_query)
                        VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                        ON CONFLICT (measure_code, evidence_type)
                        DO UPDATE SET
                            description = EXCLUDED.description,
                            freshness_days = EXCLUDED.freshness_days,
                            applicable_categories = EXCLUDED.applicable_categories,
                            is_mandatory = EXCLUDED.is_mandatory,
                            format = EXCLUDED.format,
                            source_tool = EXCLUDED.source_tool,
                            automatable = EXCLUDED.automatable,
                            audit_query = EXCLUDED.audit_query
                        RETURNING (xmax = 0)
                        """,
                        (
                            codigo, row["evidence_type"], row["description"],
                            row["freshness_days"],
                            json.dumps(row["applicable_categories"]),
                            row["is_mandatory"], row["format"],
                            row["source_tool"], row["automatable"],
                            row["audit_query"],
                        ),
                    )
                    if cur.fetchone()[0]:
                        inserted += 1
                    else:
                        updated += 1
        conn.commit()

        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) total, COUNT(DISTINCT measure_code) medidas "
                "FROM ens_measure_evidencia_types"
            )
            total, medidas_cov = cur.fetchone()
    print(
        f"inserted {inserted} · updated {updated} · "
        f"total rows {total} covering {medidas_cov} medidas"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
