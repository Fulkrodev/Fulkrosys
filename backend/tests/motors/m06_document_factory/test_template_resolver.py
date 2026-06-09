"""Tests TemplateResolver per arquetipo PYME (ADR-036 SAN-D MB-17.6)."""
from __future__ import annotations

from backend.app.motors.m06_document_factory.template_resolver import (
    TemplateResolver,
)


PSI_TEMPLATE_ID = "E100_politica_de_seguridad_de_la_informacion"


def test_resolve_default_when_no_archetype():
    """Sin arquetipo · retorna canonical baseline."""
    resolver = TemplateResolver()
    path = resolver.resolve_template(PSI_TEMPLATE_ID, "BASICA", None)
    assert path.name == f"{PSI_TEMPLATE_ID}.md"


def test_resolve_sector_salud_variant():
    """archetype=sector_salud · resuelve _sector_salud.md."""
    resolver = TemplateResolver()
    path = resolver.resolve_template(PSI_TEMPLATE_ID, "MEDIA", "sector_salud")
    assert path.name == f"{PSI_TEMPLATE_ID}_sector_salud.md"
    assert path.exists()


def test_resolve_saas_only_variant():
    """archetype=saas_only · resuelve _saas_only.md."""
    resolver = TemplateResolver()
    path = resolver.resolve_template(PSI_TEMPLATE_ID, "BASICA", "saas_only")
    assert path.name == f"{PSI_TEMPLATE_ID}_saas_only.md"
    assert path.exists()


def test_resolve_desarrollador_aapp_variant():
    """archetype=desarrollador_aapp · resuelve _desarrollador_aapp.md."""
    resolver = TemplateResolver()
    path = resolver.resolve_template(
        PSI_TEMPLATE_ID, "MEDIA", "desarrollador_aapp",
    )
    assert path.name == f"{PSI_TEMPLATE_ID}_desarrollador_aapp.md"
    assert path.exists()


def test_resolve_archetype_without_variant_falls_back_to_default():
    """archetype=generico · sin variant · fallback canonical baseline."""
    resolver = TemplateResolver()
    path = resolver.resolve_template(PSI_TEMPLATE_ID, "BASICA", "generico")
    assert path.name == f"{PSI_TEMPLATE_ID}.md"


def test_resolve_archetype_with_variant_path_does_not_exist_falls_back():
    """archetype con feature aplicable pero archivo no existe · fallback default."""
    resolver = TemplateResolver()
    # E150_plan_adecuacion no tiene variantes archivo · fallback default
    path = resolver.resolve_template(
        "E150_plan_adecuacion", "MEDIA", "sector_salud",
    )
    assert path.name == "E150_plan_adecuacion.md"


def test_resolve_uses_absolute_path():
    """TEMPLATES_ROOT es absoluto · no relativo a CWD (TRAD-10 ADR-036)."""
    resolver = TemplateResolver()
    assert resolver.TEMPLATES_ROOT.is_absolute()
    assert resolver.TEMPLATES_ROOT.exists()


def test_variant_mapping_uses_lowercase_enum():
    """VARIANT_MAPPING values son lowercase suffixes (PymeArquetipo enum real)."""
    resolver = TemplateResolver()
    suffixes = list(resolver.VARIANT_MAPPING.values())
    for suffix in suffixes:
        assert suffix.startswith("_")
        # Sufijo lowercase (sector_salud · saas_only · etc)
        assert suffix == suffix.lower()
