"""Template E-215 — PROCEDIMIENTO DE GESTIÓN DE SOPORTES EXTRAÍBLES.

Source: docs/spec/procedures/E215_PROCEDIMIENTO_GESTION_SOPORTES_EXTRAIBLES.md.
Body loaded literally from E215_procedimiento_de_gestion_de_soportes_extraibles.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-215'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE GESTIÓN DE SOPORTES EXTRAÍBLES'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E215_PROCEDIMIENTO_GESTION_SOPORTES_EXTRAIBLES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E215_procedimiento_de_gestion_de_soportes_extraibles.md').read_text(encoding="utf-8")
