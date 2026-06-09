"""Template E-106 — POLÍTICA DE COPIAS DE SEGURIDAD.

Source: docs/spec/CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md.
Body loaded literally from E106_politica_de_copias_de_seguridad.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-106'
TEMPLATE_TITLE = 'POLÍTICA DE COPIAS DE SEGURIDAD'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E106_politica_de_copias_de_seguridad.md').read_text(encoding="utf-8")
