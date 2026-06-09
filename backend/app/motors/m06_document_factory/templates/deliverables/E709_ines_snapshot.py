"""E-709 INFORME INES SNAPSHOT ANUAL DEL ESTADO DEL ENS.

Sub-lote 1.B.4 TECNICOS · architect-curated VERBATIM · ENS Art.35 + CCN-STIC-824 + plataforma INES CCN.
"""
from pathlib import Path

TEMPLATE_ID = "E-709"
TEMPLATE_TITLE = "INFORME INES SNAPSHOT ANUAL DEL ESTADO DEL ENS"
TEMPLATE_TYPE = "deliverables"
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = "FULKRO architect curated · sub-lote 1.B.4"
TEMPLATE_BODY = (Path(__file__).parent / "E709_ines_snapshot.md").read_text(encoding="utf-8")
