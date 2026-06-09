"""E-707 INFORME DE PRUEBA DE RESTAURACION DESDE COPIA DE SEGURIDAD.

Sub-lote 1.B.4 TECNICOS · architect-curated VERBATIM · ENS mp.info.6 + op.cont.3 + op.exp.10 + CCN-STIC-808.
"""
from pathlib import Path

TEMPLATE_ID = "E-707"
TEMPLATE_TITLE = "INFORME DE PRUEBA DE RESTAURACION DESDE COPIA DE SEGURIDAD"
TEMPLATE_TYPE = "deliverables"
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = "FULKRO architect curated · sub-lote 1.B.4"
TEMPLATE_BODY = (Path(__file__).parent / "E707_informe_restauracion_backup.md").read_text(encoding="utf-8")
