"""Template E-104 — POLÍTICA DE CLASIFICACIÓN Y TRATAMIENTO DE LA INFORMACIÓN.

Source: docs/spec/F1_2_POLITICAS_CRITICAS_E105_E108 (1).md.
Body loaded literally from E104_politica_de_clasificacion_y_tratamiento_de_la_info.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-104'
TEMPLATE_TITLE = 'POLÍTICA DE CLASIFICACIÓN Y TRATAMIENTO DE LA INFORMACIÓN'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F1_2_POLITICAS_CRITICAS_E105_E108 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E104_politica_de_clasificacion_y_tratamiento_de_la_info.md').read_text(encoding="utf-8")
