"""Template E-222 — PROCEDIMIENTO DE GESTIÓN DE EXCEPCIONES.

Source: docs/spec/procedures/E222_PROCEDIMIENTO_GESTION_EXCEPCIONES.md.
Body loaded literally from E222_procedimiento_de_gestion_de_excepciones.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-222'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE GESTIÓN DE EXCEPCIONES'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E222_PROCEDIMIENTO_GESTION_EXCEPCIONES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E222_procedimiento_de_gestion_de_excepciones.md').read_text(encoding="utf-8")
