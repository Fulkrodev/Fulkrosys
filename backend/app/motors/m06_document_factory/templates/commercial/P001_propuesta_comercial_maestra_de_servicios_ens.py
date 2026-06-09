"""Template P-001 — PROPUESTA COMERCIAL MAESTRA DE SERVICIOS ENS.

Source: docs/spec/F3_1_PLANTILLAS_COMERCIALES_P001_C001_C003 (1).md.
Body loaded literally from P001_propuesta_comercial_maestra_de_servicios_ens.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'P-001'
TEMPLATE_TITLE = 'PROPUESTA COMERCIAL MAESTRA DE SERVICIOS ENS'
TEMPLATE_TYPE = 'commercial'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F3_1_PLANTILLAS_COMERCIALES_P001_C001_C003 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'P001_propuesta_comercial_maestra_de_servicios_ens.md').read_text(encoding="utf-8")
