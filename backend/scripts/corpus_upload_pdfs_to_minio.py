"""Sub-lote 1.B.5.2 PASO 4.1 · upload los 14 PDFs del batch a MinIO fulkro-corpus.

Object key convention: corpus/{category}/{filename}.pdf
Reusa get_minio_client + put_object existing en backend/app/core/storage/minio_client.

Idempotente: si el objeto ya existe con mismo sha256, lo salta.

Usage:
    PYTHONPATH=. .venv/bin/python backend/scripts/corpus_upload_pdfs_to_minio.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path("/home/usuario/fulkro/.env"))

from backend.app.corpus.ccn_pdf_ingest import CORPUS_BATCH_1B5_2, PDF_ROOT
from backend.app.core.storage.minio_client import (
    BUCKET_CORPUS,
    ensure_corpus_bucket,
    get_minio_client,
    put_object,
)


def main() -> int:
    ensure_corpus_bucket()
    client = get_minio_client()

    uploaded = 0
    skipped = 0
    failed = 0

    for entry in CORPUS_BATCH_1B5_2:
        pdf_path = PDF_ROOT / entry.pdf_relative
        if not pdf_path.exists():
            print(f"[FAIL] {entry.code}: PDF no encontrado {pdf_path}")
            failed += 1
            continue

        object_key = f"corpus/{entry.category}/{pdf_path.name}"
        raw = pdf_path.read_bytes()
        sha256 = hashlib.sha256(raw).hexdigest()

        # Check existing
        try:
            existing = client.stat_object(BUCKET_CORPUS, object_key)
            if existing.metadata.get("x-amz-meta-sha256") == sha256:
                print(f"[SKIP] {entry.code} · {object_key} ya existe (sha match)")
                skipped += 1
                continue
        except Exception:
            pass

        result = put_object(
            bucket=BUCKET_CORPUS,
            key=object_key,
            data=raw,
            content_type="application/pdf",
            metadata={"sha256": sha256, "code": entry.code, "batch": "1.B.5.2"},
        )
        print(f"[OK]   {entry.code} · {object_key} · {result.size} B")
        uploaded += 1

    print("\n=== SUMMARY ===")
    print(f"  uploaded: {uploaded}")
    print(f"  skipped:  {skipped}")
    print(f"  failed:   {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
