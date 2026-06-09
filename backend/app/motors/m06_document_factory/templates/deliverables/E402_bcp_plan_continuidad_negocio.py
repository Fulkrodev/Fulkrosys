"""Template E-402 — PLAN DE CONTINUIDAD DEL NEGOCIO (BCP).

Source: FULKRO architect curated · sub-lote 1.B.2 (cubre GAP residual BCP/DRP).
Body loaded literally from E402_bcp_plan_continuidad_negocio.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-402'
TEMPLATE_TITLE = 'PLAN DE CONTINUIDAD DEL NEGOCIO (BCP)'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'FULKRO architect curated · sub-lote 1.B.2'

TEMPLATE_BODY = (Path(__file__).parent / 'E402_bcp_plan_continuidad_negocio.md').read_text(encoding="utf-8")
