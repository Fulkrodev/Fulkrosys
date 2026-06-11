"""Template E-155 — DOCUMENTO DE ALCANCE DEL SGSI.

Entregable de gobierno FASE 0 (CCN-STIC 805/809) que delimita el alcance del
SGSI: sistemas, servicios (finalistas/instrumentales), sedes (físicas/cloud),
activos esenciales y exclusiones justificadas.

Los datos per-proyecto los agrega ``build_e155_alcance_context`` (R05) desde el
dominio m01 (systems + services + information_types) y las tablas ``system_sites``
+ ``scope_exclusions``, con las dimensiones DICAT reales (regla del máximo). El
gate ``E155ScopeEmptyError`` impide emitir un alcance sin definir.
"""
from pathlib import Path

TEMPLATE_ID = 'E-155'
TEMPLATE_TITLE = 'DOCUMENTO DE ALCANCE DEL SGSI'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = 'CCN-STIC-805_809_alcance_sgsi'

TEMPLATE_BODY = (
    Path(__file__).parent / 'E155_documento_alcance_sgsi.md'
).read_text(encoding="utf-8")
