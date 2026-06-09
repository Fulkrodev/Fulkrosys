"""Template E-601 — CUESTIONARIO DE EVALUACIÓN INICIAL DEL PROVEEDOR.

Source: Sub-lote 1.B.7.1.1 architect-VERBATIM curated · reactivated 1.D.I
scope reorder pre-1.E (FULKRO empresa privada · supply chain ENS op.ext.*).

Body loaded literally from E601_cuestionario_onboarding_proveedor.md (Jinja2 + docxtpl).
Cubre ENS op.ext.1 + op.ext.2 + op.ext.3 · 7 secciones A-G (Identif + ENS + RGPD +
NIS2 + DORA + Capacidades + Continuidad) + Declaración + Firmas + Anexos.

Variables required: proveedor + cliente + branches DORA/NIS2/RGPD activables.
Fixture canonical en conftest_proveedores.py.
"""
from pathlib import Path

TEMPLATE_ID = 'E-601'
TEMPLATE_TITLE = 'CUESTIONARIO DE EVALUACIÓN INICIAL DEL PROVEEDOR'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1B711_proveedores_architect_VERBATIM.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E601_cuestionario_onboarding_proveedor.md').read_text(encoding="utf-8")
