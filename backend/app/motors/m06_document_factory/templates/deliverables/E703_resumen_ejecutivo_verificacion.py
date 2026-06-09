"""Template E-703 - RESUMEN EJECUTIVO DE LA VERIFICACION TECNICA.

Source: M8 v5.1 Checkpoint 3 (spec §5.1). Body loaded literally from
E703_resumen_ejecutivo_verificacion.md.
"""
from pathlib import Path

TEMPLATE_ID = 'E-703'
TEMPLATE_TITLE = 'RESUMEN EJECUTIVO DE LA VERIFICACION TECNICA'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = '1.0'
TEMPLATE_SOURCE_FILE = 'm08_verification_checkpoint_3_spec.md'

TEMPLATE_BODY = (
    Path(__file__).parent / 'E703_resumen_ejecutivo_verificacion.md'
).read_text(encoding='utf-8')
