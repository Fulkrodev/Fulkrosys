"""Template E-205 — PROCEDIMIENTO DE GESTIÓN DE VULNERABILIDADES Y PARCHES.

Source: docs/spec/F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md.
Body loaded literally from E205_procedimiento_de_gestion_de_vulnerabilidades_y_par.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-205'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE GESTIÓN DE VULNERABILIDADES Y PARCHES'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E205_procedimiento_de_gestion_de_vulnerabilidades_y_par.md').read_text(encoding="utf-8")
