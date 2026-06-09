"""Template E-226 — PROCEDIMIENTO DE TELETRABAJO.

Source: docs/spec/procedures/E226_PROCEDIMIENTO_TELETRABAJO.md.
Body loaded literally from E226_procedimiento_de_teletrabajo.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-226'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE TELETRABAJO'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E226_PROCEDIMIENTO_TELETRABAJO.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E226_procedimiento_de_teletrabajo.md').read_text(encoding="utf-8")
