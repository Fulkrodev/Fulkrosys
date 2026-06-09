"""Template E-121 — POLÍTICA DE REDES Y COMUNICACIONES.

Source: docs/spec/CORRECCION_5B_12_POLITICAS_RESTANTES.md.
Body loaded literally from E121_politica_de_redes_y_comunicaciones.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-121'
TEMPLATE_TITLE = 'POLÍTICA DE REDES Y COMUNICACIONES'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5B_12_POLITICAS_RESTANTES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E121_politica_de_redes_y_comunicaciones.md').read_text(encoding="utf-8")
