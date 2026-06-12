"""Template E-IT-001 — PROCEDIMIENTO DE HARDENING Y CONFIGURACIÓN SEGURA (R13 · split del 2º bloque jinja de su .md padre).

Materializa op.exp.2 (Configuracion de seguridad) y op.exp.3 (Gestion de la configuracion) del Anexo II del RD 311/2022 + ISO/IEC 27001:2022 A.8.9. Separado a su propio fichero porque vivia como 2º bloque ```jinja
que el compilador descartaba en silencio (remediacion R13). Body literal del .md.
"""
from pathlib import Path

TEMPLATE_ID = 'E-IT-001'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE HARDENING Y CONFIGURACIÓN SEGURA'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md'

TEMPLATE_BODY = (Path(__file__).parent / 'EIT001_procedimiento_hardening_configuracion_segura.md').read_text(encoding="utf-8")
