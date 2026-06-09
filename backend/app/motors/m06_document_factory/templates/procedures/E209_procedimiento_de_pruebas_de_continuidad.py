"""Template E-209 — PROCEDIMIENTO DE PRUEBAS DE CONTINUIDAD.

Source: docs/spec/CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md.
Body loaded literally from E209_procedimiento_de_pruebas_de_continuidad.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-209'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE PRUEBAS DE CONTINUIDAD'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E209_procedimiento_de_pruebas_de_continuidad.md').read_text(encoding="utf-8")
