"""Template C-003 — CONTRATO DE SERVICIOS DE MANTENIMIENTO CONTINUO (RETAINER POST-CERTIFICACIÓN).

Source: docs/spec/F3_1_PLANTILLAS_COMERCIALES_P001_C001_C003 (1).md.
Body loaded literally from C003_contrato_de_servicios_de_mantenimiento_continuo_re.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'C-003'
TEMPLATE_TITLE = 'CONTRATO DE SERVICIOS DE MANTENIMIENTO CONTINUO (RETAINER POST-CERTIFICACIÓN)'
TEMPLATE_TYPE = 'commercial'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F3_1_PLANTILLAS_COMERCIALES_P001_C001_C003 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'C003_contrato_de_servicios_de_mantenimiento_continuo_re.md').read_text(encoding="utf-8")
