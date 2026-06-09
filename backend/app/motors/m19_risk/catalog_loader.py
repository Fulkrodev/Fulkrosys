"""Motor 19 — Project Risk Management — catalog loader.

Loads the base catalog of 30 project risks from YAML and provides
utilities to instantiate risks for a project.

ALCANCE: funciones de lectura y parsing del YAML + conversion
a datos listos para insertar en DB. NO toca DB directamente.
"""
from pathlib import Path
from typing import Any

import yaml

from backend.app.motors.m19_risk.exceptions import (
    CatalogNotFoundError,
    CatalogParseError,
)

# Default catalog location
CATALOG_PATH = Path(__file__).resolve().parents[4] / "docs" / "catalogs" / "project_risks_catalog_v1.yaml"

# Required fields for each risk entry in the YAML
REQUIRED_FIELDS = [
    "codigo",
    "numero",
    "titulo",
    "descripcion",
    "categoria",
    "probabilidad_default",
    "impacto_dias_default",
    "impacto_euros_default",
    "owner_default",
    "trigger_condicion",
    "mitigation_plan",
    "contingency_plan",
]

VALID_CATEGORIES = {
    "cliente",
    "personas",
    "presupuesto",
    "normativo",
    "tecnico",
    "comercial",
}

VALID_STATUS = {
    "identificado",
    "monitorizado",
    "materializado",
    "cerrado",
}


def load_catalog(catalog_path: Path | None = None) -> dict[str, Any]:
    """Load and validate the project risks catalog YAML.

    Returns the parsed dict with version, riesgos_base, categorias, etc.
    Raises CatalogNotFoundError or CatalogParseError on failure.
    """
    path = catalog_path or CATALOG_PATH

    if not path.exists():
        raise CatalogNotFoundError(f"Catalog not found at {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise CatalogParseError(f"YAML parse error: {e}") from e

    if not isinstance(data, dict):
        raise CatalogParseError("Catalog root is not a dict")

    if "riesgos_base" not in data:
        raise CatalogParseError("Missing 'riesgos_base' key in catalog")

    risks = data["riesgos_base"]
    if not isinstance(risks, list):
        raise CatalogParseError("'riesgos_base' is not a list")

    # Validate each risk has required fields
    for idx, risk in enumerate(risks):
        for field in REQUIRED_FIELDS:
            if field not in risk:
                raise CatalogParseError(
                    f"Risk at index {idx} (code={risk.get('codigo', '?')}) "
                    f"missing required field: {field}"
                )

        if risk["categoria"] not in VALID_CATEGORIES:
            raise CatalogParseError(
                f"Risk {risk['codigo']} has invalid categoria: {risk['categoria']} "
                f"(valid: {VALID_CATEGORIES})"
            )

    return data


def get_catalog_version(catalog: dict[str, Any]) -> str:
    """Extract the version string from a loaded catalog."""
    return str(catalog.get("version", "unknown"))


def get_catalog_total_risks(catalog: dict[str, Any]) -> int:
    """Get the total number of risks in the catalog."""
    return len(catalog.get("riesgos_base", []))


def get_risks_by_categoria(
    catalog: dict[str, Any],
    categoria: str,
) -> list[dict[str, Any]]:
    """Get all risks in a specific categoria."""
    return [r for r in catalog["riesgos_base"] if r["categoria"] == categoria]


def get_risk_by_codigo(
    catalog: dict[str, Any],
    codigo: str,
) -> dict[str, Any] | None:
    """Get a specific risk by its codigo (R-001 to R-030)."""
    for risk in catalog["riesgos_base"]:
        if risk["codigo"] == codigo:
            return risk
    return None


def catalog_to_project_risk_data(
    risk_entry: dict[str, Any],
    project_id: Any,
) -> dict[str, Any]:
    """Convert a catalog risk entry into data ready to create a ProjectRisk model.

    Maps catalog field names to model field names:
    - codigo -> risk_code
    - *_default -> actual fields
    - Adds project_id and default status='identificado'
    """
    return {
        "project_id": project_id,
        "risk_code": risk_entry["codigo"],
        "titulo": risk_entry["titulo"],
        "descripcion": risk_entry.get("descripcion"),
        "categoria": risk_entry["categoria"],
        "probabilidad": risk_entry.get("probabilidad_default"),
        "impacto_dias": risk_entry.get("impacto_dias_default"),
        "impacto_euros": risk_entry.get("impacto_euros_default"),
        "owner": risk_entry.get("owner_default"),
        "trigger_condicion": risk_entry.get("trigger_condicion"),
        "mitigation_plan": risk_entry.get("mitigation_plan"),
        "contingency_plan": risk_entry.get("contingency_plan"),
        "status": "identificado",
    }
