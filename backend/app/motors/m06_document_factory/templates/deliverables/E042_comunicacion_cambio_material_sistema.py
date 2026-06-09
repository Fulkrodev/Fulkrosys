"""Template E-042 — COMUNICACIÓN DE CAMBIO MATERIAL EN EL SISTEMA.

Source: sub-atom 1.B.9.B ruta basica lifecycle.
Body loaded literally from E042_comunicacion_cambio_material_sistema.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-042'
TEMPLATE_TITLE = 'COMUNICACIÓN DE CAMBIO MATERIAL EN EL SISTEMA'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1B9B_ruta_basica_lifecycle.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E042_comunicacion_cambio_material_sistema.md').read_text(encoding="utf-8")
