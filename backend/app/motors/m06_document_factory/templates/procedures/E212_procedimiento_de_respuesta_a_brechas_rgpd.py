"""Template E-212 — PROCEDIMIENTO DE RESPUESTA A BRECHAS RGPD.

Source: docs/spec/CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md.
Body loaded literally from E212_procedimiento_de_respuesta_a_brechas_rgpd.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-212'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE RESPUESTA A BRECHAS RGPD'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E212_procedimiento_de_respuesta_a_brechas_rgpd.md').read_text(encoding="utf-8")
