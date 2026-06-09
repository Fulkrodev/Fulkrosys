"""M8 v5.1 — Tests ProwlerRunner + mapeo CIS->ENS + orchestrator cloud.

Cobertura (13 tests):

Parser / mapper (4):
  1 parse_output acepta formato {"Findings":[...]}
  2 parse_output acepta lista plana
  3 parse_output malformed -> fallback silencioso
  4 coverage_stats del mapper CIS->ENS >= 20 checks

Modo fixture (3):
  5 fixture iam_non_conformant -> 3 findings con ens_measures
  6 fixture iam_conformant -> 0 findings
  7 fixture s3_mixed -> critical + high + medium en mix

Modo mock (moto, 3):
  8 mock iam detecta user sin MFA
  9 mock s3 detecta bucket sin encryption + sin public access block
  10 mock ec2 detecta SG abierto al SSH

Modo real (2):
  11 real sin binario en PATH -> error controlado
  12 real sin credenciales AWS -> skip

Orchestrator (1):
  13 should_trigger respeta category + cloud_accounts
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.motors.m08_verification.cloud_orchestrator import (
    run_cloud_audit,
    should_trigger,
)
from backend.app.motors.m08_verification.tools.prowler_cis_ens_mapper import (
    coverage_stats,
    map_check_to_ens,
)
from backend.app.motors.m08_verification.tools.prowler_runner import ProwlerRunner


FIXTURES_DIR = (
    Path(__file__).resolve().parent / "fixtures"
)


# ════════════════════════════════════════════════════════════════════
# Parser + Mapper
# ════════════════════════════════════════════════════════════════════


def test_parse_output_accepts_wrapped_findings():
    raw = json.dumps({
        "Findings": [{
            "Title": "demo",
            "Severity": {"Label": "HIGH"},
            "Resources": [{"Id": "arn:aws:s3:::x"}],
            "ProductFields": {
                "ProviderName": "prowler",
                "ProwlerCheckId": "s3_bucket_public_access",
            },
            "Compliance": {"Status": "FAILED", "RelatedRequirements": ["CIS-2.1.5"]},
        }],
    }).encode()
    findings = ProwlerRunner.parse_output(raw)
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"
    assert "mp.s.5" in findings[0]["tool_metadata"]["ens_measures"]


def test_parse_output_accepts_flat_list():
    raw = json.dumps([{
        "Title": "demo flat",
        "Severity": {"Label": "CRITICAL"},
        "Resources": [{"Id": "arn:aws:iam::1:root"}],
        "ProductFields": {
            "ProviderName": "prowler",
            "ProwlerCheckId": "iam_root_mfa_enabled",
        },
    }]).encode()
    findings = ProwlerRunner.parse_output(raw)
    assert len(findings) == 1
    assert findings[0]["severity"] == "critical"
    assert findings[0]["tool_metadata"]["ens_measures"] == ["op.acc.5", "op.acc.4"]


def test_parse_output_malformed_returns_empty_silently():
    assert ProwlerRunner.parse_output(b"") == []
    assert ProwlerRunner.parse_output(b"not json at all") == []
    assert ProwlerRunner.parse_output(b"prowler started...\n") == []


def test_mapper_coverage_stats_minimum_thresholds():
    stats = coverage_stats()
    assert stats["checks_mapped"] >= 20
    assert stats["unique_measures"] >= 10
    assert stats["labels_defined"] >= stats["unique_measures"]
    # Unknown check_id -> lista vacia
    assert map_check_to_ens("not_a_real_check") == []


# ════════════════════════════════════════════════════════════════════
# Modo fixture
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fixture_iam_non_conformant_three_findings_with_ens():
    path = FIXTURES_DIR / "prowler_iam_non_conformant.asff.json"
    assert path.exists(), f"fixture missing: {path}"
    result = await ProwlerRunner.run_mode(
        targets=["aws"], mode="fixture", fixture_path=path,
    )
    assert result.return_code == 0
    assert len(result.findings) == 3
    # Todos deben tener al menos 1 ens_measure mapeado
    for f in result.findings:
        assert f["tool_metadata"]["ens_measures"], f"finding sin ENS: {f}"
    severities = [f["severity"] for f in result.findings]
    assert "critical" in severities
    assert "high" in severities


@pytest.mark.asyncio
async def test_fixture_iam_conformant_zero_findings():
    path = FIXTURES_DIR / "prowler_iam_conformant.asff.json"
    result = await ProwlerRunner.run_mode(
        targets=["aws"], mode="fixture", fixture_path=path,
    )
    assert result.return_code == 0
    assert result.findings == []


@pytest.mark.asyncio
async def test_fixture_s3_mixed_severity_distribution():
    path = FIXTURES_DIR / "prowler_s3_mixed.asff.json"
    result = await ProwlerRunner.run_mode(
        targets=["aws"], mode="fixture", fixture_path=path,
    )
    summary = ProwlerRunner.summarize(result.findings)
    assert summary["total"] == 3
    assert summary["by_severity"].get("critical") == 1
    assert summary["by_severity"].get("high") == 1
    assert summary["by_severity"].get("medium") == 1
    # Hit sobre cifrado + confidencialidad
    assert "mp.info.3" in summary["ens_measures_unique"]
    assert "mp.s.5" in summary["ens_measures_unique"]


# ════════════════════════════════════════════════════════════════════
# Modo mock (moto)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_mock_iam_detects_user_without_mfa():
    result = await ProwlerRunner.run_mode(
        targets=["aws"], mode="mock", services=("iam",),
    )
    check_ids = [
        f["tool_metadata"]["check_id"] for f in result.findings
    ]
    assert "iam_user_mfa_enabled_console_access" in check_ids


@pytest.mark.asyncio
async def test_mock_s3_detects_encryption_and_public_access():
    result = await ProwlerRunner.run_mode(
        targets=["aws"], mode="mock", services=("s3",),
    )
    check_ids = {
        f["tool_metadata"]["check_id"] for f in result.findings
    }
    assert "s3_bucket_default_encryption" in check_ids
    assert "s3_bucket_public_access" in check_ids


@pytest.mark.asyncio
async def test_mock_ec2_detects_open_ssh_security_group():
    result = await ProwlerRunner.run_mode(
        targets=["aws"], mode="mock", services=("ec2",),
    )
    check_ids = [
        f["tool_metadata"]["check_id"] for f in result.findings
    ]
    assert "ec2_securitygroup_allow_ingress_from_internet_to_ssh" in check_ids
    # Y el mapeo ENS tiene mp.com.1
    ssh_findings = [
        f for f in result.findings
        if f["tool_metadata"]["check_id"]
        == "ec2_securitygroup_allow_ingress_from_internet_to_ssh"
    ]
    assert "mp.com.1" in ssh_findings[0]["tool_metadata"]["ens_measures"]


# ════════════════════════════════════════════════════════════════════
# Modo real (degradado controlado)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_real_without_prowler_binary_returns_controlled_error(monkeypatch):
    # Forzamos que is_binary_available devuelva False
    monkeypatch.setattr(
        "backend.app.motors.m08_verification.tools.prowler_runner.is_binary_available",
        lambda binary: False,
    )
    result = await ProwlerRunner.run_mode(
        targets=["aws"], mode="real", provider="aws",
    )
    assert result.return_code == 0
    assert result.error == "prowler_not_installed"
    assert result.findings == []


@pytest.mark.asyncio
async def test_real_without_credentials_skips_safely(monkeypatch):
    # Finge que prowler SI existe pero sin credenciales
    monkeypatch.setattr(
        "backend.app.motors.m08_verification.tools.prowler_runner.is_binary_available",
        lambda binary: True,
    )
    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("os.path.exists", lambda p: False)
    result = await ProwlerRunner.run_mode(
        targets=["aws"], mode="real", provider="aws",
    )
    assert result.error == "aws_credentials_missing"
    assert result.findings == []


# ════════════════════════════════════════════════════════════════════
# Orchestrator cloud
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_orchestrator_triggers_only_when_cloud_and_media_plus():
    # Sin cloud -> skip
    assert should_trigger({"cloud_accounts": []}, "MEDIA") is False
    # Cloud pero BASICA -> skip
    assert should_trigger({"cloud_accounts": ["aws"]}, "BASICA") is False
    # Cloud + MEDIA -> trigger
    assert should_trigger({"cloud_accounts": ["aws"]}, "MEDIA") is True
    # Cloud + ALTA -> trigger
    assert should_trigger({"cloud_accounts": [{"provider": "aws"}]}, "ALTA") is True

    # Run end-to-end en modo fixture + category MEDIA
    scope = {"cloud_accounts": [{"provider": "aws"}]}
    fixture = FIXTURES_DIR / "prowler_s3_mixed.asff.json"
    out = await run_cloud_audit(
        scope, "MEDIA", mode="fixture", fixture_path=fixture,
    )
    assert out["skipped"] is False
    assert out["mode_used"] == "fixture"
    assert out["providers_audited"] == ["aws"]
    assert out["summary"]["total"] == 3
