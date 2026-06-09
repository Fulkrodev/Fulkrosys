"""Template E-107 — POLÍTICA DE CIFRADO Y GESTIÓN DE CLAVES CRIPTOGRÁFICAS.

Source: docs/spec/F1_2_POLITICAS_CRITICAS_E105_E108 (1).md.
Body loaded literally from E107_politica_de_cifrado_y_gestion_de_claves_criptograf.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-107'
TEMPLATE_TITLE = 'POLÍTICA DE CIFRADO Y GESTIÓN DE CLAVES CRIPTOGRÁFICAS'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F1_2_POLITICAS_CRITICAS_E105_E108 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E107_politica_de_cifrado_y_gestion_de_claves_criptograf.md').read_text(encoding="utf-8")
