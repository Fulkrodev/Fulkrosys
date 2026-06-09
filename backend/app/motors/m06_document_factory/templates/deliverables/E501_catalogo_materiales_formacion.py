"""E-501 CATALOGO DE MATERIALES DE FORMACION.

Sub-lote 1.B.3 LMS · architect-curated VERBATIM · 24 modulos G1-G6 detallados.
"""
from pathlib import Path

TEMPLATE_ID = "E-501"
TEMPLATE_TITLE = "CATALOGO DE MATERIALES DE FORMACION"
TEMPLATE_TYPE = "deliverables"
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = "FULKRO architect curated · sub-lote 1.B.3"
TEMPLATE_BODY = (Path(__file__).parent / "E501_catalogo_materiales_formacion.md").read_text(encoding="utf-8")
