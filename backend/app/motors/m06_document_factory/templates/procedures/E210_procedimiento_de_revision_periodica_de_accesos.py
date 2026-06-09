"""Template E-210 — PROCEDIMIENTO DE REVISIÓN PERIÓDICA DE ACCESOS.

Source: docs/spec/CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md.
Body loaded literally from E210_procedimiento_de_revision_periodica_de_accesos.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-210'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE REVISIÓN PERIÓDICA DE ACCESOS'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E210_procedimiento_de_revision_periodica_de_accesos.md').read_text(encoding="utf-8")
