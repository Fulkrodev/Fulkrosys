"""Template E-110 — POLÍTICA DE TELETRABAJO Y MOVILIDAD.

Source: docs/spec/CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md.
Body loaded literally from E110_politica_de_teletrabajo_y_movilidad.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-110'
TEMPLATE_TITLE = 'POLÍTICA DE TELETRABAJO Y MOVILIDAD'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E110_politica_de_teletrabajo_y_movilidad.md').read_text(encoding="utf-8")
