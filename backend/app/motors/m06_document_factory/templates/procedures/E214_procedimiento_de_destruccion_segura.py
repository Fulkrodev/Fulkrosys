"""Template E-214 — PROCEDIMIENTO DE DESTRUCCIÓN SEGURA.

Source: docs/spec/procedures/E214_PROCEDIMIENTO_DESTRUCCION_SEGURA.md.
Body loaded literally from E214_procedimiento_de_destruccion_segura.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-214'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE DESTRUCCIÓN SEGURA'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E214_PROCEDIMIENTO_DESTRUCCION_SEGURA.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E214_procedimiento_de_destruccion_segura.md').read_text(encoding="utf-8")
