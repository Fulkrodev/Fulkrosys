"""Template E-112 — POLÍTICA DE SEGURIDAD EN LAS RELACIONES CON PROVEEDORES.

Source: docs/spec/F1_2_POLITICAS_CRITICAS_E105_E108 (1).md.
Body loaded literally from E112_politica_de_seguridad_en_las_relaciones_con_provee.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-112'
TEMPLATE_TITLE = 'POLÍTICA DE SEGURIDAD EN LAS RELACIONES CON PROVEEDORES'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F1_2_POLITICAS_CRITICAS_E105_E108 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E112_politica_de_seguridad_en_las_relaciones_con_provee.md').read_text(encoding="utf-8")
