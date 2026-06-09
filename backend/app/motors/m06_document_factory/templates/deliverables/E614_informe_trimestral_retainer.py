"""Template E-614 — INFORME TRIMESTRAL DE RETAINER.

Source: sub-atom 1.B.9.C retainer reporting.
Body loaded literally from E614_informe_trimestral_retainer.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-614'
TEMPLATE_TITLE = 'INFORME TRIMESTRAL DE RETAINER'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1B9C_retainer_reporting.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E614_informe_trimestral_retainer.md').read_text(encoding="utf-8")
