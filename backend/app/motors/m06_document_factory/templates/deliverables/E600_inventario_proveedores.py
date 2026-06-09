"""Template E-600 — INVENTARIO DE PROVEEDORES ENS.

Source: Sub-lote 1.B.7.1.1 architect-VERBATIM curated · reactivated 1.D.I
scope reorder pre-1.E (FULKRO empresa privada · supply chain ENS op.ext.*).

Body loaded literally from E600_inventario_proveedores.md (Jinja2 + docxtpl).
Cubre ENS op.ext.1 (Contratación + SLAs) + op.ext.3 (Cadena suministro).

Variables required: proveedores[] list + cliente + selectattr filters
(count_criticos/altos/medios/bajos/encargados_rgpd/pendientes_eval/con_adenda).
Fixture canonical en conftest_proveedores.py (AMEND-012 target empresa privada).
"""
from pathlib import Path

TEMPLATE_ID = 'E-600'
TEMPLATE_TITLE = 'INVENTARIO DE PROVEEDORES ENS'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1B711_proveedores_architect_VERBATIM.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E600_inventario_proveedores.md').read_text(encoding="utf-8")
