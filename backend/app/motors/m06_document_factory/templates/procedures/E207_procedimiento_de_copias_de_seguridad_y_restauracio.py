"""Template E-207 — PROCEDIMIENTO DE COPIAS DE SEGURIDAD Y RESTAURACIÓN.

Source: docs/spec/F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md.
Body loaded literally from E207_procedimiento_de_copias_de_seguridad_y_restauracio.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-207'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE COPIAS DE SEGURIDAD Y RESTAURACIÓN'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E207_procedimiento_de_copias_de_seguridad_y_restauracio.md').read_text(encoding="utf-8")
