"""Template E-233 — PROCEDIMIENTO DE SEGURIDAD EN REDES INALÁMBRICAS.

Source: docs/spec/procedures/E233_PROCEDIMIENTO_SEGURIDAD_REDES_INALAMBRICAS.md.
Body loaded literally from E233_procedimiento_de_seguridad_en_redes_inalambricas.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-233'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE SEGURIDAD EN REDES INALÁMBRICAS'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E233_PROCEDIMIENTO_SEGURIDAD_REDES_INALAMBRICAS.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E233_procedimiento_de_seguridad_en_redes_inalambricas.md').read_text(encoding="utf-8")
