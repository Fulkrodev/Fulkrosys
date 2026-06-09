"""Template E-208 — PROCEDIMIENTO DE RESTAURACIÓN.

Source: docs/spec/procedures/E208_PROCEDIMIENTO_RESTAURACION.md.
Body loaded literally from E208_procedimiento_de_restauracion.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-208'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE RESTAURACIÓN'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E208_PROCEDIMIENTO_RESTAURACION.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E208_procedimiento_de_restauracion.md').read_text(encoding="utf-8")
