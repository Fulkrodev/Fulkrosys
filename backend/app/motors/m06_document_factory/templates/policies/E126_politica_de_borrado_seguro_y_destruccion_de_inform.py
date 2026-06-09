"""Template E-126 — POLÍTICA DE BORRADO SEGURO Y DESTRUCCIÓN DE INFORMACIÓN.

Source: docs/spec/CORRECCION_5B_12_POLITICAS_RESTANTES.md.
Body loaded literally from E126_politica_de_borrado_seguro_y_destruccion_de_inform.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-126'
TEMPLATE_TITLE = 'POLÍTICA DE BORRADO SEGURO Y DESTRUCCIÓN DE INFORMACIÓN'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5B_12_POLITICAS_RESTANTES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E126_politica_de_borrado_seguro_y_destruccion_de_inform.md').read_text(encoding="utf-8")
