"""Template E-150 — PLAN DE ADECUACIÓN AL ENS.

Source: FULKRO architect curated · sub-atom 1.D.F.tris.B-bis.
Body loaded literally from E150_plan_adecuacion.md (Jinja2 + docxtpl).

Variables required (contexto Jinja2):
- client_name, system_name, system_category, version, today, psi_version, template_version
- information_types[] (name, description)
- services[] (name, description)
- dimensions[] (code, name, level, justification)
- dda_total, dda_aplicables, dda_con_refuerzos, dda_no_aplica
- risk_scenarios_count
- gap_summary[] (family, aplicables, conformes, no_conformes, pct_conformidad)
- plan_tasks[] (code, title, ens_measure, responsible_role, priority,
  effort_hours, target_date, cost_eur, description)
- training_plan (sessions_count, lms_provider, next_session_date) or None
"""
from pathlib import Path

TEMPLATE_ID = 'E-150'
TEMPLATE_TITLE = 'PLAN DE ADECUACIÓN AL ENS'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1DFtrisBbis_SGSI_core_curated.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E150_plan_adecuacion.md').read_text(encoding="utf-8")
