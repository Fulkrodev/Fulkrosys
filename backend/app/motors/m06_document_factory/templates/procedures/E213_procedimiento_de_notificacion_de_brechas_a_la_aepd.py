"""Template E-213 — PROCEDIMIENTO DE NOTIFICACIÓN DE BRECHAS A LA AEPD.

Source: docs/spec/CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md.
Body loaded literally from E213_procedimiento_de_notificacion_de_brechas_a_la_aepd.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-213'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE NOTIFICACIÓN DE BRECHAS A LA AEPD'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E213_procedimiento_de_notificacion_de_brechas_a_la_aepd.md').read_text(encoding="utf-8")
