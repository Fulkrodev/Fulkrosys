"""Template E-202 — PROCEDIMIENTO DE CAMBIO DE ROL.

Source: docs/spec/CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md.
Body loaded literally from E202_procedimiento_de_cambio_de_rol.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-202'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE CAMBIO DE ROL'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E202_procedimiento_de_cambio_de_rol.md').read_text(encoding="utf-8")
