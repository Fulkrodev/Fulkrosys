"""Template E-403 — PLAN DE RECUPERACIÓN DE DESASTRES TIC (DRP).

Source: FULKRO architect curated · sub-lote 1.B.2 (cubre GAP residual BCP/DRP).
Body loaded literally from E403_drp_plan_recuperacion_desastres.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-403'
TEMPLATE_TITLE = 'PLAN DE RECUPERACIÓN DE DESASTRES TIC (DRP)'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'FULKRO architect curated · sub-lote 1.B.2'

TEMPLATE_BODY = (Path(__file__).parent / 'E403_drp_plan_recuperacion_desastres.md').read_text(encoding="utf-8")
