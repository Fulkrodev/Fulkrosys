"""Template E-160 — MANUAL DEL SGSI.

Source: FULKRO architect curated · sub-atom 1.D.F.tris.B-bis.
Body loaded literally from E160_manual_sgsi.md (Jinja2 + docxtpl).

Variables required (contexto Jinja2):
- client_name, system_name, system_category, version, today, template_version
- services_summary, assets_essential_count, exclusions_text, psi_version
- roles_table[] (role_name, person, email, functions)
"""
from pathlib import Path

TEMPLATE_ID = 'E-160'
TEMPLATE_TITLE = 'MANUAL DEL SGSI'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1DFtrisBbis_SGSI_core_curated.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E160_manual_sgsi.md').read_text(encoding="utf-8")
