"""Template E-123 — POLÍTICA DE SEGURIDAD FÍSICA.

Source: docs/spec/CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md.
Body loaded literally from E123_politica_de_seguridad_fisica.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-123'
TEMPLATE_TITLE = 'POLÍTICA DE SEGURIDAD FÍSICA'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E123_politica_de_seguridad_fisica.md').read_text(encoding="utf-8")
