"""Template E-120 — POLÍTICA DE GESTIÓN DE CLAVES CRIPTOGRÁFICAS.

Source: docs/spec/CORRECCION_5B_12_POLITICAS_RESTANTES.md.
Body loaded literally from E120_politica_de_gestion_de_claves_criptograficas.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-120'
TEMPLATE_TITLE = 'POLÍTICA DE GESTIÓN DE CLAVES CRIPTOGRÁFICAS'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5B_12_POLITICAS_RESTANTES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E120_politica_de_gestion_de_claves_criptograficas.md').read_text(encoding="utf-8")
