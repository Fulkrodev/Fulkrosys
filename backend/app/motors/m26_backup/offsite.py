"""Offsite backup upload + retention (ADR-048 · MB-10 Atom 10.6.B).

Combina encryption layer (10.6.A) con MinIO upload pattern existing
(`backend/app/core/storage/minio_client.py`) en helpers high-level:

- ``upload_encrypted_artifact`` · encrypt + upload + return descriptor
- ``download_and_decrypt`` · download + decrypt + write local plaintext
- ``list_offsite_objects`` · list bucket prefix (retention helper)
- ``delete_offsite_object`` · remove from bucket (retention enforcement)
- ``ensure_backup_vault_bucket`` · lazy-create dedicated bucket (private)

Bucket dedicated: ``backup-vault-fulkro`` (`BUCKET_BACKUP_VAULT`).
Q5.3 cement preserved: NO public read policy (private vault).
ISMS §5.5 offsite location distinta · honored literal.

MB-11 cutover Hetzner Object Storage: swap endpoint + credentials env vars ·
bucket name preserved (S3-compatible API · same calls funcionan).
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from minio.error import S3Error

from backend.app.core.storage.minio_client import (
    BUCKET_BACKUP_VAULT,
    get_minio_client,
    get_object,
    put_object,
    remove_object,
)
from backend.app.motors.m26_backup import encryption as backup_enc

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OffsiteUploadResult:
    """Resultado upload encrypted artifact."""

    bucket: str
    key: str
    encryption_key_fingerprint: str
    encrypted_size_bytes: int
    encrypted_sha256: str
    uploaded_at: datetime


def ensure_backup_vault_bucket() -> None:
    """Lazy-create ``backup-vault-fulkro`` bucket (private · no public read).

    Idempotente. Logueado advisory si falla (manual provisioning fallback).
    Pattern matches ``ensure_admin_assets_bucket`` pero SIN public read.
    """
    client = get_minio_client()
    try:
        if client.bucket_exists(BUCKET_BACKUP_VAULT):
            return
        client.make_bucket(BUCKET_BACKUP_VAULT)
        logger.info(
            "Bucket %s creado (private · no public policy · ADR-048)",
            BUCKET_BACKUP_VAULT,
        )
    except S3Error as exc:
        logger.warning(
            "ensure_backup_vault_bucket: no se pudo provisionar %s: %s. "
            "Provisionar manualmente: mc mb local/%s",
            BUCKET_BACKUP_VAULT, exc, BUCKET_BACKUP_VAULT,
        )


def _build_key(backup_type: str, basename: str) -> str:
    """Build canonical bucket key: ``{backup_type}/{yyyymmddTHHMMSS}-{basename}.enc``."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{backup_type}/{ts}-{basename}.enc"


def upload_encrypted_artifact(
    source_path: str | Path,
    backup_type: str,
    *,
    basename: str | None = None,
) -> OffsiteUploadResult:
    """Encrypt + upload backup artifact to offsite bucket.

    Args:
        source_path: Local plaintext file path.
        backup_type: Used as key prefix (e.g. ``postgres_full`` ·
            ``audit_log_export``).
        basename: Optional explicit basename for key. Defaults to
            ``source_path.name``.

    Returns:
        ``OffsiteUploadResult`` with bucket/key/fingerprint/size/sha.
    """
    src = Path(source_path)
    if not src.is_file():
        raise FileNotFoundError(f"Backup source not found: {src}")

    plaintext = src.read_bytes()
    encrypted = backup_enc.encrypt_bytes(plaintext)
    fingerprint = backup_enc.current_key_fingerprint()

    key = _build_key(backup_type, basename or src.name)
    ensure_backup_vault_bucket()

    result = put_object(
        bucket=BUCKET_BACKUP_VAULT,
        key=key,
        data=encrypted,
        content_type="application/octet-stream",
        metadata={
            "encryption_key_fingerprint": fingerprint,
            "backup_type": backup_type,
            "source_filename": src.name,
        },
    )

    return OffsiteUploadResult(
        bucket=BUCKET_BACKUP_VAULT,
        key=key,
        encryption_key_fingerprint=fingerprint,
        encrypted_size_bytes=result.size,
        encrypted_sha256=result.sha256,
        uploaded_at=datetime.now(timezone.utc),
    )


def download_and_decrypt(key: str, dest_path: str | Path) -> Path:
    """Download encrypted object + decrypt + write plaintext local."""
    dst = Path(dest_path)
    token = get_object(BUCKET_BACKUP_VAULT, key)
    plaintext = backup_enc.decrypt_bytes(token)
    dst.write_bytes(plaintext)
    return dst


def list_offsite_objects(prefix: str = "") -> list[dict]:
    """List objects en backup vault con prefix.

    Returns:
        List of dicts ``{key, size, last_modified}`` sorted desc by date.
    """
    client = get_minio_client()
    rows = []
    for obj in client.list_objects(
        BUCKET_BACKUP_VAULT, prefix=prefix, recursive=True
    ):
        rows.append({
            "key": obj.object_name,
            "size": obj.size,
            "last_modified": obj.last_modified,
        })
    rows.sort(key=lambda r: r["last_modified"], reverse=True)
    return rows


def delete_offsite_object(key: str) -> None:
    """Remove encrypted object from offsite vault (retention enforcement)."""
    remove_object(BUCKET_BACKUP_VAULT, key)
    logger.info("Offsite object eliminado: %s/%s", BUCKET_BACKUP_VAULT, key)


def _stable_hash(payload: bytes) -> str:
    """Helper SHA256 for deterministic comparison."""
    return hashlib.sha256(payload).hexdigest()
