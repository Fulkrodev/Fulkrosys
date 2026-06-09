"""Template E-127 — POLÍTICA DE REGISTRO DE ACTIVIDAD: RETENCIÓN Y SINCRONIZACIÓN HORARIA.

#1 Ola 7 · artefacto documental de op.exp.8 (retención de registros >=12 meses
+ sincronización horaria/NTP). Lo consume el detector gap_rules op.exp.8 como
política de referencia y el cliente aporta evidencia por medida.
Body loaded literally from the .md (Jinja2 + docxtpl).
"""
from pathlib import Path

TEMPLATE_ID = 'E-127'
TEMPLATE_TITLE = 'POLÍTICA DE REGISTRO DE ACTIVIDAD: RETENCIÓN Y SINCRONIZACIÓN HORARIA'
TEMPLATE_TYPE = 'policies'
TEMPLATE_VERSION = "1.0"
TEMPLATE_SOURCE_FILE = '#1 Ola7 op.exp.8'

TEMPLATE_BODY = (
    Path(__file__).parent
    / 'E127_politica_de_registro_de_actividad_retencion_y_ntp.md'
).read_text(encoding="utf-8")
