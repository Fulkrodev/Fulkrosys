"""Motor 28 — Impact assessor.

Wraps the materiality engine and adds bookkeeping (id, project_id, timestamp).
Pure functions; no DB.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from backend.app.motors.m28_change_governance.materiality_engine import assess


def assess_change(
    project_id: uuid.UUID,
    change_description: str,
    answers: dict[str, bool],
    requested_by: str,
) -> dict:
    """Run the assessment and wrap with metadata."""
    result = assess(answers)
    return {
        "change_id": uuid.uuid4(),
        "project_id": project_id,
        "description": change_description[:500],
        "requested_by": requested_by,
        "assessed_at": datetime.now(timezone.utc),
        **result,
    }
