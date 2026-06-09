"""Template E-117 — POLÍTICA DE GESTIÓN DE PRIVILEGIOS Y PAM.

Source: docs/spec/CORRECCION_5B_12_POLITICAS_RESTANTES.md.
Body loaded literally from E117_politica_de_gestion_de_privilegios_y_pam.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-117'
TEMPLATE_TITLE = 'POLÍTICA DE GESTIÓN DE PRIVILEGIOS Y PAM'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5B_12_POLITICAS_RESTANTES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E117_politica_de_gestion_de_privilegios_y_pam.md').read_text(encoding="utf-8")
