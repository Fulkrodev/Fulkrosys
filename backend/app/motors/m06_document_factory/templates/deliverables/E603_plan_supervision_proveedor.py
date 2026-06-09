"""Template E-603 — PLAN DE SUPERVISIÓN DE PROVEEDOR.

Source: Sub-lote 1.B.7.1.1 architect-VERBATIM curated · reactivated 1.D.I
scope reorder pre-1.E (FULKRO empresa privada · supply chain ENS op.ext.*).

Body loaded literally from E603_plan_supervision_proveedor.md (Jinja2 + docxtpl).
Cubre ENS op.ext.2 (Gestión diaria) + op.ext.3 (Cadena suministro) · plan supervisión
multi-listado + branches elif nivel_proveedor CRÍTICO/ALTO/MEDIO.

Variables required: plan_supervision.{kpis_sla[],pruebas_tecnicas[],
revisiones_documentales[],reuniones_operativas[],documentos_requeridos[],
periodo_inicio,periodo_fin} + proveedor.nivel_criticidad + cliente.
Fixture canonical en conftest_proveedores.py (PLAN_SUPERVISION_FULL).
"""
from pathlib import Path

TEMPLATE_ID = 'E-603'
TEMPLATE_TITLE = 'PLAN DE SUPERVISIÓN DE PROVEEDOR'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1B711_proveedores_architect_VERBATIM.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E603_plan_supervision_proveedor.md').read_text(encoding="utf-8")
