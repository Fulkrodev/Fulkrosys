"""Template E-230 — PROCEDIMIENTO DE BASTIONADO DE SISTEMAS.

Source: docs/spec/procedures/E230_PROCEDIMIENTO_BASTIONADO_SISTEMAS.md.
Body loaded literally from E230_procedimiento_de_bastionado_de_sistemas.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-230'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE BASTIONADO DE SISTEMAS'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E230_PROCEDIMIENTO_BASTIONADO_SISTEMAS.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E230_procedimiento_de_bastionado_de_sistemas.md').read_text(encoding="utf-8")
