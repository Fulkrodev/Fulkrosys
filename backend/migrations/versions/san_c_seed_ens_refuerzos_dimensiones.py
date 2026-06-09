"""san_c_seed_ens_refuerzos_dimensiones

Revision ID: sancseed091001
Revises: a21d00000001
Create Date: 2026-05-05 11:00:00.000000

Seed canónico ``ens_measure_refuerzos`` (~133 filas · 48 medidas) +
``ens_measure_dimensiones`` (~272 filas · 73 medidas) desde corpus oficial
RD 311/2022 Anexo II ya ingerido (``knowledge_documents`` doc_id
``642e417e-e2c7-4a5c-b263-a6aac74943c5``).

Cierre BLOQUEANTE-3 SAN-C: hasta este punto las dos tablas existían vacías
("diferido Fase alpha.2") · sin esto M03 DdA NO podía diferenciar Básica
vs Media vs Alta correctamente vía refuerzos R1-R9. Crítico para auditoría
externa Media/Alta.

Cada fila refuerzo lleva ``source_chunk_id`` FK a ``knowledge_chunks`` para
trazabilidad ENAC ("muéstrame de dónde sale esto").

La migration es **tolerante a corpus ausente**: si ``knowledge_chunks``
está vacío de RD 311/2022 (DB fresh sin corpus), no-op con warning. El
seed se re-ejecuta manualmente con::

    PYTHONPATH=. python backend/scripts/seed_ens_measure_refuerzos.py

una vez ingerido el corpus.

Refs: SAN-C.MB-9.1 · cierra TODO-S11-ENS-DATA-CANONICAL-DEFER-001 · ADR-029
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence, Union

from alembic import op


revision: str = "sancseed091001"
down_revision: Union[str, None] = "a21d00000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SOURCE_TAG = "BOE-A-2022-7191 Anexo II"
RD_311_DOC_ID = "642e417e-e2c7-4a5c-b263-a6aac74943c5"


def upgrade() -> None:
    """Ejecuta seed canónico si corpus RD 311/2022 está disponible."""
    from sqlalchemy import text as sa_text

    bind = op.get_bind()
    chunks_count = bind.execute(
        sa_text(
            "SELECT count(*) FROM knowledge_chunks "
            "WHERE document_id = :doc_id AND measure_code IS NOT NULL"
        ),
        {"doc_id": RD_311_DOC_ID},
    ).scalar()

    if not chunks_count or chunks_count == 0:
        print(
            f"WARNING SAN-C.MB-9.1: corpus RD 311/2022 vacío en knowledge_chunks "
            f"(doc_id={RD_311_DOC_ID}). Seed diferido · re-ejecutar manualmente: "
            f"`PYTHONPATH=. python backend/scripts/seed_ens_measure_refuerzos.py`"
        )
        return

    # Importa el script seed (se asume monorepo PYTHONPATH bien configurado)
    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.scripts import seed_ens_measure_refuerzos

    rc = seed_ens_measure_refuerzos.main()
    if rc != 0:
        raise RuntimeError(
            f"SAN-C.MB-9.1 seed_ens_measure_refuerzos.main() returned rc={rc}"
        )


def downgrade() -> None:
    """Borra solo las filas insertadas por este seed (las que llevan SOURCE_TAG)."""
    op.execute(
        "DELETE FROM ens_measure_refuerzos "
        f"WHERE metadata ->> 'source' = '{SOURCE_TAG}'"
    )
    op.execute(
        "DELETE FROM ens_measure_dimensiones "
        f"WHERE metadata ->> 'source' = '{SOURCE_TAG}'"
    )
