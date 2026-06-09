"""Template E-103 — POLÍTICA DE USO ACEPTABLE DE LOS RECURSOS.

Source: docs/spec/F1_2_POLITICAS_CRITICAS_E105_E108 (1).md.
Body loaded literally from E103_politica_de_uso_aceptable_de_los_recursos.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-103'
TEMPLATE_TITLE = 'POLÍTICA DE USO ACEPTABLE DE LOS RECURSOS'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F1_2_POLITICAS_CRITICAS_E105_E108 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E103_politica_de_uso_aceptable_de_los_recursos.md').read_text(encoding="utf-8")
