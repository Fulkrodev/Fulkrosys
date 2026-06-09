"""Template E-218 — PROCEDIMIENTO DE AUDITORÍA INTERNA DEL SGSI.

Source: docs/spec/F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md.
Body loaded literally from E218_procedimiento_de_auditoria_interna_del_sgsi.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-218'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE AUDITORÍA INTERNA DEL SGSI'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'E218_procedimiento_de_auditoria_interna_del_sgsi.md').read_text(encoding="utf-8")
