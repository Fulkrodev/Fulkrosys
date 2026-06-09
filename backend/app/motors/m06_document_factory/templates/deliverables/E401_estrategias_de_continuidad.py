"""Template E-401 — ESTRATEGIAS DE CONTINUIDAD.

Source: FULKRO architect curated · sub-lote 1.B.2 (cubre GAP residual
identificado en sub-lote 1.B.1 · plan v2 §14 GAP CRITICO 4 BCP/DRP).
Body loaded literally from E401_estrategias_de_continuidad.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-401'
TEMPLATE_TITLE = 'ESTRATEGIAS DE CONTINUIDAD'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'FULKRO architect curated · sub-lote 1.B.2'

TEMPLATE_BODY = (Path(__file__).parent / 'E401_estrategias_de_continuidad.md').read_text(encoding="utf-8")
