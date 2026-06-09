"""E-706 INFORME DE EJERCICIO TABLETOP DE GESTION DE INCIDENTE.

Sub-lote 1.B.4 TECNICOS · architect-curated VERBATIM · ENS op.exp.7 + RGPD Art.33-34 + NIS2 Art.23 + DORA Art.19 + LUCIA CCN-CERT.
"""
from pathlib import Path

TEMPLATE_ID = "E-706"
TEMPLATE_TITLE = "INFORME DE EJERCICIO TABLETOP DE GESTION DE INCIDENTE"
TEMPLATE_TYPE = "deliverables"
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = "FULKRO architect curated · sub-lote 1.B.4"
TEMPLATE_BODY = (Path(__file__).parent / "E706_tabletop_incidente.md").read_text(encoding="utf-8")
