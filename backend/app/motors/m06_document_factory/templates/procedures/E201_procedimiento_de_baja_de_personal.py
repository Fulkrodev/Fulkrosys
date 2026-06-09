"""Template E-201 — PROCEDIMIENTO DE BAJA DE PERSONAL.

Source: docs/spec/CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md.
Body loaded literally from E201_procedimiento_de_baja_de_personal.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-201'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE BAJA DE PERSONAL'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E201_procedimiento_de_baja_de_personal.md').read_text(encoding="utf-8")
