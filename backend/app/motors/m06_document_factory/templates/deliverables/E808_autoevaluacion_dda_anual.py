"""Template E-808 — AUTOEVALUACIÓN ANUAL DE LA DECLARACIÓN DE APLICABILIDAD.

#4 Ola 8 · artefacto del ciclo de revisión anual del AR/DdA (mantenimiento ·
CCN-STIC 808). Lo genera el flujo annual_review (m03_dda) / execute_activity
'revision_ar_dda'. Body loaded literally from the .md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-808'
TEMPLATE_TITLE = 'AUTOEVALUACIÓN ANUAL DE LA DECLARACIÓN DE APLICABILIDAD'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '#4 Ola8 revision anual AR/DdA'

TEMPLATE_BODY = (
    Path(__file__).parent / 'E808_autoevaluacion_dda_anual.md'
).read_text(encoding="utf-8")
