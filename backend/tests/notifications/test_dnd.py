"""Tests DND helper timezone-aware (MB-16.2 ADR-039).

Cubre:
- ``parse_hhmm`` formatos válidos / inválidos.
- ``is_dnd_active`` ventanas mismo día (start < end).
- ``is_dnd_active`` ventanas cruzan medianoche (start > end).
- Política conservadora: tz inválida → DND ignorado.
- start == end → ventana 24h (DND siempre activo).
- Bordes: start inclusivo · end exclusivo.
"""
from __future__ import annotations

from datetime import datetime, time, timezone

from backend.app.notifications.dnd import is_dnd_active, parse_hhmm


def test_parse_hhmm_valid():
    assert parse_hhmm("00:00") == time(0, 0)
    assert parse_hhmm("23:59") == time(23, 59)
    assert parse_hhmm("13:45") == time(13, 45)


def test_parse_hhmm_invalid():
    assert parse_hhmm(None) is None
    assert parse_hhmm("") is None
    assert parse_hhmm("24:00") is None
    assert parse_hhmm("12:60") is None
    assert parse_hhmm("12") is None
    assert parse_hhmm("12:30:00") is None
    assert parse_hhmm("ab:cd") is None


def test_dnd_inactive_when_no_window():
    assert is_dnd_active(
        dnd_start_local=None,
        dnd_end_local=None,
        tz_name="Europe/Madrid",
    ) is False
    assert is_dnd_active(
        dnd_start_local="22:00",
        dnd_end_local=None,
        tz_name="Europe/Madrid",
    ) is False
    assert is_dnd_active(
        dnd_start_local=None,
        dnd_end_local="08:00",
        tz_name="Europe/Madrid",
    ) is False


def test_dnd_active_same_day_window():
    """Ventana 13:00→14:00 en Europe/Madrid (UTC+1 invierno)."""
    now_utc = datetime(2026, 1, 15, 12, 30, tzinfo=timezone.utc)
    assert is_dnd_active(
        dnd_start_local="13:00",
        dnd_end_local="14:00",
        tz_name="Europe/Madrid",
        now_utc=now_utc,
    ) is True


def test_dnd_inactive_outside_same_day_window():
    now_utc = datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)
    assert is_dnd_active(
        dnd_start_local="13:00",
        dnd_end_local="14:00",
        tz_name="Europe/Madrid",
        now_utc=now_utc,
    ) is False


def test_dnd_overnight_window_active_after_start():
    """Ventana 22:00→08:00 · UTC 22:30 invierno = 23:30 Madrid."""
    now_utc = datetime(2026, 1, 15, 22, 30, tzinfo=timezone.utc)
    assert is_dnd_active(
        dnd_start_local="22:00",
        dnd_end_local="08:00",
        tz_name="Europe/Madrid",
        now_utc=now_utc,
    ) is True


def test_dnd_overnight_window_active_before_end():
    """Ventana 22:00→08:00 · UTC 06:30 invierno = 07:30 Madrid."""
    now_utc = datetime(2026, 1, 15, 6, 30, tzinfo=timezone.utc)
    assert is_dnd_active(
        dnd_start_local="22:00",
        dnd_end_local="08:00",
        tz_name="Europe/Madrid",
        now_utc=now_utc,
    ) is True


def test_dnd_overnight_window_inactive_during_day():
    now_utc = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    assert is_dnd_active(
        dnd_start_local="22:00",
        dnd_end_local="08:00",
        tz_name="Europe/Madrid",
        now_utc=now_utc,
    ) is False


def test_dnd_invalid_tz_returns_false():
    """Política conservadora: tz inválida → DND ignorado."""
    now_utc = datetime(2026, 1, 15, 23, 0, tzinfo=timezone.utc)
    assert is_dnd_active(
        dnd_start_local="22:00",
        dnd_end_local="08:00",
        tz_name="Atlantis/InvalidCity",
        now_utc=now_utc,
    ) is False


def test_dnd_24h_window_when_start_equals_end():
    """start == end → ventana 24h (DND siempre activo)."""
    now_utc = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    assert is_dnd_active(
        dnd_start_local="09:00",
        dnd_end_local="09:00",
        tz_name="Europe/Madrid",
        now_utc=now_utc,
    ) is True


def test_dnd_start_inclusive_end_exclusive():
    """Borde: start es inclusive · end exclusive."""
    # 13:00 local Madrid invierno = 12:00 UTC · DND activo (start)
    now_at_start = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    assert is_dnd_active(
        dnd_start_local="13:00",
        dnd_end_local="14:00",
        tz_name="Europe/Madrid",
        now_utc=now_at_start,
    ) is True
    # 14:00 local Madrid invierno = 13:00 UTC · DND inactivo (end)
    now_at_end = datetime(2026, 1, 15, 13, 0, tzinfo=timezone.utc)
    assert is_dnd_active(
        dnd_start_local="13:00",
        dnd_end_local="14:00",
        tz_name="Europe/Madrid",
        now_utc=now_at_end,
    ) is False


def test_dnd_uses_default_now_when_none():
    """now_utc=None usa datetime.now(UTC)."""
    result = is_dnd_active(
        dnd_start_local=None,
        dnd_end_local=None,
        tz_name="Europe/Madrid",
        now_utc=None,
    )
    assert result is False


def test_dnd_naive_datetime_treated_as_utc():
    naive = datetime(2026, 1, 15, 22, 30)
    assert is_dnd_active(
        dnd_start_local="22:00",
        dnd_end_local="08:00",
        tz_name="Europe/Madrid",
        now_utc=naive,
    ) is True
