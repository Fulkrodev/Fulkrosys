"""Template E-102 — POLÍTICA DE CONTRASEÑAS Y AUTENTICACIÓN.

Source: docs/spec/CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md.
Body loaded literally from E102_politica_de_contrasenas_y_autenticacion.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-102'
TEMPLATE_TITLE = 'POLÍTICA DE CONTRASEÑAS Y AUTENTICACIÓN'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E102_politica_de_contrasenas_y_autenticacion.md').read_text(encoding="utf-8")
