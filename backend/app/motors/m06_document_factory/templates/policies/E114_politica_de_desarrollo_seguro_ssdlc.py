"""Template E-114 — POLÍTICA DE DESARROLLO SEGURO (SSDLC).

Source: docs/spec/CORRECCION_5B_12_POLITICAS_RESTANTES.md.
Body loaded literally from E114_politica_de_desarrollo_seguro_ssdlc.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-114'
TEMPLATE_TITLE = 'POLÍTICA DE DESARROLLO SEGURO (SSDLC)'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5B_12_POLITICAS_RESTANTES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E114_politica_de_desarrollo_seguro_ssdlc.md').read_text(encoding="utf-8")
