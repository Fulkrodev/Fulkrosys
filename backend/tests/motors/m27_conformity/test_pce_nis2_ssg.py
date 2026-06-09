"""Tests PCE-NIS2 + PCE-SSG catalogs · SAN-C.MB-10.5."""
from __future__ import annotations

from pathlib import Path

import yaml

from backend.app.motors.m27_conformity.service import (
    KNOWN_OVERLAYS,
    detect_overlay,
)


_CATALOGS_DIR = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "motors"
    / "m27_conformity"
    / "catalogs"
)


def test_pce_nis2_yaml_exists_and_valid():
    path = _CATALOGS_DIR / "pce_nis2.yaml"
    assert path.exists()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["overlay_type"] == "pce_nis2"
    assert data["ccn_stic"] == "892"
    assert any(m["code"] == "nis2.notif.1" for m in data["extra_measures"])
    assert data["reinforce_thresholds"]["notification_alert_max_hours"] == 24


def test_pce_ssg_yaml_exists_and_valid():
    path = _CATALOGS_DIR / "pce_ssg.yaml"
    assert path.exists()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["overlay_type"] == "pce_ssg"
    assert data["ccn_stic"] == "896"
    assert {lvl["level"] for lvl in data["maturity_levels"]} == {
        "L1_basico", "L2_intermedio", "L3_avanzado",
    }


def test_pce_registry_includes_nis2_and_ssg():
    assert "PCE-NIS2" in KNOWN_OVERLAYS
    assert "PCE-SSG" in KNOWN_OVERLAYS
    assert KNOWN_OVERLAYS["PCE-NIS2"]["ccn_stic"] == "892"
    assert KNOWN_OVERLAYS["PCE-SSG"]["ccn_stic"] == "896"


def test_detect_overlay_nis2_essential_returns_pce_nis2():
    result = detect_overlay(sector="energia", category="ALTA", nis2_status="essential")
    assert result["overlay_code"] == "PCE-NIS2"


def test_detect_overlay_nis2_important_returns_pce_nis2():
    result = detect_overlay(sector="transporte", category="MEDIA", nis2_status="important")
    assert result["overlay_code"] == "PCE-NIS2"


def test_detect_overlay_provider_mssp_returns_pce_ssg():
    result = detect_overlay(sector="servicios_profesionales", category="MEDIA", provider_type="mssp")
    assert result["overlay_code"] == "PCE-SSG"


def test_detect_overlay_provider_priority_over_nis2():
    """SSG provider con NIS2 status prioriza PCE-SSG (es el rol del proveedor)."""
    result = detect_overlay(
        sector="servicios", category="ALTA",
        nis2_status="essential", provider_type="mssp",
    )
    assert result["overlay_code"] == "PCE-SSG"


def test_detect_overlay_no_nis2_no_provider_falls_back():
    """Sin flags NIS2/SSG · comportamiento legacy intacto."""
    result = detect_overlay(sector="salud", category="MEDIA")
    assert result["overlay_code"] == "PCE-SALUD"
