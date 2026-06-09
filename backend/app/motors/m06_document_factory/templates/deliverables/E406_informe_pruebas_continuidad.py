"""Template E-406 — INFORME DE PRUEBAS DE CONTINUIDAD.

Source: FULKRO architect curated · sub-lote 1.B.2 (cubre GAP residual BCP/DRP).
Body loaded literally from E406_informe_pruebas_continuidad.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-406'
TEMPLATE_TITLE = 'INFORME DE PRUEBAS DE CONTINUIDAD'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'FULKRO architect curated · sub-lote 1.B.2'

TEMPLATE_BODY = (Path(__file__).parent / 'E406_informe_pruebas_continuidad.md').read_text(encoding="utf-8")
