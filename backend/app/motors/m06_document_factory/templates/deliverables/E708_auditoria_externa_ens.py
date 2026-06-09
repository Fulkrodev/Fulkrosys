"""E-708 INFORME DE AUDITORIA EXTERNA DEL ENS.

Sub-lote 1.B.4 TECNICOS · architect-curated VERBATIM · ENS Anexo III + CCN-STIC-802/808/809 + ENAC.
"""
from pathlib import Path

TEMPLATE_ID = "E-708"
TEMPLATE_TITLE = "INFORME DE AUDITORIA EXTERNA DEL ENS"
TEMPLATE_TYPE = "deliverables"
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = "FULKRO architect curated · sub-lote 1.B.4"
TEMPLATE_BODY = (Path(__file__).parent / "E708_auditoria_externa_ens.md").read_text(encoding="utf-8")
