"""Template E-100 — POLÍTICA DE SEGURIDAD DE LA INFORMACIÓN.

Source: docs/spec/F1_1_POLITICAS_CRITICAS_E100_E104 (1).md.
Body loaded literally from E100_politica_de_seguridad_de_la_informacion.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-100'
TEMPLATE_TITLE = 'POLÍTICA DE SEGURIDAD DE LA INFORMACIÓN'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F1_1_POLITICAS_CRITICAS_E100_E104 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E100_politica_de_seguridad_de_la_informacion.md').read_text(encoding="utf-8")
