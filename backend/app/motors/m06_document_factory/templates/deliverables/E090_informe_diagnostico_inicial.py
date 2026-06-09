"""Template E-090 — INFORME DE DIAGNÓSTICO INICIAL · GAP ANALYSIS FRENTE AL ENS.

Source: sub-atom 1.B.9.A governance SGSI core.
Body loaded literally from E090_informe_diagnostico_inicial.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-090'
TEMPLATE_TITLE = 'INFORME DE DIAGNÓSTICO INICIAL · GAP ANALYSIS FRENTE AL ENS'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1B9A_governance_SGSI_core.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E090_informe_diagnostico_inicial.md').read_text(encoding="utf-8")
