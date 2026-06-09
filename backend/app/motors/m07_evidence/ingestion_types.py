"""Request / response types for evidence ingestion pipeline."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date


@dataclass
class IngestionRequest:
    """Input for the ingestion pipeline."""
    project_id: uuid.UUID
    evidence_type_id: str
    measure_code: str
    file_bytes: bytes
    file_name: str
    mime_type: str
    fecha_evidencia: date | None = None
    obligation_id: uuid.UUID | None = None
    metadata_extra: dict | None = None


@dataclass
class IngestionOutcome:
    """Successful result of evidence ingestion."""
    evidence_id: uuid.UUID
    hash_sha256: str
    firma_ed25519_hex: str
    firma_payload_sha256: str
    fichero_path: str
    fecha_caducidad: date | None
    evidence_type_id: str
    nombre_tipo: str


class IngestionError(Exception):
    """Raised when evidence ingestion fails validation."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"[{code}] {detail}")
