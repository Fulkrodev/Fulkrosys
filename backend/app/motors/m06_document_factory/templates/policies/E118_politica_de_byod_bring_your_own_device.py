"""Template E-118 — POLÍTICA DE BYOD (Bring Your Own Device).

Source: docs/spec/CORRECCION_5B_12_POLITICAS_RESTANTES.md.
Body loaded literally from E118_politica_de_byod_bring_your_own_device.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-118'
TEMPLATE_TITLE = 'POLÍTICA DE BYOD (Bring Your Own Device)'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5B_12_POLITICAS_RESTANTES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E118_politica_de_byod_bring_your_own_device.md').read_text(encoding="utf-8")
