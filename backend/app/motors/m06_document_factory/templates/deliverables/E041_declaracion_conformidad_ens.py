"""Template E-041 — DECLARACIÓN DE CONFORMIDAD CON EL ENS.

Source: sub-atom 1.B.9.B ruta basica lifecycle.
Body loaded literally from E041_declaracion_conformidad_ens.md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-041'
TEMPLATE_TITLE = 'DECLARACIÓN DE CONFORMIDAD CON EL ENS'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1B9B_ruta_basica_lifecycle.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E041_declaracion_conformidad_ens.md').read_text(encoding="utf-8")
