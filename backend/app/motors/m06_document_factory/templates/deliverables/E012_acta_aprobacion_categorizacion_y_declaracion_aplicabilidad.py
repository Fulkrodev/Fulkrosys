"""Template E-012 — ACTA DE APROBACIÓN DE LA CATEGORIZACIÓN Y DECLARACIÓN DE APLICABILIDAD.

Source: sub-atom 1.B.9.A governance SGSI core.
Body loaded literally from E012_acta_aprobacion_categorizacion_y_declaracion_aplicabilidad.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-012'
TEMPLATE_TITLE = 'ACTA DE APROBACIÓN DE LA CATEGORIZACIÓN Y DECLARACIÓN DE APLICABILIDAD'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1B9A_governance_SGSI_core.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E012_acta_aprobacion_categorizacion_y_declaracion_aplicabilidad.md').read_text(encoding="utf-8")
