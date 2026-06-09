"""Template E-217 — PROCEDIMIENTO DE EVALUACIÓN Y SEGUIMIENTO DE PROVEEDORES.

Source: docs/spec/F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md.
Body loaded literally from E217_procedimiento_de_evaluacion_y_seguimiento_de_prove.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-217'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE EVALUACIÓN Y SEGUIMIENTO DE PROVEEDORES'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E217_procedimiento_de_evaluacion_y_seguimiento_de_prove.md').read_text(encoding="utf-8")
