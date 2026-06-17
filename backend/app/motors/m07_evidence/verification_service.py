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
    expected_project_id: uuid.UUID | None = None,
) -> VerificationReport:
    """Verify an evidence's file integrity and Ed25519 signature.

    Steps:
    1. Load evidence metadata from DB
    2. Check file exists on disk
    3. Recalculate SHA-256 from disk bytes
    4. Compare with stored hash_sha256
    5. Verify Ed25519 signature (firma_ed25519 stored as hex)

    M2 IDOR fix: ``expected_project_id`` (siempre, desde el endpoint) ata la
    evidencia al proyecto de la URL — ya verificado como propio del caller en
    ``_set_project_rls``. Bajo el pool cliente RLS está OFF; sin este filtro un
    cliente podía leer fichero/hash/veredicto de una evidencia de otro tenant.
    Mismo contrato que ``preview``.
    """
    # 1. Load evidence from DB (acotado al proyecto de la URL si se pasa).
    result = await session.execute(
        text(
            "SELECT id, fichero_path, hash_sha256, firma_ed25519, firma_payload_sha256, "
            "project_id, evidence_type_id, firma_timestamp "
            "FROM evidence WHERE id = :eid AND deleted_at IS NULL "
            "AND (CAST(:pid AS uuid) IS NULL OR project_id = CAST(:pid AS uuid))"
        ),
        {"eid": str(evidence_id), "pid": (
            str(expected_project_id) if expected_project_id else None
        )},
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
    ev_project_id = row[5]
    ev_evidence_type_id = row[6]
    firma_timestamp = row[7]

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

    # §1.5: si se conservó firma_timestamp, reconstruimos el payload original y
    # verificamos la firma Ed25519 DE VERDAD. El payload de ingestion fue
    # f"{file_hash}|{timestamp}|{project_id}|{evidence_type_id}"; como el hash
    # coincide, file_hash == computed_hash.
    if firma_timestamp is None:
        # Evidencia previa a la migración (sin timestamp) → no reconstruible.
        return VerificationReport(
            evidence_id=evidence_id,
            verdict="ok",
            hash_matches=True,
            signature_valid=None,
            stored_hash=stored_hash,
            computed_hash=computed_hash,
            detail="Hash coincide; firma estructuralmente válida pero NO verificable (evidencia previa a la migración · sin firma_timestamp)",
        )

    from backend.app.motors.m07_evidence.signing import verify_signature

    reconstructed = (
        f"{computed_hash}|{firma_timestamp}|{ev_project_id}|{ev_evidence_type_id}"
    ).encode("utf-8")
    signature_valid = verify_signature(reconstructed, sig_bytes)
    return VerificationReport(
        evidence_id=evidence_id,
        verdict="ok" if signature_valid else "invalid_signature",
        hash_matches=True,
        signature_valid=signature_valid,
        stored_hash=stored_hash,
        computed_hash=computed_hash,
        detail=(
            "Hash coincide; firma Ed25519 verificada criptográficamente"
            if signature_valid else
            "Hash coincide pero la firma Ed25519 NO es válida"
        ),
    )
