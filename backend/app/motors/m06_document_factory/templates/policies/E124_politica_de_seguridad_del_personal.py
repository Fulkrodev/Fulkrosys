"""Template E-124 — POLÍTICA DE SEGURIDAD DEL PERSONAL.

Source: docs/spec/CORRECCION_5B_12_POLITICAS_RESTANTES.md.
Body loaded literally from E124_politica_de_seguridad_del_personal.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-124'
TEMPLATE_TITLE = 'POLÍTICA DE SEGURIDAD DEL PERSONAL'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5B_12_POLITICAS_RESTANTES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E124_politica_de_seguridad_del_personal.md').read_text(encoding="utf-8")
