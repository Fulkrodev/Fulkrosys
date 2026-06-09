"""E-503 INFORME DE SIMULACROS DE PHISHING.

Sub-lote 1.B.3 LMS · architect-curated VERBATIM · GoPhish + 7 secciones + acciones individuales.
"""
from pathlib import Path

TEMPLATE_ID = "E-503"
TEMPLATE_TITLE = "INFORME DE SIMULACROS DE PHISHING"
TEMPLATE_TYPE = "deliverables"
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = "FULKRO architect curated · sub-lote 1.B.3"
TEMPLATE_BODY = (Path(__file__).parent / "E503_informe_simulacros_phishing.md").read_text(encoding="utf-8")
