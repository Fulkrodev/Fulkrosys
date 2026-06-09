"""Template E-219 — PROCEDIMIENTO DE REVISIÓN POR LA DIRECCIÓN.

Source: docs/spec/CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md.
Body loaded literally from E219_procedimiento_de_revision_por_la_direccion.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-219'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE REVISIÓN POR LA DIRECCIÓN'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E219_procedimiento_de_revision_por_la_direccion.md').read_text(encoding="utf-8")
