"""Template E-223 — PROCEDIMIENTO DE REVISIÓN DE LOGS.

Source: docs/spec/procedures/E223_PROCEDIMIENTO_REVISION_LOGS.md.
Body loaded literally from E223_procedimiento_de_revision_de_logs.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-223'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE REVISIÓN DE LOGS'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E223_PROCEDIMIENTO_REVISION_LOGS.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E223_procedimiento_de_revision_de_logs.md').read_text(encoding="utf-8")
