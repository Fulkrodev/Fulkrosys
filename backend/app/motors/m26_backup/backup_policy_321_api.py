"""3-2-1 backup policy API · SAN-C MB-11.5.

Endpoint stateless (no requiere project_id ni DB · evaluación pura):
- POST /api/v1/backup-policy/3-2-1/evaluate

Caller pasa lista de BackupCopy (label + media_type + is_offsite) y
retorna Compliance321Result con boolean compliant + métricas + gaps.

Wire-up frontend (ADR-034): frontend/lib/admin-backup-policy/api.ts +
BackupPolicy321Panel.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.motors.m26_backup.backup_policy_3_2_1 import (
    BackupCopy,
    evaluate_3_2_1,
)

router = APIRouter(prefix="/backup-policy", tags=["M26 - 3-2-1 Policy (MB-11.5)"])


class BackupCopyInput(BaseModel):
    label: str = Field(..., max_length=200)
    media_type: str = Field(..., max_length=50)
    is_offsite: bool = False


class Evaluate321Request(BaseModel):
    copies: list[BackupCopyInput]


class Compliance321Response(BaseModel):
    compliant: bool
    copies_count: int
    media_types: list[str]
    offsite_count: int
    gaps: list[str]


@router.post(
    "/3-2-1/evaluate",
    response_model=Compliance321Response,
)
async def post_evaluate_321(body: Evaluate321Request) -> Compliance321Response:
    copies = [
        BackupCopy(
            label=c.label,
            media_type=c.media_type,
            is_offsite=c.is_offsite,
        )
        for c in body.copies
    ]
    result = evaluate_3_2_1(copies)
    return Compliance321Response(
        compliant=result.compliant,
        copies_count=result.copies_count,
        media_types=result.media_types,
        offsite_count=result.offsite_count,
        gaps=result.gaps,
    )
