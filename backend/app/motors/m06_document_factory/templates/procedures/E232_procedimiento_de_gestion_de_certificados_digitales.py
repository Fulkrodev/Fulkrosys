"""Template E-232 — PROCEDIMIENTO DE GESTIÓN DE CERTIFICADOS DIGITALES.

Source: docs/spec/procedures/E232_PROCEDIMIENTO_GESTION_CERTIFICADOS_DIGITALES.md.
Body loaded literally from E232_procedimiento_de_gestion_de_certificados_digitales.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-232'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE GESTIÓN DE CERTIFICADOS DIGITALES'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E232_PROCEDIMIENTO_GESTION_CERTIFICADOS_DIGITALES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E232_procedimiento_de_gestion_de_certificados_digitales.md').read_text(encoding="utf-8")
