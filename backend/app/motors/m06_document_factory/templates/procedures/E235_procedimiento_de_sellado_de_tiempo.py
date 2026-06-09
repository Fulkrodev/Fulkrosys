"""Template E-235 — PROCEDIMIENTO DE SELLADO DE TIEMPO (#37 mp.info.5).

Materializa la medida mp.info.5 (Sellos de tiempo) del Anexo II del RD 311/2022,
refuerzo exigible solo a categoria ALTA. Procedimiento documentado ahora; la TSA
cualificada eIDAS / RFC 3161 se contrata e integra en el primer proyecto ALTA
(ver Future-X radar/sellado). Body cargado literal del .md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-235'
TEMPLATE_TITLE = 'PROCEDIMIENTO DE SELLADO DE TIEMPO'
TEMPLATE_TYPE = 'procedures'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'E235_PROCEDIMIENTO_SELLADO_DE_TIEMPO.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E235_procedimiento_de_sellado_de_tiempo.md').read_text(encoding="utf-8")
