"""Template C-001 — CONTRATO DE PRESTACIÓN DE SERVICIOS DE CONSULTORÍA ENS.

Source: docs/spec/F3_1_PLANTILLAS_COMERCIALES_P001_C001_C003 (1).md.
Body loaded literally from C001_contrato_de_prestacion_de_servicios_de_consultoria.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'C-001'
TEMPLATE_TITLE = 'CONTRATO DE PRESTACIÓN DE SERVICIOS DE CONSULTORÍA ENS'
TEMPLATE_TYPE = 'commercial'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F3_1_PLANTILLAS_COMERCIALES_P001_C001_C003 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'C001_contrato_de_prestacion_de_servicios_de_consultoria.md').read_text(encoding="utf-8")
