"""Template E-050 — INFORME DE AUDITORÍA INTERNA DEL SGSI.

Source: docs/spec/F3_2_PLANTILLAS_ENTREGABLES_E001_E040_E050_E400 (1).md.
Body loaded literally from E050_informe_de_auditoria_interna_del_sgsi.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-050'
TEMPLATE_TITLE = 'INFORME DE AUDITORÍA INTERNA DEL SGSI'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F3_2_PLANTILLAS_ENTREGABLES_E001_E040_E050_E400 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E050_informe_de_auditoria_interna_del_sgsi.md').read_text(encoding="utf-8")
