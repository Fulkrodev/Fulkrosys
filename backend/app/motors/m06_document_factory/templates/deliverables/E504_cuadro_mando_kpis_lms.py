"""E-504 CUADRO DE MANDO DE KPIs DEL PROGRAMA DE FORMACION Y CONCIENCIACION.

Sub-lote 1.B.3 LMS · architect-curated VERBATIM · dashboard consolidado plan E-500.
"""
from pathlib import Path

TEMPLATE_ID = "E-504"
TEMPLATE_TITLE = "CUADRO DE MANDO DE KPIs DEL PROGRAMA DE FORMACION Y CONCIENCIACION"
TEMPLATE_TYPE = "deliverables"
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = "FULKRO architect curated · sub-lote 1.B.3"
TEMPLATE_BODY = (Path(__file__).parent / "E504_cuadro_mando_kpis_lms.md").read_text(encoding="utf-8")
