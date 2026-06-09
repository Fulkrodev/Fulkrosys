"""Catálogo canónico de las 16 plantillas Excel (CCN-STIC + manual ENS).

El catálogo expone metadata estable (slug · título · módulo Python que
implementa el generator · referencia normativa). Frontend lo consume
para renderizar el ``ExcelTemplatesGrid`` sin hardcoding.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ExcelTemplateInfo:
    """Metadata de una plantilla Excel canónica."""

    slug: str
    code: str
    title: str
    description: str
    module: str
    ccn_stic: str | None = None


EXCEL_TEMPLATES: list[ExcelTemplateInfo] = [
    ExcelTemplateInfo(
        slug="inventario_activos",
        code="X-001",
        title="Inventario de activos (MAGERIT)",
        description="9 categorías canónicas Libro II MAGERIT v3.",
        module="inventario_activos",
        ccn_stic="MAGERIT v3 Libro II",
    ),
    ExcelTemplateInfo(
        slug="catalogo_servicios_cidat",
        code="X-002",
        title="Catálogo de servicios + valoración CIDAT",
        description="Valoración 5 dimensiones por servicio.",
        module="catalogo_servicios_cidat",
        ccn_stic="RD 311/2022 Anexo I",
    ),
    ExcelTemplateInfo(
        slug="matriz_riesgos",
        code="X-003",
        title="Matriz de riesgos simplificada (Básica)",
        description="Análisis riesgos para sistemas Categoría Básica.",
        module="matriz_riesgos",
        ccn_stic="MAGERIT v3 simplificado",
    ),
    ExcelTemplateInfo(
        slug="dda_matriz",
        code="X-004",
        title="Declaración de Aplicabilidad (DdA)",
        description="73 medidas Anexo II + columnas operativas.",
        module="dda_matriz",
        ccn_stic="RD 311/2022 Anexo II",
    ),
    ExcelTemplateInfo(
        slug="plan_tratamiento_riesgos",
        code="X-005",
        title="Plan de tratamiento de riesgos",
        description="Acciones + responsables + plazos + coste.",
        module="plan_tratamiento_riesgos",
        ccn_stic="MAGERIT v3 Libro III",
    ),
    ExcelTemplateInfo(
        slug="matriz_gap_analysis",
        code="X-006",
        title="Matriz Gap Analysis CCN-STIC 808",
        description="Check-list completa 808.",
        module="matriz_gap_analysis",
        ccn_stic="CCN-STIC 808",
    ),
    ExcelTemplateInfo(
        slug="plantilla_pda",
        code="X-007",
        title="Plan de Adecuación tabular",
        description="Complementario al E-150 narrativo.",
        module="plantilla_pda",
        ccn_stic="CCN-STIC 806",
    ),
    ExcelTemplateInfo(
        slug="registro_incidentes",
        code="X-008",
        title="Registro de incidentes",
        description="Log incidentes formato CCN-STIC 817.",
        module="registro_incidentes",
        ccn_stic="CCN-STIC 817",
    ),
    ExcelTemplateInfo(
        slug="indicadores_metricas",
        code="X-009",
        title="Indicadores y métricas seguridad",
        description="KPIs catálogo CCN-STIC 815.",
        module="indicadores_metricas",
        ccn_stic="CCN-STIC 815",
    ),
    ExcelTemplateInfo(
        slug="informe_auditoria_interna",
        code="X-010",
        title="Informe auditoría interna",
        description="Plantilla CCN-STIC 802.",
        module="informe_auditoria_interna",
        ccn_stic="CCN-STIC 802",
    ),
    ExcelTemplateInfo(
        slug="bia_business_impact",
        code="X-011",
        title="Análisis impacto en el negocio (BIA)",
        description="BIA con RTO/RPO + procesos críticos.",
        module="bia_business_impact",
        ccn_stic="ISO 22301",
    ),
    ExcelTemplateInfo(
        slug="matriz_raci",
        code="X-012",
        title="Matriz RACI roles ENS",
        description="Responsable / Accountable / Consulted / Informed.",
        module="matriz_raci",
        ccn_stic="CCN-STIC 801",
    ),
    ExcelTemplateInfo(
        slug="plan_pruebas_continuidad",
        code="X-013",
        title="Plan de pruebas de continuidad",
        description="Simulacro anual + escenarios.",
        module="plan_pruebas_continuidad",
        ccn_stic="ISO 22301",
    ),
    ExcelTemplateInfo(
        slug="sla_terceros",
        code="X-014",
        title="SLA / SLO con proveedores",
        description="Niveles servicio acordados con terceros.",
        module="sla_terceros",
        ccn_stic="CCN-STIC 823",
    ),
    ExcelTemplateInfo(
        slug="evaluacion_proveedores_caiq",
        code="X-015",
        title="Evaluación proveedores cloud (CAIQ)",
        description="Cuestionario CSA CAIQ + módulo ENS.",
        module="evaluacion_proveedores_caiq",
        ccn_stic="CSA CAIQ + CCN-STIC 823",
    ),
    ExcelTemplateInfo(
        slug="rat_rgpd",
        code="X-016",
        title="Registro Actividades de Tratamiento (RAT)",
        description="Art. 30 RGPD · campos AEPD obligatorios.",
        module="rat_rgpd",
        ccn_stic="RGPD Art. 30",
    ),
]


_BY_SLUG: dict[str, ExcelTemplateInfo] = {t.slug: t for t in EXCEL_TEMPLATES}


def get_template_info(slug: str) -> ExcelTemplateInfo:
    """Devuelve metadata por slug · ``KeyError`` si no existe."""
    if slug not in _BY_SLUG:
        raise KeyError(f"Excel template '{slug}' no existe en catálogo")
    return _BY_SLUG[slug]


def list_templates() -> list[ExcelTemplateInfo]:
    """Lista canónica para frontend grid."""
    return list(EXCEL_TEMPLATES)
