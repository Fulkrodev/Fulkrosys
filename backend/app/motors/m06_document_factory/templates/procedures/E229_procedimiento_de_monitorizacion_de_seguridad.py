"""Template E-229 — PROCEDIMIENTO DE MONITORIZACIÓN DE SEGURIDAD.

Source: docs/spec/procedures/E229_PROCEDIMIENTO_MONITORIZACION_SEGURIDAD.md.
Body loaded literally from E229_procedimiento_de_monitorizacion_de_seguridad.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-229'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE MONITORIZACIÓN DE SEGURIDAD'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E229_PROCEDIMIENTO_MONITORIZACION_SEGURIDAD.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E229_procedimiento_de_monitorizacion_de_seguridad.md').read_text(encoding="utf-8")
