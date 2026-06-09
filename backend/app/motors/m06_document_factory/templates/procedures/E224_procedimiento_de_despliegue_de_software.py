"""Template E-224 — PROCEDIMIENTO DE DESPLIEGUE DE SOFTWARE.

Source: docs/spec/procedures/E224_PROCEDIMIENTO_DESPLIEGUE_SOFTWARE.md.
Body loaded literally from E224_procedimiento_de_despliegue_de_software.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-224'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE DESPLIEGUE DE SOFTWARE'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E224_PROCEDIMIENTO_DESPLIEGUE_SOFTWARE.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E224_procedimiento_de_despliegue_de_software.md').read_text(encoding="utf-8")
