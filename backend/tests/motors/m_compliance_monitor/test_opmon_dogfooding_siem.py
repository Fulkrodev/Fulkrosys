"""SIEM_INVESTIGATION.md · check op.mon en el dogfooding ENS de FULKRO.

El plugin ENS de dogfooding no tenía NINGÚN check op.mon (gap detectado por la
investigación SIEM). op.mon.1 (detección de intrusión) aplica desde MEDIA, el
nivel que FULKRO declara sobre sí mismo (R7). Este check lo cierra honestamente.
"""
from __future__ import annotations

import pytest

from backend.app.motors.m_compliance_monitor.checks import (
    CHECK_REGISTRY,
    check_intrusion_detection_present,
)
from backend.app.motors.m_compliance_monitor.normas import ens_rd_311_2022 as ens

pytestmark = pytest.mark.asyncio


async def test_opmon_check_registered_and_owned_by_ens():  # noqa: RUF029
    assert "intrusion_detection_present" in CHECK_REGISTRY
    spec = CHECK_REGISTRY["intrusion_detection_present"]
    assert "op.mon" in spec.regulatory_basis
    # el plugin ENS dogfooding lo posee + pesos suman 1.0 (validate en registro)
    assert "intrusion_detection_present" in ens.ENSModule.checks_owned
    ens.ENSModule.validate()
    assert abs(sum(ens.ENSModule.check_weights.values()) - 1.0) < 1e-3


async def test_opmon_red_without_ids(monkeypatch):
    monkeypatch.delenv("FULKRO_IDS_ENABLED", raising=False)
    # sin fail2ban/auditd (entorno de test) → RED honesto (no conformidad op.mon.1)
    r = await check_intrusion_detection_present(None)
    assert r.status == "red"
    assert "op.mon.1" in r.message


async def test_opmon_green_with_flag(monkeypatch):
    monkeypatch.setenv("FULKRO_IDS_ENABLED", "true")
    r = await check_intrusion_detection_present(None)
    assert r.status == "green"
    assert r.details.get("ids_enabled_flag") is True
