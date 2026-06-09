"""Template E-231 — PROCEDIMIENTO DE GESTIÓN DE CUENTAS Y ACCESOS.

Source: docs/spec/F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md.
Body loaded literally from E231_procedimiento_de_gestion_de_cuentas_y_accesos.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-231'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE GESTIÓN DE CUENTAS Y ACCESOS'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E231_procedimiento_de_gestion_de_cuentas_y_accesos.md').read_text(encoding="utf-8")
