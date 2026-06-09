"""Template E-001 — FICHA RESUMEN EJECUTIVO DEL PROYECTO ENS.

Source: docs/spec/F3_2_PLANTILLAS_ENTREGABLES_E001_E040_E050_E400 (1).md.
Body loaded literally from E001_ficha_resumen_ejecutivo_del_proyecto_ens.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-001'
TEMPLATE_TITLE = 'FICHA RESUMEN EJECUTIVO DEL PROYECTO ENS'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F3_2_PLANTILLAS_ENTREGABLES_E001_E040_E050_E400 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E001_ficha_resumen_ejecutivo_del_proyecto_ens.md').read_text(encoding="utf-8")
