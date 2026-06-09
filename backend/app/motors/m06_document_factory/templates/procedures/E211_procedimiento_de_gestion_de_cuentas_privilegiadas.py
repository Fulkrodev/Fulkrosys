"""Template E-211 — PROCEDIMIENTO DE GESTIÓN DE CUENTAS PRIVILEGIADAS.

Source: docs/spec/CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md.
Body loaded literally from E211_procedimiento_de_gestion_de_cuentas_privilegiadas.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-211'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE GESTIÓN DE CUENTAS PRIVILEGIADAS'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E211_procedimiento_de_gestion_de_cuentas_privilegiadas.md').read_text(encoding="utf-8")
