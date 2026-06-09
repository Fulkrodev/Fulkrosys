"""Template E-115 — POLÍTICA DE GESTIÓN DE VULNERABILIDADES.

Source: docs/spec/CORRECCION_5B_12_POLITICAS_RESTANTES.md.
Body loaded literally from E115_politica_de_gestion_de_vulnerabilidades.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-115'
TEMPLATE_TITLE = 'POLÍTICA DE GESTIÓN DE VULNERABILIDADES'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5B_12_POLITICAS_RESTANTES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E115_politica_de_gestion_de_vulnerabilidades.md').read_text(encoding="utf-8")
