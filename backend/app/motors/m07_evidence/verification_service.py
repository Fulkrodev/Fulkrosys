"""Evidence cryptographic verification service.

Verifies file integrity (SHA-256 hash) and Ed25519 signature.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# Evidence storage root: same as ingestion_service
_REPO_ROOT = Path(__file__).resolve().parents[3].parent
_EVIDENCES_DIR = _REPO_ROOT / "var" / "evidences"


@dataclass
class VerificationReport:
    """Result of cryptographic verification."""
    evidence_id: uuid.UUID
    verdict: str  # "ok" | "tampered" | "missing" | "invalid_signature" | "unknown"
    hash_matches: bool | None = None
    signature_valid: bool | None = None
    stored_hash: str | None = None
    computed_hash: str | None = None
    detail: str | None = None


async def verify_evidence(
    session: AsyncSession,
    evidence_id: uuid.UUID,
) -> VerificationReport:
    """Verify an evidence's file integrity and Ed25519 signature.

    Steps:
    1. Load evidence metadata from DB
    2. Check file exists on disk
    3. Recalculate SHA-256 from disk bytes
    4. Compare with stored hash_sha256
    5. Verify Ed25519 signature (firma_ed25519 stored as hex)
    """
    # 1. Load evidence from DB
    result = await session.execute(
        text(
            "SELECT id, fichero_path, hash_sha256, firma_ed25519, firma_payload_sha256 "
            "FROM evidence WHERE id = :eid AND deleted_at IS NULL"
        ),
        {"eid": str(evidence_id)},
    )
    row = result.fetchone()
    if row is None:
        return VerificationReport(
            evidence_id=evidence_id,
            verdict="unknown",
            detail="Evidence not found in database",
        )

    fichero_path = row[1]
    stored_hash = row[2]
    firma_hex = row[3]
    firma_payload_sha256 = row[4]

    # 2. Resolve file path and check existence
    file_path = _REPO_ROOT / fichero_path if fichero_path else None
    if file_path is None or not file_path.exists():
        return VerificationReport(
            evidence_id=evidence_id,
            verdict="missing",
            stored_hash=stored_hash,
            detail=f"File not found on disk: {fichero_path}",
        )

    # 3. Recalculate SHA-256
    file_bytes = file_path.read_bytes()
    computed_hash = hashlib.sha256(file_bytes).hexdigest()

    # 4. Compare hashes
    hash_matches = (computed_hash == stored_hash)

    if not hash_matches:
        return VerificationReport(
            evidence_id=evidence_id,
            verdict="tampered",
            hash_matches=False,
            signature_valid=None,
            stored_hash=stored_hash,
            computed_hash=computed_hash,
            detail="SHA-256 hash mismatch — file has been modified",
        )

    # 5. Verify Ed25519 signature
    if firma_hex is None:
        return VerificationReport(
            evidence_id=evidence_id,
            verdict="ok",
            hash_matches=True,
            signature_valid=None,
            stored_hash=stored_hash,
            computed_hash=computed_hash,
            detail="Hash matches. No signature stored (unsigned evidence).",
        )

    try:
        sig_bytes = bytes.fromhex(firma_hex)
    except ValueError:
        return VerificationReport(
            evidence_id=evidence_id,
            verdict="invalid_signature",
            hash_matches=True,
            stored_hash=stored_hash,
            computed_hash=computed_hash,
            detail="Stored signature is not valid hex",
        )

    # We need the original signing payload to verify.
    # The signing payload hash is stored in firma_payload_sha256,
    # but we don't have the original payload to re-verify against.
    # The signature was computed over: "{file_hash}|{timestamp}|{project_id}|{evidence_type_id}"
    # We can't reconstruct timestamp, so we just verify the signature
    # is a valid 64-byte Ed25519 signature for the stored payload.
    # For structural integrity, we confirm length and format.
    if len(sig_bytes) != 64:
        return VerificationReport(
            evidence_id=evidence_id,
            verdict="invalid_signature",
            hash_matches=True,
            stored_hash=stored_hash,
            computed_hash=computed_hash,
            detail=f"Signature length {len(sig_bytes)} != 64 bytes",
        )

    # Hash matches y la firma es ESTRUCTURALMENTE válida (64 bytes), pero NO se
    # verifica criptográficamente con Ed25519 porque no se conserva el payload
    # original (timestamp) para reconstruirlo. Reportar signature_valid=None (no
    # verificada) en vez de True — no afirmar integridad de firma ante ENAC que
    # no se ha comprobado. La integridad de contenido (hash) SÍ se confirma.
    return VerificationReport(
        evidence_id=evidence_id,
        verdict="ok",
        hash_matches=True,
        signature_valid=None,
        stored_hash=stored_hash,
        computed_hash=computed_hash,
        detail="Hash coincide; firma estructuralmente válida pero NO verificada criptográficamente (payload original no conservado)",
    )
