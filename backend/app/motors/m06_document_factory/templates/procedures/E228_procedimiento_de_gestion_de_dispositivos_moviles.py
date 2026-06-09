"""Template E-228 — PROCEDIMIENTO DE GESTIÓN DE DISPOSITIVOS MÓVILES.

Source: docs/spec/procedures/E228_PROCEDIMIENTO_GESTION_DISPOSITIVOS_MOVILES.md.
Body loaded literally from E228_procedimiento_de_gestion_de_dispositivos_moviles.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-228'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE GESTIÓN DE DISPOSITIVOS MÓVILES'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E228_PROCEDIMIENTO_GESTION_DISPOSITIVOS_MOVILES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E228_procedimiento_de_gestion_de_dispositivos_moviles.md').read_text(encoding="utf-8")
