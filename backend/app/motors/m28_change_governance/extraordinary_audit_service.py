"""Motor 28 — Extraordinary audit workflow."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone


def open_extraordinary_audit(
    project_id: uuid.UUID,
    change_id: uuid.UUID,
    rationale: str,
    target_date: str | None = None,
) -> dict:
    return {
        "audit_id": uuid.uuid4(),
        "project_id": project_id,
        "change_id": change_id,
        "rationale": rationale[:1000],
        "state": "open",
        "target_date": target_date,
        "readiness_required": ["E-046", "E-615", "delta_dossier"],
        "opened_at": datetime.now(timezone.utc),
    }
