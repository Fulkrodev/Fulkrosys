"""Template E-221 — PROCEDIMIENTO DE GESTIÓN DE LA INFORMACIÓN DOCUMENTADA DEL SGSI.

Source: docs/spec/F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md.
Body loaded literally from E221_procedimiento_de_gestion_de_la_informacion_documen.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-221'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE GESTIÓN DE LA INFORMACIÓN DOCUMENTADA DEL SGSI'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E221_procedimiento_de_gestion_de_la_informacion_documen.md').read_text(encoding="utf-8")
