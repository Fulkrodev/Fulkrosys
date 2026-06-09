"""E-705 INFORME FORMAL DE CAMPANA DE PHISHING.

Sub-lote 1.B.4 TECNICOS · architect-curated VERBATIM · ENS mp.per.3/4 + NIS2 Art.21.2 + DORA Art.24-26 + CCN-STIC-481.
"""
from pathlib import Path

TEMPLATE_ID = "E-705"
TEMPLATE_TITLE = "INFORME FORMAL DE CAMPANA DE PHISHING"
TEMPLATE_TYPE = "deliverables"
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = "FULKRO architect curated · sub-lote 1.B.4"
TEMPLATE_BODY = (Path(__file__).parent / "E705_informe_formal_campania_phishing.md").read_text(encoding="utf-8")
