"""Tests M14 Contract.scan_window + integración con M08 scope_deriver.

Cubre SAN-B.MB-3.bis.3 (cierre TODO-M8-G3):
- Validación Pydantic ScanWindow (HHMM, ISO date, IANA tz)
- ContractService.set_scan_window persiste + clear con None
- fetch_scan_window_for_project retorna m14_contract o default
- derive_scope reporta scan_window_source correcto
- is_in_scan_window dict mode (cross-midnight, dias, fechas, tz)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.app.motors.m08_verification.scheduler import is_in_scan_window
from backend.app.motors.m08_verification.scope_deriver import (
    DEFAULT_SCAN_WINDOW,
    derive_scope,
    fetch_scan_window_for_project,
)
from backend.app.motors.m14_contracts.contract_service import (
    ContractError,
    ContractService,
)
from backend.app.motors.m14_contracts.schemas import (
    DEFAULT_SCAN_WINDOW as SCHEMA_DEFAULT,
    ScanWindow,
)
from backend.tests.conftest import setup_test_project


# ════════════════════════════════════════════════════════════════════
# 1. Pydantic ScanWindow schema validation (unit · sin DB)
# ════════════════════════════════════════════════════════════════════

def test_scan_window_canonical_default_valid():
    """DEFAULT_SCAN_WINDOW exportado matches schema canonical."""
    parsed = ScanWindow.model_validate(SCHEMA_DEFAULT)
    assert parsed.horario_inicio == "22:00"
    assert parsed.horario_fin == "06:00"
    assert parsed.tz == "Europe/Madrid"
    assert len(parsed.dias_ok) == 7
    assert parsed.dias_bloqueados == []
    assert parsed.fechas_bloqueadas == []


def test_scan_window_default_in_scope_deriver_matches_schema():
    """DEFAULT_SCAN_WINDOW re-exportado scope_deriver = schema canonical."""
    assert DEFAULT_SCAN_WINDOW == SCHEMA_DEFAULT


def test_scan_window_invalid_hhmm_raises():
    with pytest.raises(ValidationError, match="HH:MM"):
        ScanWindow(horario_inicio="25:00", horario_fin="06:00")
    with pytest.raises(ValidationError, match="HH:MM"):
        ScanWindow(horario_inicio="22:00", horario_fin="6:00")
    with pytest.raises(ValidationError, match="HH:MM"):
        ScanWindow(horario_inicio="22:60", horario_fin="06:00")


def test_scan_window_invalid_fecha_iso_raises():
    with pytest.raises(ValidationError, match="ISO YYYY-MM-DD"):
        ScanWindow(
            horario_inicio="22:00",
            horario_fin="06:00",
            fechas_bloqueadas=["2026/12/25"],
        )
    with pytest.raises(ValidationError, match="ISO YYYY-MM-DD"):
        ScanWindow(
            horario_inicio="22:00",
            horario_fin="06:00",
            fechas_bloqueadas=["31-12-2026"],
        )


def test_scan_window_invalid_tz_raises():
    with pytest.raises(ValidationError, match="IANA"):
        ScanWindow(horario_inicio="22:00", horario_fin="06:00", tz="Mars/Phobos")


def test_scan_window_cross_midnight_format_valid():
    """Formato ScanWindow acepta inicio>fin (cruza medianoche)."""
    w = ScanWindow(horario_inicio="22:00", horario_fin="06:00")
    assert w.horario_inicio == "22:00"
    assert w.horario_fin == "06:00"


def test_scan_window_dias_bloqueados_overlap_with_dias_ok():
    """Permitido: dias_bloqueados puede overlap con dias_ok (overrides)."""
    w = ScanWindow(
        horario_inicio="22:00",
        horario_fin="06:00",
        dias_ok=["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        dias_bloqueados=["sun"],
    )
    assert "sun" in w.dias_bloqueados
    assert "sun" in w.dias_ok


# ════════════════════════════════════════════════════════════════════
# 2. is_in_scan_window dict mode (unit · sin DB)
# ════════════════════════════════════════════════════════════════════

UTC_REF_MON_NIGHT = datetime(2026, 5, 4, 23, 0, tzinfo=timezone.utc)  # lunes 23h UTC
UTC_REF_MON_AFTERNOON = datetime(2026, 5, 4, 14, 0, tzinfo=timezone.utc)


def test_is_in_scan_window_dict_basic_inside():
    w = ScanWindow(horario_inicio="22:00", horario_fin="06:00", tz="UTC").model_dump()
    assert is_in_scan_window(UTC_REF_MON_NIGHT, window=w) is True


def test_is_in_scan_window_dict_basic_outside():
    w = ScanWindow(horario_inicio="22:00", horario_fin="06:00", tz="UTC").model_dump()
    assert is_in_scan_window(UTC_REF_MON_AFTERNOON, window=w) is False


def test_is_in_scan_window_dict_cross_midnight_pre_midnight():
    w = ScanWindow(horario_inicio="22:00", horario_fin="06:00", tz="UTC").model_dump()
    assert is_in_scan_window(
        datetime(2026, 5, 4, 22, 0, tzinfo=timezone.utc), window=w
    ) is True


def test_is_in_scan_window_dict_cross_midnight_post_midnight():
    w = ScanWindow(horario_inicio="22:00", horario_fin="06:00", tz="UTC").model_dump()
    assert is_in_scan_window(
        datetime(2026, 5, 5, 4, 0, tzinfo=timezone.utc), window=w
    ) is True


def test_is_in_scan_window_dict_at_window_end_excluded():
    w = ScanWindow(horario_inicio="22:00", horario_fin="06:00", tz="UTC").model_dump()
    assert is_in_scan_window(
        datetime(2026, 5, 5, 6, 0, tzinfo=timezone.utc), window=w
    ) is False


def test_is_in_scan_window_dict_dias_bloqueados_blocks():
    """Aunque hora está dentro, día bloqueado → False."""
    # 2026-05-03 = domingo (sun)
    sunday_night = datetime(2026, 5, 3, 23, 0, tzinfo=timezone.utc)
    w = ScanWindow(
        horario_inicio="22:00", horario_fin="06:00", tz="UTC",
        dias_bloqueados=["sun"],
    ).model_dump()
    assert is_in_scan_window(sunday_night, window=w) is False


def test_is_in_scan_window_dict_fechas_bloqueadas_blocks():
    """Festivo cliente · día válido pero fecha bloqueada → False."""
    monday_night = datetime(2026, 5, 4, 23, 0, tzinfo=timezone.utc)
    w = ScanWindow(
        horario_inicio="22:00", horario_fin="06:00", tz="UTC",
        fechas_bloqueadas=["2026-05-04"],
    ).model_dump()
    assert is_in_scan_window(monday_night, window=w) is False


def test_is_in_scan_window_dict_dias_ok_filter():
    """Solo sábados permitidos · lunes fuera."""
    monday_night = datetime(2026, 5, 4, 23, 0, tzinfo=timezone.utc)
    w = ScanWindow(
        horario_inicio="22:00", horario_fin="06:00", tz="UTC",
        dias_ok=["sat"],
    ).model_dump()
    assert is_in_scan_window(monday_night, window=w) is False


def test_is_in_scan_window_dict_tz_conversion():
    """22h UTC = 0h Madrid (+2h CEST mayo) → fuera de 22:00-06:00 Madrid."""
    # 2026-05-04 22:00 UTC = 2026-05-05 00:00 Madrid (CEST)
    # En Madrid: 00:00 está dentro de 22:00-06:00 → True
    ref = datetime(2026, 5, 4, 22, 0, tzinfo=timezone.utc)
    w = ScanWindow(
        horario_inicio="22:00", horario_fin="06:00", tz="Europe/Madrid",
    ).model_dump()
    assert is_in_scan_window(ref, window=w) is True


def test_is_in_scan_window_legacy_time_mode_still_works():
    """Backwards compat: signature time-based sigue funcional."""
    night = datetime(2026, 5, 4, 23, 30, tzinfo=timezone.utc)
    assert is_in_scan_window(night) is True
    afternoon = datetime(2026, 5, 4, 14, 0, tzinfo=timezone.utc)
    assert is_in_scan_window(afternoon) is False


# ════════════════════════════════════════════════════════════════════
# 3. ContractService.set_scan_window + fetch (integration · DB)
# ════════════════════════════════════════════════════════════════════

async def _create_minimal_contract(db, project_id: str) -> uuid.UUID:
    """Inserta Contract minimal directamente (skip lifecycle generate)."""
    cid = uuid.uuid4()
    await db.execute(text(
        "INSERT INTO contracts (id, project_id, plantilla_id, estado, created_at) "
        "VALUES (:id, :pid, 'C-001', 'draft', now())"
    ), {"id": str(cid), "pid": project_id})
    await db.flush()
    return cid


@pytest.mark.asyncio
async def test_set_scan_window_persists(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    cid = await _create_minimal_contract(db, project_id)

    window_payload = ScanWindow(
        horario_inicio="20:00", horario_fin="08:00",
        dias_ok=["sat", "sun"],
    ).model_dump()
    c = await ContractService().set_scan_window(db, cid, window_payload)
    assert c.scan_window == window_payload


@pytest.mark.asyncio
async def test_set_scan_window_clear_with_none(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    cid = await _create_minimal_contract(db, project_id)

    await ContractService().set_scan_window(
        db, cid, ScanWindow(horario_inicio="22:00", horario_fin="06:00").model_dump()
    )
    c = await ContractService().set_scan_window(db, cid, None)
    assert c.scan_window is None


@pytest.mark.asyncio
async def test_set_scan_window_unknown_contract_raises(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    with pytest.raises(ContractError, match="no encontrado"):
        await ContractService().set_scan_window(db, uuid.uuid4(), None)


# ════════════════════════════════════════════════════════════════════
# 4. fetch_scan_window_for_project + derive_scope (integration · DB)
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_fetch_scan_window_returns_default_when_no_contract(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    window, source = await fetch_scan_window_for_project(db, uuid.UUID(project_id))
    assert window == DEFAULT_SCAN_WINDOW
    assert source == "default"


@pytest.mark.asyncio
async def test_fetch_scan_window_uses_m14_contract_when_present(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    cid = await _create_minimal_contract(db, project_id)
    custom = ScanWindow(
        horario_inicio="00:00", horario_fin="04:00", dias_ok=["sat"]
    ).model_dump()
    await ContractService().set_scan_window(db, cid, custom)

    window, source = await fetch_scan_window_for_project(db, uuid.UUID(project_id))
    assert window == custom
    assert source == "m14_contract"


@pytest.mark.asyncio
async def test_derive_scope_reports_scan_window_source_m14_contract(db):
    """End-to-end: derive_scope refleja scan_window_source correctamente."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    cid = await _create_minimal_contract(db, project_id)
    custom = ScanWindow(
        horario_inicio="01:00", horario_fin="05:00",
    ).model_dump()
    await ContractService().set_scan_window(db, cid, custom)

    scope, derived = await derive_scope(
        db, uuid.UUID(project_id), category="BASICO",
    )
    assert scope["scan_window"] == custom
    assert derived["scan_window_source"] == "m14_contract"


@pytest.mark.asyncio
async def test_derive_scope_reports_scan_window_source_default(db):
    """Sin Contract scan_window populated → source 'default'."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    scope, derived = await derive_scope(
        db, uuid.UUID(project_id), category="BASICO",
    )
    assert scope["scan_window"] == DEFAULT_SCAN_WINDOW
    assert derived["scan_window_source"] == "default"
