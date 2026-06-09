"""DND (Do Not Disturb) helper timezone-aware (ADR-039 MB-16.2).

Resuelve si el momento ``now_utc`` cae dentro de la ventana DND
configurada por el cliente en su timezone IANA local.

Soporta ventanas que cruzan medianoche (ej. 22:00→08:00 = activa
desde las 22h hasta las 8h del día siguiente). Política de bordes:
``[start, end)`` inclusive de start, exclusivo de end.

Política conservadora MB-16: si timezone inválido o parse format
falla → DND ignorado (envío permitido) · NO suprimir por error
config (mejor mensaje extra que mensaje perdido).
"""
from __future__ import annotations

import logging
from datetime import datetime, time, timezone

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover · stdlib >=3.9
    ZoneInfo = None  # type: ignore[assignment]
    ZoneInfoNotFoundError = Exception  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)


def parse_hhmm(value: str | None) -> time | None:
    """Parse ``"HH:MM"`` 24h string a ``datetime.time``.

    Retorna ``None`` si ``value`` es ``None`` o formato inválido.
    Coincide con CHECK constraint de ``notification_preferences``.
    """
    if value is None:
        return None
    parts = value.split(":")
    if len(parts) != 2:
        return None
    try:
        h = int(parts[0])
        m = int(parts[1])
    except ValueError:
        return None
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return time(hour=h, minute=m)


def is_dnd_active(
    *,
    dnd_start_local: str | None,
    dnd_end_local: str | None,
    tz_name: str,
    now_utc: datetime | None = None,
) -> bool:
    """¿Está DND activo en este momento para el cliente?

    Args:
        dnd_start_local: ``HH:MM`` local timezone o ``None`` (sin DND).
        dnd_end_local: ``HH:MM`` local timezone o ``None`` (sin DND).
        tz_name: IANA timezone name (ej. ``Europe/Madrid``).
        now_utc: instante actual UTC. Default ``datetime.now(UTC)``.

    Returns:
        ``True`` si DND activo (suprimir envío).
        ``False`` si fuera de ventana DND o config inválida (envío
        permitido por política conservadora).

    Política borde:
    - ``start <= now_local < end`` cuando ``start < end`` (ventana
      mismo día · ej. 13:00→14:00).
    - ``now_local >= start OR now_local < end`` cuando ``start >
      end`` (ventana cruza medianoche · ej. 22:00→08:00).
    - ``start == end`` se considera ventana 24h (DND siempre activo).
    """
    start = parse_hhmm(dnd_start_local)
    end = parse_hhmm(dnd_end_local)
    if start is None or end is None:
        return False

    if ZoneInfo is None:  # pragma: no cover · stdlib siempre disponible
        logger.warning("zoneinfo no disponible · DND ignorado")
        return False

    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        logger.warning(
            "DND tz %r inválida · ignorando ventana DND (envío permitido)",
            tz_name,
        )
        return False

    now = now_utc if now_utc is not None else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now_local = now.astimezone(tz).time()

    if start == end:
        return True
    if start < end:
        return start <= now_local < end
    return now_local >= start or now_local < end


__all__ = ["is_dnd_active", "parse_hhmm"]
