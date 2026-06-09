"""Template E-400 — ANÁLISIS DE IMPACTO EN EL NEGOCIO (BIA).

Source: docs/spec/F3_2_PLANTILLAS_ENTREGABLES_E001_E040_E050_E400 (1).md.
Body loaded literally from E400_analisis_de_impacto_en_el_negocio_bia.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-400'
TEMPLATE_TITLE = 'ANÁLISIS DE IMPACTO EN EL NEGOCIO (BIA)'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F3_2_PLANTILLAS_ENTREGABLES_E001_E040_E050_E400 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E400_analisis_de_impacto_en_el_negocio_bia.md').read_text(encoding="utf-8")
