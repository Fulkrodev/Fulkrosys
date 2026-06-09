"""E-500 PLAN ANUAL DE FORMACION Y CONCIENCIACION.

Sub-lote 1.B.3 LMS · architect-curated VERBATIM (mp.per.3 + mp.per.4 + G1-G6 + KPIs).
Cierra GAP CRITICO 5 plan v2 §14.1 (OPCION B · Moodle externo · ver ADR-LMS-001).
"""
from pathlib import Path

TEMPLATE_ID = "E-500"
TEMPLATE_TITLE = "PLAN ANUAL DE FORMACION Y CONCIENCIACION"
TEMPLATE_TYPE = "deliverables"
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = "FULKRO architect curated · sub-lote 1.B.3"
TEMPLATE_BODY = (Path(__file__).parent / "E500_plan_anual_formacion.md").read_text(encoding="utf-8")
