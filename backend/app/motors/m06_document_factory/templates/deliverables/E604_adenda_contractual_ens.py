"""Template E-604 — ADENDA CONTRACTUAL DE CUMPLIMIENTO ENS / RGPD / NIS2 / DORA.

Source: Sub-lote 1.B.7.1.1 architect-VERBATIM curated · reactivated 1.D.I
scope reorder pre-1.E (FULKRO empresa privada · supply chain ENS op.ext.*).

Body loaded literally from E604_adenda_contractual_ens.md (Jinja2 + docxtpl).
Cubre ENS op.ext.1 (Contratación + SLAs) + op.ext.4 (Interconexión) · adenda
multi-norma con branches RGPD + NIS2 + DORA + AI Act + notificacion_horas
per regulation + seguro_cuantia_eur.

Variables required: adenda + contrato_base + proveedor.normativas_aplicables[]
list + cliente.representante + notificacion_horas/notificacion_horas_nis2/
notificacion_horas_rgpd/seguro_cuantia_eur.

Complementaria a wizard frontend M14 1.D.D.A (`/admin/projects/[id]/contratos`)
que ya cubre generate workflow C-001/C-003/C-004 vía m14_contracts admin UI.
E-604 expone plantilla directamente para casos sin wizard (manual ad-hoc).
"""
from pathlib import Path

TEMPLATE_ID = 'E-604'
TEMPLATE_TITLE = 'ADENDA CONTRACTUAL DE CUMPLIMIENTO ENS / RGPD / NIS2 / DORA'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '1B711_proveedores_architect_VERBATIM.md'

TEMPLATE_BODY = (Path(__file__).parent / 'E604_adenda_contractual_ens.md').read_text(encoding="utf-8")
