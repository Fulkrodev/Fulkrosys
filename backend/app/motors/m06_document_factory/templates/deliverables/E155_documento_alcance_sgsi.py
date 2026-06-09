"""Template E-155 — DOCUMENTO DE ALCANCE DEL SGSI.

Entregable de gobierno FASE 0 (CCN-STIC 805/809) que delimita el alcance del
SGSI: sistemas, servicios, sedes, activos esenciales y exclusiones justificadas.
Ejecutable 8 Pasada 16 (F-14-05).

NOTA: el wording normativo del cuerpo (.md) marcado con `⚠ REVISIÓN CONSULTOR`
es un BORRADOR genérico y debe ser validado por el consultor antes de emitirse a
un cliente real. Los datos per-proyecto se inyectan vía placeholders Jinja2.
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
