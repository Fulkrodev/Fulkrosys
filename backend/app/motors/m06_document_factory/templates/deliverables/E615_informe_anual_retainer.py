"""Template E-615 — INFORME ANUAL DE RETAINER.

Source: sub-atom 1.B.9.C retainer reporting.
Body loaded literally from E615_informe_anual_retainer.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-615'
TEMPLATE_TITLE = 'INFORME ANUAL DE RETAINER'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1B9C_retainer_reporting.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E615_informe_anual_retainer.md').read_text(encoding="utf-8")
