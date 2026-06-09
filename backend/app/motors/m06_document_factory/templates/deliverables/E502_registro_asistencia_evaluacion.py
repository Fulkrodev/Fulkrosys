"""E-502 REGISTRO DE ASISTENCIA Y EVALUACION DE LA FORMACION.

Sub-lote 1.B.3 LMS · architect-curated VERBATIM · evidencia trimestral mp.per.3+mp.per.4.
"""
from pathlib import Path

TEMPLATE_ID = "E-502"
TEMPLATE_TITLE = "REGISTRO DE ASISTENCIA Y EVALUACION DE LA FORMACION"
TEMPLATE_TYPE = "deliverables"
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = "FULKRO architect curated · sub-lote 1.B.3"
TEMPLATE_BODY = (Path(__file__).parent / "E502_registro_asistencia_evaluacion.md").read_text(encoding="utf-8")
