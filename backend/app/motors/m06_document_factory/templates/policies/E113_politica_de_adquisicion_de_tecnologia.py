"""Template E-113 — POLÍTICA DE ADQUISICIÓN DE TECNOLOGÍA.

Source: docs/spec/CORRECCION_5B_12_POLITICAS_RESTANTES.md.
Body loaded literally from E113_politica_de_adquisicion_de_tecnologia.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-113'
TEMPLATE_TITLE = 'POLÍTICA DE ADQUISICIÓN DE TECNOLOGÍA'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5B_12_POLITICAS_RESTANTES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E113_politica_de_adquisicion_de_tecnologia.md').read_text(encoding="utf-8")
