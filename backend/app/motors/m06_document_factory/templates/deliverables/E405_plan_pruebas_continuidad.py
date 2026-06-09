"""Template E-405 — PLAN DE PRUEBAS DE CONTINUIDAD.

Source: FULKRO architect curated · sub-lote 1.B.2 (cubre GAP residual BCP/DRP).
Body loaded literally from E405_plan_pruebas_continuidad.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-405'
TEMPLATE_TITLE = 'PLAN DE PRUEBAS DE CONTINUIDAD'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'FULKRO architect curated · sub-lote 1.B.2'

TEMPLATE_BODY = (Path(__file__).parent / 'E405_plan_pruebas_continuidad.md').read_text(encoding="utf-8")
