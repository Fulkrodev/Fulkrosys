"""Template E-200 — PROCEDIMIENTO DE ALTA DE PERSONAL.

Source: docs/spec/CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md.
Body loaded literally from E200_procedimiento_de_alta_de_personal.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-200'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE ALTA DE PERSONAL'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E200_procedimiento_de_alta_de_personal.md').read_text(encoding="utf-8")
