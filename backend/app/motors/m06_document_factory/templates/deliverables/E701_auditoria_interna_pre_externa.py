"""E-701 INFORME DE AUDITORIA INTERNA PRE-EXTERNA.

Sub-lote 1.B.4 TECNICOS · architect-curated VERBATIM · ENS Art.31 + CCN-STIC-802 + mp.aud.*.
"""
from pathlib import Path

TEMPLATE_ID = "E-701"
TEMPLATE_TITLE = "INFORME DE AUDITORIA INTERNA PRE-EXTERNA"
TEMPLATE_TYPE = "deliverables"
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = "FULKRO architect curated · sub-lote 1.B.4"
TEMPLATE_BODY = (Path(__file__).parent / "E701_auditoria_interna_pre_externa.md").read_text(encoding="utf-8")
