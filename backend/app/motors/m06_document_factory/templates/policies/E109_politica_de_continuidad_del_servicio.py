"""Template E-109 — POLÍTICA DE CONTINUIDAD DEL SERVICIO.

Source: docs/spec/F1_1_POLITICAS_CRITICAS_E100_E104 (1).md.
Body loaded literally from E109_politica_de_continuidad_del_servicio.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-109'
TEMPLATE_TITLE = 'POLÍTICA DE CONTINUIDAD DEL SERVICIO'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F1_1_POLITICAS_CRITICAS_E100_E104 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E109_politica_de_continuidad_del_servicio.md').read_text(encoding="utf-8")
