"""Template E-702 - INFORME DE VERIFICACION TECNICA.

Source: M8 v5.1 Checkpoint 3 (spec §5.1). Body loaded literally from
E702_informe_verificacion_tecnica.md.
"""
from pathlib import Path

TEMPLATE_ID = 'E-702'
TEMPLATE_TITLE = 'INFORME DE VERIFICACION TECNICA'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = '1.0'
TEMPLATE_SOURCE_FILE = 'm08_verification_checkpoint_3_spec.md'

TEMPLATE_BODY = (
    Path(__file__).parent / 'E702_informe_verificacion_tecnica.md'
).read_text(encoding='utf-8')
