"""Template E-116 — POLÍTICA DE GESTIÓN DE CAMBIOS.

Source: docs/spec/CORRECCION_5B_12_POLITICAS_RESTANTES.md.
Body loaded literally from E116_politica_de_gestion_de_cambios.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-116'
TEMPLATE_TITLE = 'POLÍTICA DE GESTIÓN DE CAMBIOS'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5B_12_POLITICAS_RESTANTES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E116_politica_de_gestion_de_cambios.md').read_text(encoding="utf-8")
