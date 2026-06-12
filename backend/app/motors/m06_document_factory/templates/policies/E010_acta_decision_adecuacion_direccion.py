"""Template E-010 — ACTA DE DECISIÓN DE ADECUACIÓN AL ENS DE LA DIRECCIÓN.

Entregable de gobierno FASE 0 (R24) · materializa la medida org.1 (Política de
seguridad) y el compromiso de la Dirección exigido por el RD 311/2022: la
decisión formal y firmable del órgano de gobierno de impulsar la adecuación al
ENS, aprobar la política, designar roles y dotar recursos. Firmable por la
Dirección (E-signature TIER 1 · m05_signing · SignableType
``acta_decision_direccion``).
"""
from pathlib import Path

TEMPLATE_ID = 'E-010'
TEMPLATE_TITLE = 'ACTA DE DECISIÓN DE ADECUACIÓN AL ENS DE LA DIRECCIÓN'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'RD_311_2022_org1_compromiso_direccion'

TEMPLATE_BODY = (
    Path(__file__).parent / 'E010_acta_decision_adecuacion_direccion.md'
).read_text(encoding="utf-8")
