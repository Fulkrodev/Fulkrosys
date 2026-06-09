"""Excel generators · 16 plantillas canónicas manual ENS · SAN-C.MB-10.1.

Cada generator implementa la firma::

    def generate(project_id: uuid.UUID, db: AsyncSession) -> openpyxl.Workbook

Y es resiliente: si los datos cross-motor no están disponibles, devuelve
el workbook con cabeceras canónicas + filas placeholder vacías para que
el cliente rellene durante reuniones. La estructura es la canon ENS y
la auditoría puede verificar el documento incluso pre-implantación.

Catálogo de las 16 plantillas (briefing SAN-C.MB-10.1):

1.  inventario_activos             · MAGERIT Libro II · 9 categorías
2.  catalogo_servicios_cidat       · valoración CIDAT por servicio
3.  matriz_riesgos                 · análisis riesgos simplificado Básica
4.  dda_matriz                     · 73 medidas Anexo II
5.  plan_tratamiento_riesgos       · acciones + responsables + plazos
6.  matriz_gap_analysis            · CCN-STIC 808 check-list
7.  plantilla_pda                  · plan adecuación tabular complementario
8.  registro_incidentes            · log incidentes formato CCN-STIC 817
9.  indicadores_metricas           · CCN-STIC 815 KPIs
10. informe_auditoria_interna      · CCN-STIC 802
11. bia_business_impact            · BIA estructurado RTO/RPO
12. matriz_raci                    · roles ENS responsabilidades
13. plan_pruebas_continuidad       · simulacro anual
14. sla_terceros                   · SLA/SLO con proveedores
15. evaluacion_proveedores_caiq    · cuestionario CAIQ + módulo ENS
16. rat_rgpd                       · Registro Actividades Tratamiento

Refs: SAN-C.MB-10.1
"""
from __future__ import annotations

import uuid
from typing import Awaitable, Callable

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from .registry import (
    EXCEL_TEMPLATES,
    ExcelTemplateInfo,
    get_template_info,
    list_templates,
)


GeneratorFn = Callable[[uuid.UUID, AsyncSession], Awaitable[Workbook]]


async def dispatch(
    template_name: str,
    project_id: uuid.UUID,
    db: AsyncSession,
) -> Workbook:
    """Invoca el generator correcto según ``template_name``.

    Los generators se importan lazy para evitar cargar 16 módulos en boot.
    Lanza ``KeyError`` si el template no existe en el catálogo.
    """
    info = get_template_info(template_name)
    module = __import__(
        f"backend.app.motors.m06_document_factory.excel_generators.{info.module}",
        fromlist=["generate"],
    )
    fn: GeneratorFn = module.generate
    return await fn(project_id, db)


__all__ = [
    "EXCEL_TEMPLATES",
    "ExcelTemplateInfo",
    "dispatch",
    "get_template_info",
    "list_templates",
]
