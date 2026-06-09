"""Template E-101 — POLÍTICA DE CONTROL DE ACCESO.

Source: docs/spec/F1_1_POLITICAS_CRITICAS_E100_E104 (1).md.
Body loaded literally from E101_politica_de_control_de_acceso.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-101'
TEMPLATE_TITLE = 'POLÍTICA DE CONTROL DE ACCESO'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F1_1_POLITICAS_CRITICAS_E100_E104 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E101_politica_de_control_de_acceso.md').read_text(encoding="utf-8")
