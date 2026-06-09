"""Template E-220 — PROCEDIMIENTO DE GESTIÓN DE NO CONFORMIDADES.

Source: docs/spec/CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md.
Body loaded literally from E220_procedimiento_de_gestion_de_no_conformidades.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-220'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE GESTIÓN DE NO CONFORMIDADES'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E220_procedimiento_de_gestion_de_no_conformidades.md').read_text(encoding="utf-8")
