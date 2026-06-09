"""M8 v5.1 — Tests OpenvasRunner + mapper + vuln orchestrator.

Cobertura (14 tests, todos offline — NO requieren Docker ni GVM vivo):

Parser XML GMP (4):
  1. linux high severity parsea findings + CVE + CVSS
  2. windows mixed severities counts match
  3. web ssl issues parsea family SSL and TLS -> mp.com.*
  4. malformed XML -> fallback silencioso

Mapper (3):
  5. coverage_stats minimum thresholds
  6. severity >= 9.0 maps a op.exp.4 + op.exp.7
  7. name overrides detectan path traversal / SMB signing / HSTS

Fixture mode (3):
  8. linux conformant -> 0 findings con severity !=info
  9. web ssl maps to mp.com.2 correctamente
  10. mock synthetic XML produce al menos 1 finding

Real degradado (2):
  11. real mode sin GVM env -> error controlado
  12. real mode con python-gvm roto (simulado) -> error controlado

Vuln orchestrator (2):
  13. should_trigger respeta targets + category (BASICA incluida)
  14. orchestrator ejecuta OpenVAS en chain y devuelve summary
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.motors.m08_verification.tools.openvas_ens_mapper import (
    coverage_stats,
    map_finding_to_ens,
    severity_to_ens,
)
from backend.app.motors.m08_verification.tools.openvas_runner import (
    OpenvasRunner,
)
from backend.app.motors.m08_verification.vuln_orchestrator import (
    run_vuln_audit,
    should_trigger,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ════════════════════════════════════════════════════════════════════
# Parser XML GMP
# ════════════════════════════════════════════════════════════════════


def test_parse_linux_high_severity_extracts_cve_and_cvss():
    raw = (FIXTURES_DIR / "openvas_report_linux_high_severity.xml").read_bytes()
    findings = OpenvasRunner.parse_output(raw)
    assert len(findings) == 4
    cves = [f["cve_id"] for f in findings if f["cve_id"]]
    assert "CVE-2021-41773" in cves
    assert "CVE-2018-15473" in cves
    # Apache path traversal tiene cvss 9.8
    path_trav = next(
        f for f in findings if "Path Traversal" in f["title"]
    )
    assert path_trav["cvss_score"] == 9.8
    assert path_trav["severity"] == "high"
    # op.exp.4 + op.exp.7 deberian estar presentes (CVSS >= 9.0)
    assert "op.exp.4" in path_trav["tool_metadata"]["ens_measures"]
    assert "op.exp.7" in path_trav["tool_metadata"]["ens_measures"]


def test_parse_windows_mixed_severities_counts():
    raw = (FIXTURES_DIR / "openvas_report_windows_mixed.xml").read_bytes()
    findings = OpenvasRunner.parse_output(raw)
    summary = OpenvasRunner.summarize(findings)
    assert summary["total"] == 4
    assert summary["by_severity"].get("high") == 2
    assert summary["by_severity"].get("medium") == 2
    # MSSQL empty SA password tiene CVSS 10
    mssql = next(
        f for f in findings if "SA login without password" in f["title"]
        or "MSSQL" in f["title"]
    )
    assert mssql["cvss_score"] == 10.0
    assert mssql["severity"] == "high"


def test_parse_web_ssl_issues_maps_family_to_mp_com():
    raw = (FIXTURES_DIR / "openvas_report_web_server_ssl_issues.xml").read_bytes()
    findings = OpenvasRunner.parse_output(raw)
    assert len(findings) == 4
    # Todos los SSL/TLS findings deberian mapear a mp.com.2
    ssl_findings = [
        f for f in findings
        if f["tool_metadata"]["nvt_family"] == "SSL and TLS"
    ]
    assert len(ssl_findings) >= 3
    for f in ssl_findings:
        assert "mp.com.2" in f["tool_metadata"]["ens_measures"]


def test_parse_malformed_xml_safe_fallback():
    assert OpenvasRunner.parse_output(b"") == []
    assert OpenvasRunner.parse_output(b"<not-xml") == []
    assert OpenvasRunner.parse_output(b"<root>no results here</root>") == []


# ════════════════════════════════════════════════════════════════════
# Mapper
# ════════════════════════════════════════════════════════════════════


def test_mapper_coverage_stats_minimum_thresholds():
    stats = coverage_stats()
    assert stats["families_mapped"] >= 12
    assert stats["name_overrides"] >= 8
    assert stats["unique_measures"] >= 12
    assert stats["labels_defined"] >= stats["unique_measures"]


def test_severity_to_ens_critical_and_high_bands():
    # CVSS critico (>=9) -> parcheo urgente + incidentes
    assert "op.exp.4" in severity_to_ens(9.8)
    assert "op.exp.7" in severity_to_ens(9.8)
    # CVSS high (7-8.9) -> solo mantenimiento
    assert severity_to_ens(7.5) == ["op.exp.4"]
    # CVSS medium (4-6.9) -> gestion cambios
    assert severity_to_ens(5.0) == ["op.exp.3"]
    # CVSS low / info
    assert severity_to_ens(2.0) == []
    assert severity_to_ens(None) == []
    assert severity_to_ens("bad-float") == []


def test_mapper_name_overrides_detect_specific_issues():
    # Path traversal
    ens = map_finding_to_ens("Web Servers", "Apache HTTP Server Path Traversal", 9.8)
    assert "op.exp.4" in ens
    assert "op.acc.4" in ens
    assert "mp.sw.1" in ens
    # HSTS missing
    ens = map_finding_to_ens(
        "Web application abuses", "HTTP Missing HSTS Header", 4.0,
    )
    assert "mp.com.2" in ens
    # SMB signing
    ens = map_finding_to_ens("Windows", "SMB signing not required", 4.3)
    assert "mp.com.3" in ens
    assert "op.exp.3" in ens


# ════════════════════════════════════════════════════════════════════
# Fixture mode
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fixture_linux_conformant_zero_high_findings():
    path = FIXTURES_DIR / "openvas_report_linux_conformant.xml"
    result = await OpenvasRunner.run_mode(
        targets=["10.0.12.51"], mode="fixture", fixture_path=path,
    )
    # Solo findings informational (Log)
    assert all(f["severity"] == "info" for f in result.findings)


@pytest.mark.asyncio
async def test_fixture_web_ssl_orchestrator_level_summary():
    path = FIXTURES_DIR / "openvas_report_web_server_ssl_issues.xml"
    result = await OpenvasRunner.run_mode(
        targets=["10.0.30.5"], mode="fixture", fixture_path=path,
    )
    summary = OpenvasRunner.summarize(result.findings)
    assert summary["total"] == 4
    # SSL/TLS deberian aportar mp.com.2 al menos
    assert "mp.com.2" in summary["ens_measures_unique"]


@pytest.mark.asyncio
async def test_mock_synthetic_xml_produces_findings():
    # mock sin fixture_path -> XML sintetico inline
    result = await OpenvasRunner.run_mode(
        targets=["127.0.0.1"], mode="mock",
    )
    assert len(result.findings) == 1
    assert result.findings[0]["tool"] == "openvas"
    assert result.findings[0]["severity"] == "info"


# ════════════════════════════════════════════════════════════════════
# Real degradado
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_real_without_gvm_credentials_returns_error(monkeypatch):
    for var in ("GVM_HOST", "GVM_USERNAME", "GVM_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    result = await OpenvasRunner.run_mode(
        targets=["10.0.0.1"], mode="real",
    )
    assert result.error is not None
    assert "gvm_credentials_missing" in result.error
    assert result.findings == []


@pytest.mark.asyncio
async def test_real_without_python_gvm_returns_error(monkeypatch):
    """Simulamos python-gvm roto para forzar el ImportError del runner."""
    original_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __import__

    def broken_import(name, *args, **kwargs):
        if name.startswith("gvm.") or name == "gvm":
            raise ImportError("gvm module not available (simulated)")
        return original_import(name, *args, **kwargs)

    # Parchear `__import__` globalmente para la duracion del test
    monkeypatch.setattr(
        "builtins.__import__", broken_import,
    )
    # Tambien configuramos env para pasar el primer check
    monkeypatch.setenv("GVM_HOST", "localhost")
    monkeypatch.setenv("GVM_USERNAME", "admin")
    monkeypatch.setenv("GVM_PASSWORD", "test")

    result = await OpenvasRunner.run_mode(
        targets=["10.0.0.1"], mode="real",
    )
    assert result.error is not None
    assert "python-gvm no instalado" in result.error


# ════════════════════════════════════════════════════════════════════
# Vuln orchestrator
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_vuln_should_trigger_includes_basica():
    # Sin targets -> skip
    assert should_trigger({"targets": []}, "MEDIA") is False
    # Targets BASICA -> activa (a diferencia del cloud orchestrator)
    assert should_trigger({"targets": ["10.0.0.1"]}, "BASICA") is True
    assert should_trigger({"targets": ["10.0.0.1"]}, "MEDIA") is True
    assert should_trigger({"targets": ["10.0.0.1"]}, "ALTA") is True
    assert should_trigger({"targets": ["10.0.0.1"]}, "") is False


@pytest.mark.asyncio
async def test_vuln_orchestrator_runs_openvas_and_summarizes():
    scope = {"targets": ["10.0.12.50"]}
    fixture = FIXTURES_DIR / "openvas_report_linux_high_severity.xml"
    out = await run_vuln_audit(
        scope, "BASICA", openvas_mode="fixture",
        openvas_fixture_path=fixture,
    )
    assert out["skipped"] is False
    assert out["tools_run"] == ["openvas"]
    assert out["summary"]["total"] == 4
    # Al menos 1 CVE referenciado (CVE-2021-41773)
    assert out["summary"]["cve_references_total"] >= 1
    # Mixed severity
    by_sev = out["summary"]["by_severity"]
    assert by_sev.get("high", 0) >= 1
