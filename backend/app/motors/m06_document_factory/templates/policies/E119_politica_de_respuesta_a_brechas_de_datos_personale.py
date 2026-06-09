"""Template E-119 — POLÍTICA DE RESPUESTA A BRECHAS DE DATOS PERSONALES.

Source: docs/spec/CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md.
Body loaded literally from E119_politica_de_respuesta_a_brechas_de_datos_personale.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-119'
TEMPLATE_TITLE = 'POLÍTICA DE RESPUESTA A BRECHAS DE DATOS PERSONALES'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E119_politica_de_respuesta_a_brechas_de_datos_personale.md').read_text(encoding="utf-8")
