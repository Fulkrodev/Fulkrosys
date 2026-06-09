"""Template E-002 — ACTA DE NOMBRAMIENTO DE ROLES DEL SISTEMA (ENS).

Source: sub-atom 1.B.9.A governance SGSI core.
Body loaded literally from E002_acta_nombramiento_roles_ens.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-002'
TEMPLATE_TITLE = 'ACTA DE NOMBRAMIENTO DE ROLES DEL SISTEMA (ENS)'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1B9A_governance_SGSI_core.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E002_acta_nombramiento_roles_ens.md').read_text(encoding="utf-8")
