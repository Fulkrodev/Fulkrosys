"""API admin de sellado de tiempo RFC 3161 · feat/fulkro-100 Ola D.

Marcos (require_owner) sella un evento de firma contra la TSA y consulta/verifica
el sello. NO toca ``signing_events`` (inmutable · hash chain R6): el sello vive en
``trusted_timestamps`` (append-only). ADR-013.
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.core.timestamping import request_timestamp, verify_timestamp
from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.trusted_timestamp import TrustedTimestamp
from backend.app.motors.m05_signing.models import SigningEvent

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/signing",
    tags=["Motor 5 - Firma · Sellado RFC 3161"],
    dependencies=[Depends(require_owner)],
)


class TimestampOut(BaseModel):
    id: str
    artifact_type: str
    artifact_id: str
    artifact_hash: str
    tsa_url: str
    status: str
    has_token: bool
    gen_time: Optional[str] = None
    verified: Optional[bool] = None
    created_at: Optional[str] = None


def _to_out(r: TrustedTimestamp, *, verified: Optional[bool] = None) -> TimestampOut:
    return TimestampOut(
        id=str(r.id),
        artifact_type=r.artifact_type,
        artifact_id=str(r.artifact_id),
        artifact_hash=r.artifact_hash,
        tsa_url=r.tsa_url,
        status=r.status,
        has_token=r.token is not None,
        gen_time=r.gen_time.isoformat() if r.gen_time else None,
        verified=verified,
        created_at=r.created_at.isoformat() if r.created_at else None,
    )


async def _load_event_set_rls(
    db: AsyncSession, event_id: uuid.UUID,
) -> SigningEvent:
    event = await db.get(SigningEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Evento de firma no encontrado")
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(event.project_id)},
    )
    return event


@router.post("/events/{event_id}/timestamp", response_model=TimestampOut)
async def request_event_timestamp(
    event_id: uuid.UUID,
    owner: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> TimestampOut:
    """Solicita un sello RFC 3161 para el hash del evento de firma.

    Best-effort: si la TSA está deshabilitada/inalcanzable, se registra igualmente
    el intento con su status honesto (disabled/unavailable/failed) sin romper nada.
    """
    event = await _load_event_set_rls(db, event_id)
    result = await request_timestamp(event.event_hash_sha256)

    row = TrustedTimestamp(
        project_id=event.project_id,
        artifact_type="signing_event",
        artifact_id=event.id,
        artifact_hash=event.event_hash_sha256,
        tsa_url=result.tsa_url,
        status=result.status,
        token=result.token_der,
        gen_time=result.gen_time,
    )
    db.add(row)
    await db.flush()

    # audit_log Sub-atom 5.A
    try:
        await db.execute(
            text(
                "INSERT INTO audit_log "
                "(id, tabla, registro_id, accion, usuario, project_id, "
                "payload_new, timestamp) VALUES (gen_random_uuid(), "
                "'trusted_timestamps', :rid, 'timestamp.requested', :usuario, "
                ":pid, :payload, now())"
            ),
            {
                "rid": str(row.id),
                "usuario": getattr(owner, "email", "admin") or "admin",
                "pid": str(event.project_id),
                "payload": '{"status": "%s"}' % result.status,
            },
        )
    except Exception:  # pragma: no cover · best-effort
        logger.exception("audit_log timestamp.requested emit failed")
    await db.commit()

    verified = (
        verify_timestamp(row.token, row.artifact_hash)
        if row.token is not None else None
    )
    return _to_out(row, verified=verified)


@router.get("/events/{event_id}/timestamp", response_model=Optional[TimestampOut])
async def get_event_timestamp(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Optional[TimestampOut]:
    """Último sello del evento de firma (con verificación del message imprint)."""
    await _load_event_set_rls(db, event_id)
    row = (await db.execute(
        select(TrustedTimestamp)
        .where(
            TrustedTimestamp.artifact_type == "signing_event",
            TrustedTimestamp.artifact_id == event_id,
        )
        .order_by(TrustedTimestamp.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    if row is None:
        return None
    verified = (
        verify_timestamp(row.token, row.artifact_hash)
        if row.token is not None else None
    )
    return _to_out(row, verified=verified)
