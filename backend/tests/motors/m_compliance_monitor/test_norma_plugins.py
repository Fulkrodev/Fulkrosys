"""NormaModule + NormaRegistry plugin tests (mini-atom 3)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.motors.m_compliance_monitor.normas import (
    CheckOutcome,
    NormaModule,
    NormaRegistry,
)


_NOW = datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc)


def test_registry_auto_discovery_finds_7_normas() -> None:
    """The plugin __init__ should discover and register every norma."""
    keys = set(NormaRegistry.keys())
    expected = {
        "RGPD_UE_2016_679",
        "LOPDGDD_3_2018",
        "LSSI_CE_34_2002",
        "AEPD_COOKIES_2020",
        "NIS2_UE_2022_2555",
        "ISO_27001_2022",
        "ENS_RD_311_2022",
    }
    assert expected.issubset(keys), f"missing normas: {expected - keys}"
    # Defensive: registry returns instances of NormaModule.
    for module in NormaRegistry.get_all():
        assert isinstance(module, NormaModule)


def test_every_plugin_weights_sum_to_one() -> None:
    """Static validation runs at register time, plus a defensive runtime check."""
    for module in NormaRegistry.get_all():
        if not module.check_weights:
            continue
        total = sum(module.check_weights.values())
        assert abs(total - 1.0) < 1e-3, (
            f"{module.norma_key}: weights sum to {total:.4f}"
        )
        for name in module.check_weights:
            assert name in module.checks_owned, (
                f"{module.norma_key}: weight for non-owned check {name!r}"
            )


def test_cross_cutting_checks_resolve_to_multiple_normas() -> None:
    """``ssl_cert_expiry`` is owned by NIS2 + ISO 27001 + ENS."""
    keys = {n.norma_key for n in NormaRegistry.get_by_check_owned("ssl_cert_expiry")}
    assert {"NIS2_UE_2022_2555", "ISO_27001_2022", "ENS_RD_311_2022"}.issubset(keys)

    breach_keys = {n.norma_key for n in NormaRegistry.get_by_check_owned("breach_workflow_ready")}
    assert {"RGPD_UE_2016_679", "LOPDGDD_3_2018", "NIS2_UE_2022_2555"}.issubset(breach_keys)


def test_calculate_score_weighted_status_coefficients() -> None:
    """Status → coefficient mapping (green=1, yellow=0.5, unknown=0.5, red=0)."""
    rgpd = NormaRegistry.get("RGPD_UE_2016_679")
    assert rgpd is not None
    all_green = [
        CheckOutcome(name, "green", "ok", _NOW, None)
        for name in rgpd.checks_owned
    ]
    assert rgpd.calculate_score(all_green) == 100.0

    all_red = [
        CheckOutcome(name, "red", "bad", _NOW, None)
        for name in rgpd.checks_owned
    ]
    assert rgpd.calculate_score(all_red) == 0.0

    all_yellow = [
        CheckOutcome(name, "yellow", "warn", _NOW, None)
        for name in rgpd.checks_owned
    ]
    assert rgpd.calculate_score(all_yellow) == 50.0


def test_score_to_status_thresholds() -> None:
    """≥85 green · 70-84 yellow · 0-69 red · 0 unknown."""
    iso = NormaRegistry.get("ISO_27001_2022")
    assert iso is not None
    assert iso.score_to_status(95.0) == "green"
    assert iso.score_to_status(85.0) == "green"
    assert iso.score_to_status(84.99) == "yellow"
    assert iso.score_to_status(70.0) == "yellow"
    assert iso.score_to_status(69.99) == "red"
    assert iso.score_to_status(0.0) == "unknown"


def test_iso_27001_generate_report_cites_annex_controls() -> None:
    iso = NormaRegistry.get("ISO_27001_2022")
    assert iso is not None
    outcomes = [
        CheckOutcome(name, "green", f"{name} ok", _NOW, None)
        for name in iso.checks_owned
    ]
    md = iso.generate_report_md(outcomes, _NOW, _NOW)
    assert "ISO/IEC 27001:2022" in md
    # Annex A controls cited.
    assert "A.8.13" in md
    assert "A.8.15" in md
    assert "Anexo A" in md or "Anexo" in md
    # Score line present.
    assert "100.0 %" in md or "100.00" in md or "100" in md


def test_nis2_priority_critical_frequency_weekly() -> None:
    nis2 = NormaRegistry.get("NIS2_UE_2022_2555")
    assert nis2 is not None
    assert nis2.priority == "critical"
    assert nis2.frequency == "weekly"
    cfg = nis2.get_scheduler_config()
    assert cfg["task"] == "compliance.generate_norma_report"
    assert cfg["args"] == ["NIS2_UE_2022_2555"]
    assert cfg["cron"]["day_of_week"] == "monday"


def test_rgpd_generate_report_lists_every_owned_check() -> None:
    rgpd = NormaRegistry.get("RGPD_UE_2016_679")
    assert rgpd is not None
    outcomes = [
        CheckOutcome(name, "green", "ok", _NOW, None)
        for name in rgpd.checks_owned
    ]
    md = rgpd.generate_report_md(outcomes, _NOW, _NOW)
    for name in rgpd.checks_owned:
        assert f"`{name}`" in md, f"missing check row for {name}"
    # Article references appear (RGPD Art. 15/17/20 etc).
    assert "Art. 33" in md
    assert "Art. 28" in md
    assert "Art. 30" in md
