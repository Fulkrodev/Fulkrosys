"""Path-aware tests for ComplianceReportsService (atom 9.bis.6).

2 tests covering the development storage mode contract:
- Desktop folder writable → ``storage_mode='desktop'`` + filesystem path
- Desktop folder unavailable → ``storage_mode='inline'`` fallback

Production (MinIO) mode is exercised in integration with a live MinIO
bucket; unit tests here cover the dev-path branch only.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.app.motors.m_compliance_monitor.reports_service import (
    ComplianceReportsService,
)


@pytest.mark.asyncio
async def test_persist_report_writes_to_desktop(db, tmp_path, monkeypatch) -> None:
    """Dev env writes MD file to Desktop folder + persists row."""
    monkeypatch.setattr(
        "backend.app.motors.m_compliance_monitor.reports_service._is_production",
        lambda: False,
    )
    monkeypatch.setattr(
        "backend.app.motors.m_compliance_monitor.reports_service._desktop_root",
        lambda: tmp_path,
    )
    svc = ComplianceReportsService(db)
    period_end = datetime.now(timezone.utc)
    row = await svc.persist_report(
        report_type="weekly_status",
        period_start=period_end - timedelta(days=7),
        period_end=period_end,
        summary={"green": 12, "yellow": 3, "red": 0, "unknown": 2, "total": 17},
        body_markdown="# FULKRO Compliance Status Report\n\nTest body.",
        email_recipient="marcos@fulkro.es",
    )
    assert row.storage_mode == "desktop"
    assert row.storage_path is not None
    file_path = Path(row.storage_path)
    assert file_path.exists()
    assert "Test body" in file_path.read_text(encoding="utf-8")
    assert row.summary["green"] == 12


@pytest.mark.asyncio
async def test_persist_report_falls_back_to_inline_when_desktop_unavailable(
    db, monkeypatch, tmp_path
) -> None:
    """Server / CI without WSL mount → ``inline`` fallback (DB-only).

    Q3 · antes esto apuntaba a ``/no/such/path/that/should/never/exist`` dando
    por hecho que ``mkdir(parents=True)`` fallaria. Como root --que es como
    corre la imagen de test-- esa ruta se CREA sin problema, asi que el
    servicio escribia el informe, devolvia "desktop" y el test fallaba con
    `assert 'desktop' == 'inline'`. Dependia de una propiedad del entorno (no
    ser root) que no declaraba, igual que el puerto codificado o la clave
    ausente.

    Ahora la imposibilidad es estructural: se pide crear un directorio DENTRO
    de un fichero, y eso es `NotADirectoryError` (un `OSError`) para cualquier
    usuario, root incluido.
    """
    bloqueo = tmp_path / "esto-es-un-fichero"
    bloqueo.write_text("no soy un directorio", encoding="utf-8")

    monkeypatch.setattr(
        "backend.app.motors.m_compliance_monitor.reports_service._is_production",
        lambda: False,
    )
    monkeypatch.setattr(
        "backend.app.motors.m_compliance_monitor.reports_service._desktop_root",
        lambda: bloqueo / "dentro",
    )
    svc = ComplianceReportsService(db)
    period_end = datetime.now(timezone.utc)
    row = await svc.persist_report(
        report_type="weekly_status",
        period_start=period_end - timedelta(days=7),
        period_end=period_end,
        summary={"green": 0, "yellow": 0, "red": 0, "unknown": 17, "total": 17},
        body_markdown="# fallback",
        email_recipient=None,
    )
    assert row.storage_mode == "inline"
    assert row.storage_path is None
    assert row.body_markdown == "# fallback"
