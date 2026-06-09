"""SQLAlchemy TypeDecorator · ``EncryptedText`` field-level Fernet at-rest.

Transparent encrypt/decrypt: la app recibe/escribe plaintext, BD
almacena ciphertext URL-safe base64. Migración entre keys vía
``MultiFernet`` (rotation-aware) en master_key.

Refs: ADR-032 · SAN-B.MB-3.ter.4
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.types import Text, TypeDecorator

from backend.app.core.encryption.master_key import get_master_fernet


class EncryptedText(TypeDecorator):
    """TEXT column con Fernet encrypt/decrypt transparente.

    NULL-safe: Python None ↔ SQL NULL sin tocar ciphertext.

    Uso:
        from backend.app.core.encryption import EncryptedText

        class WorkspaceChatMessage(...):
            mensaje: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        return get_master_fernet().encrypt(value.encode("utf-8")).decode("ascii")

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, str):
            value = value.decode("ascii") if isinstance(value, bytes) else str(value)
        return get_master_fernet().decrypt(value.encode("ascii")).decode("utf-8")
