"""Template E-203 — PROCEDIMIENTO DE GESTIÓN DE CAMBIOS.

Source: docs/spec/F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md.
Body loaded literally from E203_procedimiento_de_gestion_de_cambios.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-203'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE GESTIÓN DE CAMBIOS'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E203_procedimiento_de_gestion_de_cambios.md').read_text(encoding="utf-8")
