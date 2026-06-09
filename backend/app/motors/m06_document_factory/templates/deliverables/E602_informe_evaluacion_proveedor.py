"""Template E-602 — INFORME DE EVALUACIÓN DE PROVEEDOR.

Source: Sub-lote 1.B.7.1.1 architect-VERBATIM curated · reactivated 1.D.I
scope reorder pre-1.E (FULKRO empresa privada · supply chain ENS op.ext.*).

Body loaded literally from E602_informe_evaluacion_proveedor.md (Jinja2 + docxtpl).
Cubre ENS op.ext.1 + op.ext.3 · 5 dimensions assessment (a/b/c/d/e) + scoring + DORA + NIS2 + BCP + INES + decisión entidad.

Variables required: assessment.dimension_{a,b,c,d,e}.{conclusion,descripcion,evidencias} +
scoring_total + DORA/NIS2/INES flags + evaluador.
Fixture canonical en conftest_proveedores.py (ASSESSMENT_FULL).
"""
from pathlib import Path

TEMPLATE_ID = 'E-602'
TEMPLATE_TITLE = 'INFORME DE EVALUACIÓN DE PROVEEDOR'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1B711_proveedores_architect_VERBATIM.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E602_informe_evaluacion_proveedor.md').read_text(encoding="utf-8")
