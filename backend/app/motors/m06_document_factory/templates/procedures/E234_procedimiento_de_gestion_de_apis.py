"""Template E-234 — PROCEDIMIENTO DE GESTIÓN DE APIs.

Source: docs/spec/procedures/E234_PROCEDIMIENTO_GESTION_APIS.md.
Body loaded literally from E234_procedimiento_de_gestion_de_apis.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-234'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE GESTIÓN DE APIs'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E234_PROCEDIMIENTO_GESTION_APIS.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E234_procedimiento_de_gestion_de_apis.md').read_text(encoding="utf-8")
