"""san_b_m20_workspace_chat_messages_encryption

Revision ID: 90dd52c1dfd9
Revises: 75c6f519dab6
Create Date: 2026-05-04 16:41:32.720099

Implementa ADR-032: cifrado at-rest Fernet para
``workspace_chat_messages.mensaje``.

Cambios schema:
1. Add column ``encryption_version SMALLINT NOT NULL DEFAULT 1``
   (track key generation activa · soporta key rotation MultiFernet).
2. Backfill ``mensaje`` rows existentes encriptando con
   ``EncryptedText`` (Fernet primary key from
   FULKRO_MASTER_ENCRYPTION_KEY o dev fallback FULKRO_AUTH_PRIVATE_KEY).
   En MVP típicamente 0 rows · backfill no-op pero correcto si rows.

downgrade decifra rows existentes vuelta a plaintext + drop column.

Refs: ADR-032 · SAN-B.MB-3.ter.4 · cierra TODO-M20-CHAT-ENCRYPTION
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '90dd52c1dfd9'
down_revision: Union[str, None] = '75c6f519dab6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Nueva columna encryption_version
    op.add_column(
        "workspace_chat_messages",
        sa.Column(
            "encryption_version",
            sa.SmallInteger(),
            server_default="1",
            nullable=False,
        ),
    )

    # 2. Backfill encrypt rows existentes con plaintext (típicamente 0 rows MVP)
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, mensaje FROM workspace_chat_messages "
        "WHERE mensaje IS NOT NULL"
    )).fetchall()

    if rows:
        # Lazy import para evitar fallo si master key no configurada en
        # contextos edge (init schema sin env vars). Si rows existen,
        # master key DEBE estar configurada.
        from cryptography.fernet import InvalidToken

        from backend.app.core.encryption.master_key import get_master_fernet
        fernet = get_master_fernet()
        for row in rows:
            row_id, plain = row[0], row[1]
            if not isinstance(plain, str):
                continue
            # Idempotencia robusta (re-run safe): si descifra con la master key,
            # ya está cifrado → skip. Try-decrypt en vez de heurística de prefijo
            # "gAAAAA" (un plaintext que empezara por ese prefijo se saltaría el
            # cifrado y quedaría en claro).
            try:
                fernet.decrypt(plain.encode("ascii"))
                continue
            except (InvalidToken, ValueError):
                pass
            encrypted = fernet.encrypt(plain.encode("utf-8")).decode("ascii")
            conn.execute(
                sa.text(
                    "UPDATE workspace_chat_messages "
                    "SET mensaje = :enc WHERE id = :id"
                ),
                {"enc": encrypted, "id": row_id},
            )


def downgrade() -> None:
    # 1. Decifrar rows con plaintext (revert orden)
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, mensaje FROM workspace_chat_messages "
        "WHERE mensaje IS NOT NULL"
    )).fetchall()

    if rows:
        from cryptography.fernet import InvalidToken

        from backend.app.core.encryption.master_key import get_master_fernet
        fernet = get_master_fernet()
        for row in rows:
            row_id, encrypted = row[0], row[1]
            if not isinstance(encrypted, str):
                continue
            # Try-decrypt (sin heurística de prefijo): si descifra, era cifrado
            # → volver a plaintext; si no, ya está en claro / no descifrable con
            # la key actual → skip.
            try:
                plain = fernet.decrypt(encrypted.encode("ascii")).decode("utf-8")
            except (InvalidToken, ValueError):
                continue
            conn.execute(
                sa.text(
                    "UPDATE workspace_chat_messages "
                    "SET mensaje = :p WHERE id = :id"
                ),
                {"p": plain, "id": row_id},
            )

    # 2. Drop column encryption_version
    op.drop_column("workspace_chat_messages", "encryption_version")
