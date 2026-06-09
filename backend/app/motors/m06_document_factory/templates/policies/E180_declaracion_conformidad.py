"""Template E-180 — DECLARACIÓN DE CONFORMIDAD SGSI (AUTOEVALUACIÓN BÁSICA CCN-STIC 809).

Source: FULKRO architect curated · sub-atom 1.D.F.tris.B-bis.
Body loaded literally from E180_declaracion_conformidad.md (Jinja2 + docxtpl).

Complementaria a E-041 (Declaración Conformidad ENS · certificación ENAC MEDIA/ALTA).
E-180 es ruta AUTOEVALUACIÓN BÁSICA sin entidad certificadora acreditada.

Variables required (contexto Jinja2):
- client_name, client_cif, client_domicilio, system_name, system_category
- cert_id, today, expiry_date, template_version
- services_summary, information_summary, assets_essential_count
- dda_total, dda_aplicables, dda_con_refuerzos, dda_no_aplica
- conformes_count, no_conformes_count, pct_conformidad
- project_id, public_badge_url
- rseg_name, rseg_email
- cliente.sector_aplicacion ('publico' | 'privado' · branch LUCIA obligatorio/recomendado)
"""
from pathlib import Path

TEMPLATE_ID = 'E-180'
TEMPLATE_TITLE = 'DECLARACIÓN DE CONFORMIDAD SGSI (AUTOEVALUACIÓN BÁSICA CCN-STIC 809)'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1DFtrisBbis_SGSI_core_curated.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E180_declaracion_conformidad.md').read_text(encoding="utf-8")
