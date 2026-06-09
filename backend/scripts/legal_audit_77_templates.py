"""Legal audit automatizado sobre los 83 templates FULKRO.

Complementa la revision manual narrativa en progress/LEGAL_AUDIT_REPORT.md
con checks estructurales sobre cada template:

1. Presencia de referencias normativas actuales (no derogadas).
2. Placeholders legal-criticos marcados required.
3. Presencia de clausulas clave por categoria (politica/procedimiento/
   comercial/entregable/registro).
4. Ausencia de referencias a leyes derogadas (LOPD 15/1999, Ley 30/1992).
5. Uso correcto de terminologia ENS vs LOPDGDD vs RGPD.

Output JSON: progress/legal_audit_autocheck.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATALOG = PROJECT_ROOT / "docs" / "catalogs" / "template_catalog_v1.yaml"
TEMPLATES_DIR = (
    PROJECT_ROOT / "backend" / "app" / "motors" / "m06_document_factory" / "templates"
)


# ══════════════════════════════════════════════════════════════════════
# Heuristicas legales
# ══════════════════════════════════════════════════════════════════════

DEROGATED_LAWS_PATTERNS = [
    (r"\bLey\s+15/1999\b", "CRITICAL", "LOPD 15/1999 derogada por LOPDGDD 3/2018"),
    (r"\bLey\s+30/1992\b", "CRITICAL", "Ley 30/1992 derogada por Ley 39/2015 PAC"),
    (r"\bReglamento\s+1720/2007\b", "HIGH",
     "RD 1720/2007 derogado (desarrollo LOPD antigua)"),
    (r"\bLey\s+11/2007\b", "MEDIUM",
     "Ley 11/2007 LAECSP derogada por Ley 40/2015 y 39/2015"),
    (r"\bLey\s+34/2002\b(?!.+LSSI)", "MEDIUM",
     "Referencia a Ley 34/2002 sin contextualizar como LSSI — aclarar"),
    (r"\bDirectiva\s+95/46\b", "CRITICAL",
     "Directiva 95/46/CE derogada por RGPD 2016/679"),
]

CURRENT_LEGAL_REFERENCES = [
    "RD 311/2022", "Real Decreto 311/2022", "ENS",
    "LO 3/2018", "LOPDGDD", "Reglamento (UE) 2016/679", "RGPD",
    "Ley 39/2015", "Ley 40/2015", "Ley 9/2017",
]

LEGAL_CRITICAL_PLACEHOLDERS = {
    "cliente.razon_social",
    "cliente.nif",
    "cliente.firmante.nombre_completo",
    "cliente.firmante.nif",
    "cliente.firmante.cargo",
    "contrato.fecha_firma",
    "marcos.nif",
}

# Clausulas clave esperadas en documentos comerciales. Cada entrada es
# una tupla de sinonimos aceptados — al menos uno debe aparecer en el
# texto (normalizado sin tildes).
COMMERCIAL_REQUIRED_CLAUSES_SYNONYMS: dict[str, tuple[str, ...]] = {
    "objeto": ("objeto", "servicios ofertados", "servicios objeto"),
    "honorarios": (
        "honorarios", "contraprestacion", "cuota mensual",
        "inversion", "precio",
    ),
    "duracion": ("duracion", "validez", "vigencia", "plazo"),
    "obligaciones": ("obligaciones", "deberes"),
    "confidencialidad": ("confidencialidad",),
    "proteccion de datos": (
        "proteccion de datos", "datos personales", "rgpd",
        "lopdgdd", "encargado del tratamiento",
    ),
    "propiedad intelectual": (
        "propiedad intelectual", "propiedad industrial",
    ),
    "limitacion de responsabilidad": (
        "limitacion de responsabilidad", "responsabilidad maxima",
    ),
    "resolucion": (
        "resolucion del contrato", "resolucion anticipada",
        "terminacion", "extincion",
    ),
    "legislacion aplicable": (
        "legislacion aplicable", "ley aplicable", "fuero",
        "jurisdiccion", "se someten a",
    ),
}

# Los templates tipo "propuesta" (P-*) son pre-contractuales y pueden
# delegar en el contrato destino (C-*). Relajamos las exigencias.
PROPOSAL_EXPECTED_CLAUSES = {
    "honorarios", "duracion",
}


# ══════════════════════════════════════════════════════════════════════
# Analisis por template
# ══════════════════════════════════════════════════════════════════════


def _load_template_md(template_codigo: str, subdir: str) -> str | None:
    """Busca el .md del template en backend/app/motors/m06_document_factory/
    templates/<subdir>/ con heuristica de slug."""
    dir_path = TEMPLATES_DIR / subdir
    if not dir_path.is_dir():
        return None
    # Convert E-041 -> E041 prefix
    code_norm = template_codigo.replace("-", "")
    for md_file in dir_path.glob(f"{code_norm}*.md"):
        return md_file.read_text(encoding="utf-8")
    return None


def _audit_template(template: dict[str, Any]) -> dict[str, Any]:
    codigo = template["codigo"]
    categoria = template["categoria"]
    issues: list[dict[str, str]] = []
    level_by_category = {
        "politica": "policies",
        "procedimiento": "procedures",
        "comercial": "commercial",
        "entregable": "deliverables",
        "apendice_f": "deliverables",
        "instruccion_tecnica": "deliverables",
        "registro": "other",
    }
    subdir = level_by_category.get(categoria, "other")
    md_content = _load_template_md(codigo, subdir)

    # 1. Detectar leyes derogadas
    if md_content:
        for pattern, severity, desc in DEROGATED_LAWS_PATTERNS:
            if re.search(pattern, md_content, re.IGNORECASE):
                issues.append({
                    "severity": severity,
                    "type": "derogated_law",
                    "detail": desc,
                })

    # 2. Placeholders legal-criticos con required=true
    phs = template.get("placeholders_requeridos") or {}
    for critical_key in LEGAL_CRITICAL_PLACEHOLDERS:
        spec = phs.get(critical_key)
        if spec is not None and isinstance(spec, dict):
            if not spec.get("required", False):
                issues.append({
                    "severity": "HIGH",
                    "type": "optional_legal_placeholder",
                    "detail": (
                        f"Placeholder legal-critico {critical_key!r} esta "
                        "marcado como required=False"
                    ),
                })

    # 3. Clausulas clave para comerciales (normalizacion sin tildes +
    # sinonimos + relajacion para propuestas P-*).
    if categoria == "comercial" and md_content:
        import unicodedata
        md_norm = unicodedata.normalize("NFKD", md_content.lower())
        md_norm = "".join(c for c in md_norm if not unicodedata.combining(c))
        is_proposal = codigo.startswith("P-")
        required_set = (
            PROPOSAL_EXPECTED_CLAUSES if is_proposal
            else set(COMMERCIAL_REQUIRED_CLAUSES_SYNONYMS.keys())
        )
        missing = [
            canon for canon in required_set
            if not any(
                syn in md_norm
                for syn in COMMERCIAL_REQUIRED_CLAUSES_SYNONYMS[canon]
            )
        ]
        if missing:
            issues.append({
                "severity": "HIGH",
                "type": "missing_commercial_clauses",
                "detail": f"Clausulas ausentes: {', '.join(sorted(missing))}",
            })

    # 4. ENS reference in politicas (normalizacion sin tildes)
    if categoria == "politica" and md_content:
        import unicodedata
        md_norm = unicodedata.normalize("NFKD", md_content)
        md_norm = "".join(c for c in md_norm if not unicodedata.combining(c))
        if (
            "RD 311/2022" not in md_norm
            and "Real Decreto 311/2022" not in md_norm
            and "Esquema Nacional de Seguridad" not in md_norm
            and "ENS" not in md_norm
        ):
            issues.append({
                "severity": "MEDIUM",
                "type": "missing_ens_reference",
                "detail": (
                    "Politica sin referencia explicita al RD 311/2022 / ENS"
                ),
            })

    # 5. Medida ENS documentada en familia
    if categoria in ("politica", "procedimiento"):
        familia = template.get("familia_ens")
        if not familia:
            issues.append({
                "severity": "LOW",
                "type": "missing_familia_ens",
                "detail": "familia_ens sin especificar",
            })

    # 6. Datos firmante RGPD (minimizacion)
    if categoria == "comercial" and md_content:
        # Should collect minimum data: nombre + NIF + cargo, but avoid others
        if "domicilio personal" in md_content.lower():
            issues.append({
                "severity": "MEDIUM",
                "type": "excessive_personal_data",
                "detail": "Solicita domicilio personal del firmante — RGPD minimizacion",
            })

    # Global risk level
    severities = [i["severity"] for i in issues]
    if "CRITICAL" in severities:
        risk = "CRITICAL"
    elif "HIGH" in severities:
        risk = "HIGH"
    elif "MEDIUM" in severities:
        risk = "MEDIUM"
    elif "LOW" in severities:
        risk = "LOW"
    else:
        risk = "OK"

    return {
        "codigo": codigo,
        "nombre": template.get("nombre"),
        "categoria": categoria,
        "risk": risk,
        "issues": issues,
        "md_found": md_content is not None,
    }


def main() -> int:
    data = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    results = [_audit_template(t) for t in data["templates"]]

    totals = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "OK": 0}
    by_cat: dict[str, dict[str, int]] = {}
    for r in results:
        totals[r["risk"]] += 1
        cat = r["categoria"]
        by_cat.setdefault(cat, {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "OK": 0})
        by_cat[cat][r["risk"]] += 1

    total_templates = len(results)
    score = round(
        100.0
        * (
            totals["OK"] * 1.0
            + totals["LOW"] * 0.90
            + totals["MEDIUM"] * 0.70
            + totals["HIGH"] * 0.40
            + totals["CRITICAL"] * 0.0
        )
        / max(1, total_templates),
        1,
    )

    out = {
        "total_templates": total_templates,
        "global_score_0_100": score,
        "totals": totals,
        "by_category": by_cat,
        "results": results,
    }
    out_path = PROJECT_ROOT / "progress" / "legal_audit_autocheck.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Audit done. Score={score}/100. "
        f"CRITICAL={totals['CRITICAL']} HIGH={totals['HIGH']} "
        f"MEDIUM={totals['MEDIUM']} LOW={totals['LOW']} OK={totals['OK']}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
