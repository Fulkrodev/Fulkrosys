"""Template E-170 — PLAN DIRECTOR DE SEGURIDAD (TRIANUAL).

Source: FULKRO architect curated · sub-atom 1.D.F.tris.B-bis.
Body loaded literally from E170_plan_director.md (Jinja2 + docxtpl).

Variables required (contexto Jinja2):
- client_name, year_start, year_end, year_start_plus_1, version, today, template_version
- target_maturity_level, target_cmm, target_cmm_y2
- kpi_y1, kpi_y2_level, kpi_disponibilidad, kpi_mttr, kpi_cumplimiento, kpi_madurez
- strategic_lines[] (title, description)
- capex_y1, opex_y1, total_y1, capex_y2, opex_y2, total_y2, capex_y3, opex_y3, total_y3
- total_3y
- sponsor_name, comite_chair, rseg_name
"""
from pathlib import Path

TEMPLATE_ID = 'E-170'
TEMPLATE_TITLE = 'PLAN DIRECTOR DE SEGURIDAD (TRIANUAL)'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1DFtrisBbis_SGSI_core_curated.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E170_plan_director.md').read_text(encoding="utf-8")
