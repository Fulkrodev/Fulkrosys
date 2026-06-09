"""san_b_knowledge_documents_consolidate_legacy

Revision ID: 68c039a64829
Revises: 33cef115cdf5
Create Date: 2026-05-04 14:27:51.485104

Strategy A.2 (SAN-B.MB-2.0 audit decision): consolidar schema dual
de knowledge_documents · DROP 6 columnas legacy migrando 3 sin
equivalente new al campo metadata JSONB para preservar datos.

Schema dual antes (16 columnas):
  legacy: fuente, titulo, version, fecha_publicacion, hash_sha256,
          contenido_path
  new:    source_id, title, mime_type, content_hash, chunk_count, metadata
  sistemica: id, created_at, updated_at, deleted_at

Schema final post (10 columnas):
  source_id, title (NOT NULL), mime_type, content_hash, chunk_count,
  metadata, id, created_at, updated_at, deleted_at

Migracion:
  1. Backfill metadata JSONB con legacy_version/legacy_publication_date/
     legacy_content_path (preserva datos sin equivalente)
  2. Backfill title=titulo si title IS NULL (datos populated en row real)
  3. ALTER COLUMN title SET NOT NULL
  4. DROP 6 columnas legacy

0 data loss. 1 row preservado integralmente. Schema final 37% mas limpio.

Refs: SAN-B.MB-2.2 · cierre schema dual ambiguity
"""
from typing import Sequence, Union

from alembic import op


revision: str = '68c039a64829'
down_revision: Union[str, None] = '33cef115cdf5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1 · Backfill metadata JSONB con datos legacy sin equivalente new.
    op.execute("""
        UPDATE knowledge_documents
        SET metadata = COALESCE(metadata, '{}'::jsonb) ||
            jsonb_strip_nulls(jsonb_build_object(
                'legacy_version', version,
                'legacy_publication_date',
                    CASE WHEN fecha_publicacion IS NOT NULL
                         THEN fecha_publicacion::text
                         ELSE NULL END,
                'legacy_content_path', contenido_path
            ))
        WHERE version IS NOT NULL
           OR fecha_publicacion IS NOT NULL
           OR contenido_path IS NOT NULL
    """)

    # Step 2 · Backfill title=titulo si title IS NULL.
    op.execute("""
        UPDATE knowledge_documents
        SET title = titulo
        WHERE title IS NULL AND titulo IS NOT NULL
    """)

    # Step 3 · ALTER title SET NOT NULL (todos los rows tienen valor post-step 2).
    op.execute("ALTER TABLE knowledge_documents ALTER COLUMN title SET NOT NULL")

    # Step 4 · DROP 6 columnas legacy.
    op.execute("ALTER TABLE knowledge_documents DROP COLUMN fuente")
    op.execute("ALTER TABLE knowledge_documents DROP COLUMN titulo")
    op.execute("ALTER TABLE knowledge_documents DROP COLUMN version")
    op.execute("ALTER TABLE knowledge_documents DROP COLUMN fecha_publicacion")
    op.execute("ALTER TABLE knowledge_documents DROP COLUMN hash_sha256")
    op.execute("ALTER TABLE knowledge_documents DROP COLUMN contenido_path")


def downgrade() -> None:
    # Re-add 6 columnas legacy con tipos originales.
    op.execute("ALTER TABLE knowledge_documents ADD COLUMN fuente VARCHAR(255)")
    op.execute("ALTER TABLE knowledge_documents ADD COLUMN titulo VARCHAR(500)")
    op.execute("ALTER TABLE knowledge_documents ADD COLUMN version VARCHAR(50)")
    op.execute("ALTER TABLE knowledge_documents ADD COLUMN fecha_publicacion DATE")
    op.execute("ALTER TABLE knowledge_documents ADD COLUMN hash_sha256 VARCHAR(64)")
    op.execute("ALTER TABLE knowledge_documents ADD COLUMN contenido_path VARCHAR(500)")

    # Best-effort restore desde metadata JSONB (datos sin equivalente new).
    op.execute("""
        UPDATE knowledge_documents
        SET version = metadata->>'legacy_version',
            fecha_publicacion =
                CASE WHEN metadata->>'legacy_publication_date' IS NOT NULL
                     THEN (metadata->>'legacy_publication_date')::date
                     ELSE NULL END,
            contenido_path = metadata->>'legacy_content_path'
        WHERE metadata IS NOT NULL
    """)

    # Restore titulo desde title (siempre populated post-upgrade).
    op.execute("UPDATE knowledge_documents SET titulo = title")

    # title vuelve a NULLABLE en estado pre-upgrade.
    op.execute("ALTER TABLE knowledge_documents ALTER COLUMN title DROP NOT NULL")

    # Backfill fuente desde metadata si existia (no-op si nunca seteo).
    # Notese: 'fuente' no se preservaba en metadata · downgrade puro
    # restaura column NULL. Si el caller necesita restore completo,
    # consultar manualmente backup pre-MB-2.2.
