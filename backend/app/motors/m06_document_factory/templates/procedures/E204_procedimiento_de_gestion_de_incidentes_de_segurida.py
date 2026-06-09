"""Template E-204 — PROCEDIMIENTO DE GESTIÓN DE INCIDENTES DE SEGURIDAD.

Source: docs/spec/F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md.
Body loaded literally from E204_procedimiento_de_gestion_de_incidentes_de_segurida.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-204'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE GESTIÓN DE INCIDENTES DE SEGURIDAD'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E204_procedimiento_de_gestion_de_incidentes_de_segurida.md').read_text(encoding="utf-8")
