"""Template E-204-A — PROCEDIMIENTO DE RECOPILACIÓN Y CUSTODIA DE EVIDENCIAS.

Source: docs/spec/F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md.
Body loaded literally from E204A_procedimiento_de_recopilacion_y_custodia_de_eviden.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-204-A'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE RECOPILACIÓN Y CUSTODIA DE EVIDENCIAS'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E204A_procedimiento_de_recopilacion_y_custodia_de_eviden.md').read_text(encoding="utf-8")
