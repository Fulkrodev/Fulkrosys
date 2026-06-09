"""Template E-704 - INFORME DE VERIFICACION RED TEAM EXTERNA.

Source: M8 v5.1 Checkpoint 3 (spec §5.1). Body loaded literally from
E704_informe_red_team.md.
"""
from pathlib import Path

TEMPLATE_ID = 'E-704'
TEMPLATE_TITLE = 'INFORME DE VERIFICACION RED TEAM EXTERNA'
TEMPLATE_TYPE = 'deliverables'
TEMPLATE_VERSION = '1.0'
TEMPLATE_SOURCE_FILE = 'm08_verification_checkpoint_3_spec.md'

TEMPLATE_BODY = (
    Path(__file__).parent / 'E704_informe_red_team.md'
).read_text(encoding='utf-8')
