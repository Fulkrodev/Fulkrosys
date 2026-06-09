"""Template E-111 — POLÍTICA DE USO DE SERVICIOS CLOUD.

Source: docs/spec/CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md.
Body loaded literally from E111_politica_de_uso_de_servicios_cloud.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-111'
TEMPLATE_TITLE = 'POLÍTICA DE USO DE SERVICIOS CLOUD'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E111_politica_de_uso_de_servicios_cloud.md').read_text(encoding="utf-8")
