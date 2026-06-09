"""Template E-040 — INFORME FINAL DE ADECUACIÓN AL ENS.

Source: docs/spec/F3_2_PLANTILLAS_ENTREGABLES_E001_E040_E050_E400 (1).md.
Body loaded literally from E040_informe_final_de_adecuacion_al_ens.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-040'
TEMPLATE_TITLE = 'INFORME FINAL DE ADECUACIÓN AL ENS'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F3_2_PLANTILLAS_ENTREGABLES_E001_E040_E050_E400 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E040_informe_final_de_adecuacion_al_ens.md').read_text(encoding="utf-8")
