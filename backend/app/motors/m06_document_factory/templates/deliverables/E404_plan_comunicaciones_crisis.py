"""Template E-404 — PLAN DE COMUNICACIONES EN CRISIS.

Source: FULKRO architect curated · sub-lote 1.B.2 (cubre GAP residual BCP/DRP).
Body loaded literally from E404_plan_comunicaciones_crisis.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-404'
TEMPLATE_TITLE = 'PLAN DE COMUNICACIONES EN CRISIS'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'FULKRO architect curated · sub-lote 1.B.2'

TEMPLATE_BODY = (Path(__file__).parent / 'E404_plan_comunicaciones_crisis.md').read_text(encoding="utf-8")
