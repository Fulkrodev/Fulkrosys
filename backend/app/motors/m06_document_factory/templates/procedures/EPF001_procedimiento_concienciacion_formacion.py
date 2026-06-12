"""Template E-PF-001 — PROCEDIMIENTO DE CONCIENCIACIÓN Y FORMACIÓN EN SEGURIDAD (R13 · split del 2º bloque jinja de su .md padre).

Materializa mp.per.3 (Concienciacion) y mp.per.4 (Formacion) del Anexo II del RD 311/2022 + ISO/IEC 27001:2022 A.6.3. Separado a su propio fichero porque vivia como 2º bloque ```jinja
que el compilador descartaba en silencio (remediacion R13). Body literal del .md.
"""
from pathlib import Path

TEMPLATE_ID = 'E-PF-001'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE CONCIENCIACIÓN Y FORMACIÓN EN SEGURIDAD'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'EPF001_procedimiento_concienciacion_formacion.md').read_text(encoding="utf-8")
