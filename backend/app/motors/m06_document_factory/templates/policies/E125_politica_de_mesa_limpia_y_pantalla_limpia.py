"""Template E-125 — POLÍTICA DE MESA LIMPIA Y PANTALLA LIMPIA.

Source: docs/spec/CORRECCION_5B_12_POLITICAS_RESTANTES.md.
Body loaded literally from E125_politica_de_mesa_limpia_y_pantalla_limpia.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-125'
TEMPLATE_TITLE = 'POLÍTICA DE MESA LIMPIA Y PANTALLA LIMPIA'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5B_12_POLITICAS_RESTANTES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E125_politica_de_mesa_limpia_y_pantalla_limpia.md').read_text(encoding="utf-8")
