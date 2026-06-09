"""Template E-108 — POLÍTICA DE GESTIÓN DE INCIDENTES DE SEGURIDAD.

Source: docs/spec/F1_1_POLITICAS_CRITICAS_E100_E104 (1).md.
Body loaded literally from E108_politica_de_gestion_de_incidentes_de_seguridad.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-108'
TEMPLATE_TITLE = 'POLÍTICA DE GESTIÓN DE INCIDENTES DE SEGURIDAD'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F1_1_POLITICAS_CRITICAS_E100_E104 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E108_politica_de_gestion_de_incidentes_de_seguridad.md').read_text(encoding="utf-8")
