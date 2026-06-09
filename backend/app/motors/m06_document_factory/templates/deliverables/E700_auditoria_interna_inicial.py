"""E-700 INFORME DE AUDITORIA INTERNA INICIAL DEL SGSI.

Sub-lote 1.B.4 TECNICOS · architect-curated VERBATIM · ENS Art.31 + CCN-STIC-802 + mp.aud.*.
"""
from pathlib import Path

TEMPLATE_ID = "E-700"
TEMPLATE_TITLE = "INFORME DE AUDITORIA INTERNA INICIAL DEL SGSI"
TEMPLATE_TYPE = "deliverables"
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = "FULKRO architect curated · sub-lote 1.B.4"
TEMPLATE_BODY = (Path(__file__).parent / "E700_auditoria_interna_inicial.md").read_text(encoding="utf-8")
