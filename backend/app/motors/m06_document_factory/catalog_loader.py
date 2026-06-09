"""Motor 6 -- Document Factory -- catalog loader.

Loads the template catalog from YAML.
Pattern consistent with M4 catalog_loader.py and M19 catalog_loader.py.
"""
from pathlib import Path
from typing import Any

import yaml

from backend.app.motors.m06_document_factory.exceptions import CatalogLoadError

CATALOG_PATH = (
    Path(__file__).resolve().parents[4]
    / "docs"
    / "catalogs"
    / "template_catalog_v1.yaml"
)

REQUIRED_TEMPLATE_FIELDS = [
    "codigo",
    "nombre",
    "categoria",
]

VALID_CATEGORIAS = {
    "politica",
    "procedimiento",
    "comercial",
    "entregable",
    "apendice_f",
    "instruccion_tecnica",
    "registro",
}

VALID_APLICA_DESDE = {"basica", "media", "alta"}


def load_catalog(catalog_path: Path | None = None) -> dict[str, Any]:
    """Load and validate template_catalog YAML.

    Returns the parsed dict with keys: version, templates.
    Raises CatalogLoadError on missing file or parse issues.
    """
    path = catalog_path or CATALOG_PATH
    if not path.exists():
        raise CatalogLoadError(f"Template catalog not found at {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise CatalogLoadError(f"YAML parse error: {exc}") from exc

    if not isinstance(data, dict):
        raise CatalogLoadError("Catalog root is not a dict")
    if "templates" not in data:
        raise CatalogLoadError("Missing 'templates' key in catalog")

    templates = data["templates"]
    if not isinstance(templates, list):
        raise CatalogLoadError("'templates' is not a list")

    for idx, t in enumerate(templates):
        for field in REQUIRED_TEMPLATE_FIELDS:
            if field not in t:
                raise CatalogLoadError(
                    f"Template idx={idx} codigo={t.get('codigo', '?')} "
                    f"missing field: {field}"
                )
        cat = t.get("categoria", "")
        if cat not in VALID_CATEGORIAS:
            raise CatalogLoadError(
                f"Template {t['codigo']} has invalid categoria '{cat}'"
            )
        aplica = t.get("aplica_desde")
        if aplica and aplica not in VALID_APLICA_DESDE:
            raise CatalogLoadError(
                f"Template {t['codigo']} has invalid aplica_desde '{aplica}'"
            )
        # L-6 · flag opcional de proporcionalidad para micro/autónomo. Ausente o
        # true → aplica siempre; false → se omite cuando tamano == "micro"
        # (el autónomo cubre la medida con una tarea ligera ENR_AUT · L-5).
        aplica_micro = t.get("aplica_micro")
        if aplica_micro is not None and not isinstance(aplica_micro, bool):
            raise CatalogLoadError(
                f"Template {t['codigo']} has non-bool aplica_micro '{aplica_micro}'"
            )

        # Normalize placeholders (accepts both legacy and new format)
        raw_ph = t.get("placeholders") or t.get("placeholders_requeridos")
        t["placeholders"] = _normalize_placeholders(raw_ph)

    return data


def get_template_metadata(
    catalog: dict[str, Any], codigo: str
) -> dict[str, Any] | None:
    """Get a single template entry by its codigo."""
    for t in catalog.get("templates", []):
        if t["codigo"] == codigo:
            return t
    return None


def list_templates_by_categoria(
    catalog: dict[str, Any], categoria: str
) -> list[dict[str, Any]]:
    """Filter templates by categoria."""
    return [
        t
        for t in catalog.get("templates", [])
        if t.get("categoria") == categoria
    ]


def list_templates_by_familia(
    catalog: dict[str, Any], familia: str
) -> list[dict[str, Any]]:
    """Filter templates by familia_ens."""
    return [
        t
        for t in catalog.get("templates", [])
        if t.get("familia_ens") == familia
    ]


def list_applicable_for_size(
    catalog: dict[str, Any], size: str | None
) -> list[dict[str, Any]]:
    """L-6 · plantillas aplicables para un tamaño de organización.

    Para ``size == "micro"`` (autónomo/microempresa) se excluyen las plantillas
    marcadas ``aplica_micro: false`` (artefactos de escala-equipo desproporcionados
    para una organización unipersonal · la medida ENS se cubre con tareas ligeras
    del perfil autónomo · ver L-5/L-8). Para el resto de tamaños se devuelven todas.
    """
    templates = catalog.get("templates", [])
    if size != "micro":
        return list(templates)
    return [t for t in templates if t.get("aplica_micro", True) is not False]


def get_catalog_version(catalog: dict[str, Any]) -> str:
    """Extract the version string from a loaded catalog."""
    return str(catalog.get("version", "unknown"))


def get_total_templates(catalog: dict[str, Any]) -> int:
    """Get the total number of templates in the catalog."""
    return len(catalog.get("templates", []))


def _normalize_placeholders(raw: dict | None) -> dict:
    """Normalize placeholders to {key: {description, required}} format.

    Accepts legacy format {key: string_description} (treated as optional)
    and new format {key: {description, required}}.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise CatalogLoadError(f"placeholders must be a dict, got {type(raw).__name__}")
    normalized = {}
    for key, value in raw.items():
        if isinstance(value, str):
            normalized[key] = {"description": value, "required": False}
        elif isinstance(value, dict):
            if "description" not in value:
                raise CatalogLoadError(f"placeholder {key} missing 'description' field")
            normalized[key] = {
                "description": str(value["description"]),
                "required": bool(value.get("required", False)),
            }
        else:
            raise CatalogLoadError(f"placeholder {key} has invalid value type {type(value).__name__}")
    return normalized


def get_required_vars(placeholders: dict) -> list[str]:
    """Extract the list of placeholder keys marked as required=True."""
    return sorted(k for k, v in placeholders.items() if isinstance(v, dict) and v.get("required", False))
