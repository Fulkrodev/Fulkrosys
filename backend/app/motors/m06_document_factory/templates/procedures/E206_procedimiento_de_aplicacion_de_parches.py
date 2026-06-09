"""Template E-206 — PROCEDIMIENTO DE APLICACIÓN DE PARCHES.

Source: docs/spec/CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md.
Body loaded literally from E206_procedimiento_de_aplicacion_de_parches.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-206'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE APLICACIÓN DE PARCHES'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E206_procedimiento_de_aplicacion_de_parches.md').read_text(encoding="utf-8")
