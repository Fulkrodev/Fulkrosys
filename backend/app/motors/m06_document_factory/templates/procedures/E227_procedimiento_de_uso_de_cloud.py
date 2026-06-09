"""Template E-227 — PROCEDIMIENTO DE USO DE CLOUD.

Source: docs/spec/procedures/E227_PROCEDIMIENTO_USO_CLOUD.md.
Body loaded literally from E227_procedimiento_de_uso_de_cloud.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-227'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE USO DE CLOUD'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E227_PROCEDIMIENTO_USO_CLOUD.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E227_procedimiento_de_uso_de_cloud.md').read_text(encoding="utf-8")
