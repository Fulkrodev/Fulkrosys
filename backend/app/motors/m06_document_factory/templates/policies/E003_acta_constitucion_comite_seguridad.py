"""Template E-003 — ACTA DE CONSTITUCIÓN DEL COMITÉ DE SEGURIDAD DE LA INFORMACIÓN.

Source: sub-atom 1.B.9.A governance SGSI core.
Body loaded literally from E003_acta_constitucion_comite_seguridad.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-003'
TEMPLATE_TITLE = 'ACTA DE CONSTITUCIÓN DEL COMITÉ DE SEGURIDAD DE LA INFORMACIÓN'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1B9A_governance_SGSI_core.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E003_acta_constitucion_comite_seguridad.md').read_text(encoding="utf-8")
