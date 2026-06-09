"""Template E-225 — PROCEDIMIENTO DE PRUEBAS PRE-PRODUCCIÓN.

Source: docs/spec/procedures/E225_PROCEDIMIENTO_PRUEBAS_PREPRODUCCION.md.
Body loaded literally from E225_procedimiento_de_pruebas_pre_produccion.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-225'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE PRUEBAS PRE-PRODUCCIÓN'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E225_PROCEDIMIENTO_PRUEBAS_PREPRODUCCION.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E225_procedimiento_de_pruebas_pre_produccion.md').read_text(encoding="utf-8")
