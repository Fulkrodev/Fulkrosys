"""Template E-122 — POLÍTICA DE GESTIÓN DE SOPORTES.

Source: docs/spec/CORRECCION_5B_12_POLITICAS_RESTANTES.md.
Body loaded literally from E122_politica_de_gestion_de_soportes.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-122'
TEMPLATE_TITLE = 'POLÍTICA DE GESTIÓN DE SOPORTES'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5B_12_POLITICAS_RESTANTES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E122_politica_de_gestion_de_soportes.md').read_text(encoding="utf-8")
