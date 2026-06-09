"""Tests offsite backup upload + retention (ADR-043 · MB-10 Atom 10.6.B).

Uses in-memory fake para minio_client helpers (NO dependency MinIO server
en tests). Pattern monkeypatch put_object/get_object/remove_object.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.config import get_settings
from backend.app.core.storage.minio_client import BUCKET_BACKUP_VAULT
from backend.app.motors.m26_backup import encryption as backup_enc
from backend.app.motors.m26_backup import offsite


@pytest.fixture(autouse=True)
def _reset_backup_key(monkeypatch):
    monkeypatch.setenv(
        "BACKUP_ENCRYPTION_KEY", "test-offsite-key-32-bytes-min-length"
    )
    get_settings.cache_clear()
    backup_enc.reset_fernet_cache()
    yield
    get_settings.cache_clear()
    backup_enc.reset_fernet_cache()


class _FakeMinio:
    """In-memory fake minio replacement (NO server dependency)."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.bucket_created: list[str] = []

    def bucket_exists(self, bucket: str) -> bool:
        return bucket == BUCKET_BACKUP_VAULT and bucket in self.bucket_created

    def make_bucket(self, bucket: str) -> None:
        self.bucket_created.append(bucket)

    def list_objects(self, bucket: str, prefix: str = "", recursive: bool = True):
        for key, data in self.objects.items():
            if not key.startswith(prefix):
                continue
            yield SimpleNamespace(
                object_name=key,
                size=len(data),
                last_modified=datetime.now(timezone.utc),
            )

    def get(self, key):
        return self.objects.get(key)

    def put(self, key, data):
        self.objects[key] = data

    def remove(self, key):
        self.objects.pop(key, None)


@pytest.fixture
def fake_minio(monkeypatch):
    fake = _FakeMinio()
    fake.bucket_created.append(BUCKET_BACKUP_VAULT)  # pre-create for tests

    def fake_get_client():
        return fake

    def fake_put_object(bucket, key, data, content_type, metadata):
        if isinstance(data, (bytes, bytearray)):
            raw = bytes(data)
        else:
            raw = data.read()
        fake.put(key, raw)
        from backend.app.core.storage.minio_client import PutObjectResult
        import hashlib
        return PutObjectResult(
            bucket=bucket,
            key=key,
            size=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            content_type=content_type,
        )

    def fake_get_object(bucket, key):
        data = fake.get(key)
        if data is None:
            raise FileNotFoundError(f"Object not found: {bucket}/{key}")
        return data

    def fake_remove_object(bucket, key):
        fake.remove(key)

    monkeypatch.setattr(offsite, "get_minio_client", fake_get_client)
    monkeypatch.setattr(offsite, "put_object", fake_put_object)
    monkeypatch.setattr(offsite, "get_object", fake_get_object)
    monkeypatch.setattr(offsite, "remove_object", fake_remove_object)
    return fake


def test_build_key_format():
    key = offsite._build_key("postgres_full", "backup.tar.gz")
    assert key.startswith("postgres_full/")
    assert key.endswith("-backup.tar.gz.enc")
    # Format: postgres_full/YYYYMMDDTHHMMSS-backup.tar.gz.enc
    parts = key.split("/")
    assert len(parts) == 2
    assert parts[0] == "postgres_full"
    assert len(parts[1]) > 30  # timestamp + basename + ext


def test_upload_encrypted_artifact_encrypts_data(tmp_path: Path, fake_minio):
    src = tmp_path / "snapshot.sql"
    plaintext = b"INSERT INTO users VALUES (1);"
    src.write_bytes(plaintext)

    result = offsite.upload_encrypted_artifact(src, "postgres_full")

    assert result.bucket == BUCKET_BACKUP_VAULT
    assert result.key.startswith("postgres_full/")
    assert result.key.endswith("-snapshot.sql.enc")
    assert result.encryption_key_fingerprint == backup_enc.current_key_fingerprint()

    stored = fake_minio.get(result.key)
    assert stored is not None
    assert stored != plaintext  # encrypted differs


def test_upload_missing_source_raises(fake_minio):
    with pytest.raises(FileNotFoundError, match="not found"):
        offsite.upload_encrypted_artifact("/nonexistent/path.tar", "postgres_full")


def test_download_and_decrypt_roundtrip(tmp_path: Path, fake_minio):
    src = tmp_path / "backup.tar.gz"
    plaintext = b"backup payload " * 100
    src.write_bytes(plaintext)

    upload = offsite.upload_encrypted_artifact(src, "postgres_full")

    dest = tmp_path / "restored.tar.gz"
    out = offsite.download_and_decrypt(upload.key, dest)

    assert out == dest
    assert dest.read_bytes() == plaintext


def test_list_offsite_objects_filter_prefix(tmp_path: Path, fake_minio):
    # Upload 2 distinct backups
    for name, btype in [("a.sql", "postgres_full"), ("b.sql", "audit_log_export")]:
        f = tmp_path / name
        f.write_bytes(b"data")
        offsite.upload_encrypted_artifact(f, btype)

    pg_list = offsite.list_offsite_objects(prefix="postgres_full/")
    audit_list = offsite.list_offsite_objects(prefix="audit_log_export/")
    all_list = offsite.list_offsite_objects(prefix="")

    assert len(pg_list) == 1
    assert len(audit_list) == 1
    assert len(all_list) == 2
    assert pg_list[0]["key"].startswith("postgres_full/")
    assert audit_list[0]["key"].startswith("audit_log_export/")


def test_delete_offsite_object_removes_from_bucket(tmp_path: Path, fake_minio):
    src = tmp_path / "x.sql"
    src.write_bytes(b"x")
    upload = offsite.upload_encrypted_artifact(src, "postgres_full")
    assert fake_minio.get(upload.key) is not None

    offsite.delete_offsite_object(upload.key)
    assert fake_minio.get(upload.key) is None


def test_ensure_backup_vault_bucket_idempotent(monkeypatch):
    """Lazy-create no-op si ya existe."""
    fake = _FakeMinio()
    fake.bucket_created.append(BUCKET_BACKUP_VAULT)
    monkeypatch.setattr(offsite, "get_minio_client", lambda: fake)
    offsite.ensure_backup_vault_bucket()  # ya exists
    # Bucket counter no aumenta porque ya existe
    assert fake.bucket_created.count(BUCKET_BACKUP_VAULT) == 1


def test_ensure_backup_vault_bucket_creates_if_missing(monkeypatch):
    fake = _FakeMinio()
    # NO pre-create
    monkeypatch.setattr(offsite, "get_minio_client", lambda: fake)
    offsite.ensure_backup_vault_bucket()
    assert BUCKET_BACKUP_VAULT in fake.bucket_created


def test_upload_encrypted_artifact_metadata_includes_fingerprint(
    tmp_path: Path, fake_minio, monkeypatch
):
    captured_metadata = {}

    def fake_put_object(bucket, key, data, content_type, metadata):
        captured_metadata.update(metadata)
        from backend.app.core.storage.minio_client import PutObjectResult
        return PutObjectResult(
            bucket=bucket, key=key, size=len(data),
            sha256="x", content_type=content_type,
        )

    monkeypatch.setattr(offsite, "put_object", fake_put_object)

    src = tmp_path / "metadata.bin"
    src.write_bytes(b"data")
    offsite.upload_encrypted_artifact(src, "config_snapshot")

    assert "encryption_key_fingerprint" in captured_metadata
    assert captured_metadata["backup_type"] == "config_snapshot"
    assert captured_metadata["source_filename"] == "metadata.bin"
