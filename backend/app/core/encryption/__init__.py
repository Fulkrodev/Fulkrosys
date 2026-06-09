"""FULKRO encryption primitives · field-level Fernet at-rest.

Public API:
- ``get_master_fernet()`` → MultiFernet (rotación-aware)
- ``EncryptedText`` SQLAlchemy TypeDecorator para columnas TEXT cifradas
- ``reset_master_fernet_cache()`` para tests

Refs: ADR-032 · SAN-B.MB-3.ter.4
"""
from backend.app.core.encryption.master_key import (
    get_master_fernet,
    reset_master_fernet_cache,
)
from backend.app.core.encryption.sqlalchemy_types import EncryptedText


__all__ = [
    "get_master_fernet",
    "reset_master_fernet_cache",
    "EncryptedText",
]
