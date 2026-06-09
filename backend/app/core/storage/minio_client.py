"""MinIO client factory for FULKRO.

Lazy-initialised singleton. Reads endpoint / credentials from
``Settings`` (``.env``). Buckets are not auto-created here — they are
provisioned via ``mc`` at deployment time (see infra docs) because some
buckets (``fulkro-evidence-worm``) require Object Lock enabled at
creation, which the Python SDK cannot do.
"""
from __future__ import annotations

import functools
import hashlib
import json
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from backend.app.config import get_settings


logger = logging.getLogger(__name__)


BUCKET_DOCUMENTS = "fulkro-documents"
BUCKET_EVIDENCE = "fulkro-evidence"
BUCKET_EVIDENCE_WORM = "fulkro-evidence-worm"
BUCKET_EXPORTS = "fulkro-exports"
BUCKET_ADMIN_ASSETS = "fulkro-admin-assets"
# MB-10 Atom 10.6.B · backup offsite vault dedicated (ADR-043).
# Clear separation backup vs files · ISMS §5.5 offsite location distinta.
# Dev: MinIO local · Prod: Hetzner Object Storage cutover MB-11 (S3-compatible).
BUCKET_BACKUP_VAULT = "backup-vault-fulkro"
# Sub-lote 1.B.5.0 · ADR-CORPUS-001 · corpus normativo PDF/HTML storage.
# Acceso via signed URLs (NO public read) · TTL configurable. Pipeline
# ccn_pdf_ingest.py (sub-lote 1.B.5.2) sube PDFs aqui antes de extraer +
# chunk + embed + INSERT en knowledge_chunks.
BUCKET_CORPUS = "fulkro-corpus"


@dataclass(frozen=True)
class PutObjectResult:
    bucket: str
    key: str
    size: int
    sha256: str
    content_type: str


@functools.lru_cache(maxsize=1)
def get_minio_client() -> Minio:
    """Return the shared MinIO client for the current process."""
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key.get_secret_value(),
        secure=False,
    )


def _build_retention(worm_retention_days: int | None):
    """Construye Retention COMPLIANCE (WORM) o None. Import perezoso del SDK."""
    if not worm_retention_days or worm_retention_days <= 0:
        return None
    try:
        from datetime import datetime, timedelta, timezone

        from minio.commonconfig import COMPLIANCE
        from minio.retention import Retention

        return Retention(
            COMPLIANCE,
            datetime.now(timezone.utc) + timedelta(days=worm_retention_days),
        )
    except Exception as exc:  # pragma: no cover — SDK variante
        logger.warning("No se pudo construir Retention WORM: %s", exc)
        return None


def put_object(
    bucket: str,
    key: str,
    data: bytes | BinaryIO,
    content_type: str = "application/octet-stream",
    metadata: dict | None = None,
    *,
    worm_retention_days: int | None = None,
) -> PutObjectResult:
    """Upload ``data`` to ``bucket/key``. Returns size + sha256.

    FIX P2-7: si ``worm_retention_days`` se pasa, el objeto se escribe con
    retención COMPLIANCE (WORM · inmutable incluso para root hasta la fecha). Si
    el bucket no tiene Object Lock habilitado (p.ej. el MinIO de dev), se
    degrada con gracia a una escritura durable normal (sin WORM) en vez de
    fallar — el código de producción es correcto y dev sigue funcionando.
    """
    if isinstance(data, (bytes, bytearray)):
        raw = bytes(data)
    else:
        raw = data.read()
    stream = BytesIO(raw)
    sha = hashlib.sha256(raw).hexdigest()
    meta = {f"x-amz-meta-{k}": v for k, v in (metadata or {}).items()}
    retention = _build_retention(worm_retention_days)
    try:
        get_minio_client().put_object(
            bucket, key, data=stream, length=len(raw),
            content_type=content_type, metadata=meta, retention=retention,
        )
    except S3Error as exc:
        if retention is None:
            raise
        # Bucket sin Object Lock (dev) → reintento durable sin WORM (graceful).
        logger.warning(
            "put_object %s/%s sin Object Lock; guardo durable SIN WORM: %s",
            bucket, key, exc,
        )
        stream.seek(0)
        get_minio_client().put_object(
            bucket, key, data=stream, length=len(raw),
            content_type=content_type, metadata=meta,
        )
    return PutObjectResult(
        bucket=bucket, key=key, size=len(raw), sha256=sha, content_type=content_type
    )


def get_object(bucket: str, key: str) -> bytes:
    """Download ``bucket/key`` fully into memory."""
    resp = get_minio_client().get_object(bucket, key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()


def remove_object(bucket: str, key: str) -> None:
    """Elimina ``bucket/key``. Idempotente: no falla si no existe."""
    try:
        get_minio_client().remove_object(bucket, key)
    except S3Error as exc:
        # NoSuchKey o similar: log warning + continúa (idempotencia)
        logger.warning(
            "remove_object %s/%s falló (probable not-exists): %s",
            bucket, key, exc,
        )


def ensure_corpus_bucket() -> None:
    """Garantiza que el bucket ``fulkro-corpus`` existe (sin policy publica).

    Sub-lote 1.B.5.0 · ADR-CORPUS-001. Acceso al corpus normativo via
    signed URLs · NO public read (a diferencia de ``fulkro-admin-assets``
    que sirve logos sin auth). Provisión deploy-time recomendada con
    ``mc mb local/fulkro-corpus``; este helper es lazy-create defensive
    para dev/CI. Idempotente.
    """
    client = get_minio_client()
    try:
        if client.bucket_exists(BUCKET_CORPUS):
            return
        client.make_bucket(BUCKET_CORPUS)
        logger.info("Bucket %s creado (signed-URL only, sin public read)", BUCKET_CORPUS)
    except Exception as exc:
        logger.warning(
            "ensure_corpus_bucket: no se pudo provisionar %s: %s. "
            "Provisionar manualmente: mc mb local/%s",
            BUCKET_CORPUS, exc, BUCKET_CORPUS,
        )


def ensure_admin_assets_bucket() -> None:
    """Garantiza que el bucket ``fulkro-admin-assets`` existe + es public read.

    Lazy-create defensive: si no existe, intenta crearlo con policy
    public download. En staging/prod con permisos restrictivos puede
    fallar; el endpoint logo upload propagará el error real al
    cliente. Ver ``docs/infra/buckets.md`` para provisión manual
    deploy-time vía ``mc``.

    Idempotente: si ya existe, no hace nada (silent).
    """
    client = get_minio_client()
    try:
        if client.bucket_exists(BUCKET_ADMIN_ASSETS):
            return
        client.make_bucket(BUCKET_ADMIN_ASSETS)
        # Public read policy (logos accesibles por browser sin auth)
        policy = json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{BUCKET_ADMIN_ASSETS}/*"],
            }],
        })
        client.set_bucket_policy(BUCKET_ADMIN_ASSETS, policy)
        logger.info("Bucket %s creado con public read policy", BUCKET_ADMIN_ASSETS)
    except Exception as exc:
        logger.warning(
            "ensure_admin_assets_bucket: no se pudo provisionar %s: %s. "
            "Provisionar manualmente vía: mc mb local/%s && mc anonymous set "
            "download local/%s",
            BUCKET_ADMIN_ASSETS, exc, BUCKET_ADMIN_ASSETS, BUCKET_ADMIN_ASSETS,
        )
