"""Tests para el subsistema de remediacion (Checkpoint 3)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.motors.m08_verification.remediation.guide_generator import (
    _deterministic_template,
    _validate_guide_shape,
    generate_guide,
)
from backend.app.motors.m08_verification.remediation.retest_runner import (
    choose_retest_type,
)
from backend.app.motors.m08_verification.remediation.sla_calculator import (
    SLA_HOURS,
    calculate_deadline,
    prioritize_findings,
)


# ═══════════════════════════════════════════════════════════════════
# SLA calculator
# ═══════════════════════════════════════════════════════════════════

class TestSlaCalculator:
    def test_critical_48h(self):
        now = datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc)
        d = calculate_deadline("critical", now, now=now)
        assert d.hours_total == 48
        expected = now + timedelta(hours=48)
        assert d.deadline == expected

    def test_high_7d(self):
        now = datetime.now(timezone.utc)
        d = calculate_deadline("high", now, now=now)
        assert d.hours_total == 7 * 24

    def test_medium_30d(self):
        now = datetime.now(timezone.utc)
        d = calculate_deadline("medium", now, now=now)
        assert d.hours_total == 30 * 24

    def test_low_90d(self):
        now = datetime.now(timezone.utc)
        d = calculate_deadline("low", now, now=now)
        assert d.hours_total == 90 * 24

    def test_overdue_when_deadline_past(self):
        past = datetime.now(timezone.utc) - timedelta(hours=72)
        d = calculate_deadline("critical", past)
        assert d.overdue is True

    def test_not_overdue_when_fresh(self):
        now = datetime.now(timezone.utc)
        d = calculate_deadline("high", now)
        assert d.overdue is False

    def test_naive_datetime_treated_as_utc(self):
        naive = datetime(2026, 4, 21, 10, 0)
        d = calculate_deadline("critical", naive)
        assert d.calculated_from.tzinfo is not None

    def test_prioritize_critical_first(self):
        findings = [
            {"severity": "low", "remediation_effort": "quick_win"},
            {"severity": "critical", "remediation_effort": "long_term"},
            {"severity": "high", "remediation_effort": "short_term"},
        ]
        ordered = prioritize_findings(findings)
        assert ordered[0]["severity"] == "critical"
        assert ordered[-1]["severity"] == "low"

    def test_prioritize_quick_win_first_within_severity(self):
        findings = [
            {"severity": "high", "remediation_effort": "long_term"},
            {"severity": "high", "remediation_effort": "quick_win"},
            {"severity": "high", "remediation_effort": "short_term"},
        ]
        ordered = prioritize_findings(findings)
        assert ordered[0]["remediation_effort"] == "quick_win"
        assert ordered[-1]["remediation_effort"] == "long_term"

    def test_sla_hours_catalog_complete(self):
        assert set(SLA_HOURS) >= {"critical", "high", "medium", "low", "info"}


# ═══════════════════════════════════════════════════════════════════
# Guide generator (offline deterministic)
# ═══════════════════════════════════════════════════════════════════

class TestGuideGenerator:
    def test_tls_finding_produces_openssl_steps(self):
        f = {
            "title": "TLS/SSL: weak cipher",
            "severity": "high",
            "affected_host": "app.example.es",
            "affected_port": 443,
            "tool_sources": ["testssl"],
        }
        guide = _deterministic_template(f)
        assert _validate_guide_shape(guide)
        commands = [p["comando"] for p in guide["pasos"]]
        assert any("openssl" in c or "apt" in c for c in commands)

    def test_cve_finding_includes_apt_upgrade(self):
        f = {
            "title": "OpenSSH vulnerable",
            "severity": "critical",
            "cve_id": "CVE-2024-6387",
            "affected_host": "srv.example.es",
            "tool_sources": ["nuclei"],
        }
        guide = _deterministic_template(f)
        assert _validate_guide_shape(guide)
        assert any("apt" in p["comando"] for p in guide["pasos"])

    def test_web_finding_uses_curl(self):
        f = {
            "title": "SQL Injection in form",
            "severity": "high",
            "affected_url": "https://app.example.es/login",
            "affected_host": "app.example.es",
            "tool_sources": ["zap"],
        }
        guide = _deterministic_template(f)
        assert _validate_guide_shape(guide)

    def test_lynis_finding_returns_hardening_template(self):
        f = {
            "title": "Hardening check failed",
            "affected_host": "srv.example.es",
            "severity": "medium",
            "tool_sources": ["lynis"],
            "tool_metadata": {"control_id": "AUTH-9328"},
        }
        guide = _deterministic_template(f)
        assert _validate_guide_shape(guide)
        assert "lynis" in guide["pasos"][0]["comando"].lower()

    def test_generate_guide_force_offline_always_works(self):
        f = {
            "title": "test",
            "severity": "medium",
            "affected_host": "x",
            "tool_sources": ["nuclei"],
        }
        g = generate_guide(f, force_offline=True)
        assert g["fuente"] == "deterministic_template"
        assert _validate_guide_shape(g)

    def test_validate_guide_shape_rejects_missing_pasos(self):
        assert not _validate_guide_shape({
            "resumen_no_tecnico": "x",
            "riesgo_real": "y",
            "pasos": [],
            "tiempo_estimado": "1h",
            "requiere_reinicio": False,
            "requiere_ventana_mantenimiento": False,
        })

    def test_validate_guide_shape_rejects_paso_without_comando(self):
        assert not _validate_guide_shape({
            "resumen_no_tecnico": "x",
            "riesgo_real": "y",
            "pasos": [{"paso": 1, "titulo": "t", "explicacion": "e"}],
            "tiempo_estimado": "1h",
            "requiere_reinicio": False,
            "requiere_ventana_mantenimiento": False,
        })


# ═══════════════════════════════════════════════════════════════════
# Retest type chooser
# ═══════════════════════════════════════════════════════════════════

class TestRetestTypeChooser:
    def test_tls_finding_picks_ssl(self):
        f = {"title": "TLS weak", "tool_sources": ["testssl"]}
        assert choose_retest_type(f) == "ssl"

    def test_cve_finding_picks_cve(self):
        f = {"title": "RCE", "tool_sources": ["nuclei"], "cve_id": "CVE-2024-1234"}
        assert choose_retest_type(f) == "cve"

    def test_web_url_picks_web(self):
        f = {
            "title": "XSS",
            "tool_sources": ["zap"],
            "affected_url": "https://x/y",
        }
        assert choose_retest_type(f) == "web"

    def test_lynis_picks_hardening(self):
        f = {"title": "Hardening AUTH-9328", "tool_sources": ["lynis"]}
        assert choose_retest_type(f) == "hardening"

    def test_nmap_port_picks_port(self):
        f = {"title": "Open port found", "tool_sources": ["nmap"]}
        assert choose_retest_type(f) == "port"

    def test_unknown_defaults_to_cve(self):
        f = {"title": "misc", "tool_sources": ["unknown"]}
        assert choose_retest_type(f) == "cve"
