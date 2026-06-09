"""Awareness training tracker · SAN-C MB-11.5.

Tracking sesiones formación seguridad + asistencia + coverage cliente.
Pattern: schedule sesión → notify (M29 client_messaging) → record
attendance (magic-link sign) → calcular coverage (% empleados con
formación reciente último año).

Decisión: motor stateful con tablas dedicadas (no extender m16 RRHH)
porque awareness_sessions es entidad temporal con FK distintos
(project + attendees vs employee_id) y queremos query-friendly per
project para coverage metrics.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.awareness import AwarenessAttendance, AwarenessSession


async def schedule_session(
    session: AsyncSession,
    project_id: uuid.UUID,
    title: str,
    scheduled_date: datetime,
    topics: Optional[list[str]] = None,
    mandatory: bool = True,
) -> AwarenessSession:
    """Programa sesión formación seguridad para proyecto."""
    s = AwarenessSession(
        project_id=project_id,
        title=title,
        scheduled_date=scheduled_date,
        topics=topics or [],
        mandatory=mandatory,
    )
    session.add(s)
    await session.flush()
    return s


async def list_sessions(
    session: AsyncSession,
    project_id: uuid.UUID,
) -> list[AwarenessSession]:
    """Lista sesiones del proyecto, scheduled más recientes primero."""
    result = await session.execute(
        select(AwarenessSession)
        .where(AwarenessSession.project_id == project_id)
        .order_by(AwarenessSession.scheduled_date.desc())
    )
    return list(result.scalars().all())


async def record_attendance(
    session: AsyncSession,
    session_id: uuid.UUID,
    attendee_email: str,
    method: str,  # in_person | virtual | recorded
    magic_link_token: Optional[str] = None,
) -> AwarenessAttendance:
    """Registra asistencia · audit log immutable.

    Si method == 'recorded', acepta sin magic-link (auto-tracking).
    Else, magic_link_token recomendado para identidad sign-in.
    """
    if method not in {"in_person", "virtual", "recorded"}:
        raise ValueError(f"method inválido: {method}")
    a = AwarenessAttendance(
        session_id=session_id,
        attendee_email=attendee_email,
        method=method,
        attended_at=datetime.now(timezone.utc),
        magic_link_token=magic_link_token,
    )
    session.add(a)
    await session.flush()
    return a


async def calculate_coverage(
    session: AsyncSession,
    project_id: uuid.UUID,
    expected_attendees: int,
    window_days: int = 365,
) -> dict:
    """% empleados con formación reciente (último año por defecto).

    Args:
        project_id: Project ID.
        expected_attendees: Total empleados esperados (denominador).
        window_days: Ventana de validez de formación (365 default).

    Returns:
        dict con unique_attendees + coverage_pct + window_start.
    """
    if expected_attendees <= 0:
        raise ValueError("expected_attendees debe ser positivo")

    window_start = datetime.now(timezone.utc) - timedelta(days=window_days)

    result = await session.execute(
        select(func.count(func.distinct(AwarenessAttendance.attendee_email)))
        .join(AwarenessSession, AwarenessAttendance.session_id == AwarenessSession.id)
        .where(
            AwarenessSession.project_id == project_id,
            AwarenessAttendance.attended_at >= window_start,
        )
    )
    unique_attendees = result.scalar_one() or 0
    coverage_pct = (unique_attendees / expected_attendees) * 100.0
    return {
        "unique_attendees": unique_attendees,
        "expected_attendees": expected_attendees,
        "coverage_pct": round(coverage_pct, 2),
        "window_start": window_start.isoformat(),
    }
