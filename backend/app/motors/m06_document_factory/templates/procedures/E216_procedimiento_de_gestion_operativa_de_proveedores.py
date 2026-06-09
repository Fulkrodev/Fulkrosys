"""Template E-216 — PROCEDIMIENTO DE GESTIÓN OPERATIVA DE PROVEEDORES.

Source: docs/spec/procedures/E216_PROCEDIMIENTO_GESTION_OPERATIVA_PROVEEDORES.md.
Body loaded literally from E216_procedimiento_de_gestion_operativa_de_proveedores.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-216'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE GESTIÓN OPERATIVA DE PROVEEDORES'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E216_PROCEDIMIENTO_GESTION_OPERATIVA_PROVEEDORES.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E216_procedimiento_de_gestion_operativa_de_proveedores.md').read_text(encoding="utf-8")
