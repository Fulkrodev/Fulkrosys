"""Template E-105 — POLÍTICA DE TRATAMIENTO DE DATOS PERSONALES (RGPD).

Source: docs/spec/CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md.
Body loaded literally from E105_politica_de_tratamiento_de_datos_personales_rgpd.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-105'
TEMPLATE_TITLE = 'POLÍTICA DE TRATAMIENTO DE DATOS PERSONALES (RGPD)'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E105_politica_de_tratamiento_de_datos_personales_rgpd.md').read_text(encoding="utf-8")
