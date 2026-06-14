"""M8 v5.1 — Tests ScoutSuiteRunner + mapper multi-cloud + orchestrator.

Cobertura (16 tests):

Parser (4):
  1. parse aws wrapped estructura services.<svc>.findings
  2. parse azure estructura services.<svc>.findings (provider detection)
  3. parse gcp estructura services.<svc>.findings
  4. parse malformed -> fallback silencioso

Mapper (3):
  5. coverage_stats total >= 25 checks
  6. detect_provider_from_check clasifica correctamente AWS/Azure/GCP
  7. aws coverage complementaria sin solape total con Prowler

Fixture mode (3):
  8. fixture aws_iam -> 4 findings (1 root + 2 mfaless + 1 multikey + 1 ct)
  9. fixture azure_storage_mixed -> severities danger/warning + ENS
  10. fixture gcp_compute_violations -> firewall + iam keys

Mock moto (AWS only, 2):
  11. mock aws iam detecta user sin MFA + multi-keys
  12. mock aws cloudtrail sin global trail detectado

Real degradado (2):
  13. real sin binario scout -> error controlado
  14. real sin credenciales aws -> skip

Orchestrator complementario (2):
  15. orchestrator aws -> corren Prowler + ScoutSuite
  16. orchestrator azure -> corre solo ScoutSuite (Prowler no)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.motors.m08_verification.cloud_orchestrator import (
    run_cloud_audit,
)
from backend.app.motors.m08_verification.tools.prowler_cis_ens_mapper import (
    CIS_TO_ENS,
)
from backend.app.motors.m08_verification.tools.scoutsuite_cloud_ens_mapper import (
    SCOUTSUITE_TO_ENS,
    coverage_stats,
    detect_provider_from_check,
)
from backend.app.motors.m08_verification.tools.scoutsuite_runner import (
    ScoutSuiteRunner,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ════════════════════════════════════════════════════════════════════
# Parser
# ════════════════════════════════════════════════════════════════════


def test_parse_aws_wrapped_services_findings():
    raw = json.dumps({
        "provider_code": "aws",
        "account_id": "123456789012",
        "services": {
            "iam": {
                "findings": {
                    "iam-root-account-used-recently": {
                        "description": "Root used recently",
                        "level": "danger",
                        "flagged_items": 1, "checked_items": 1,
                        "items": ["arn:aws:iam::123456789012:root"],
                    },
                },
            },
        },
    }).encode()
    findings = ScoutSuiteRunner.parse_output(raw)
    assert len(findings) == 1
    assert findings[0]["tool"] == "scoutsuite"
    md = findings[0]["tool_metadata"]
    assert md["provider"] == "aws"
    assert md["check_id"] == "iam-root-account-used-recently"
    assert "op.acc.4" in md["ens_measures"]


def test_parse_azure_provider_detected_from_prefix():
    raw = json.dumps({
        "provider_code": "azure",
        "services": {
            "storageaccounts": {
                "findings": {
                    "azure-storage-account-blob-public": {
                        "description": "Blob public access",
                        "level": "danger",
                        "flagged_items": 1, "checked_items": 1,
                        "items": ["/subs/x/sa/test"],
                    },
                },
            },
        },
    }).encode()
    findings = ScoutSuiteRunner.parse_output(raw)
    assert len(findings) == 1
    md = findings[0]["tool_metadata"]
    assert md["provider"] == "azure"
    # storage público → clasificación + acceso (mp.s.5 era código fantasma RD3/2010)
    assert "mp.info.2" in md["ens_measures"]


def test_parse_gcp_services_findings():
    raw = json.dumps({
        "provider_code": "gcp",
        "services": {
            "computeengine": {
                "findings": {
                    "gcp-compute-firewall-rule-allow-any": {
                        "description": "Firewall open",
                        "level": "danger",
                        "flagged_items": 2, "checked_items": 10,
                        "items": [
                            "//compute.googleapis.com/.../fw-a",
                            "//compute.googleapis.com/.../fw-b",
                        ],
                    },
                },
            },
        },
    }).encode()
    findings = ScoutSuiteRunner.parse_output(raw)
    # 1 finding_id con 2 items -> 2 findings (un finding por item)
    assert len(findings) == 2
    for f in findings:
        assert f["tool_metadata"]["provider"] == "gcp"
        assert "mp.com.1" in f["tool_metadata"]["ens_measures"]


def test_parse_malformed_returns_empty_silently():
    assert ScoutSuiteRunner.parse_output(b"") == []
    assert ScoutSuiteRunner.parse_output(b"not json") == []
    # Wrapper JS sin contenido valido
    assert ScoutSuiteRunner.parse_output(b"scoutsuite_results = ???;") == []


# ════════════════════════════════════════════════════════════════════
# Mapper
# ════════════════════════════════════════════════════════════════════


def test_mapper_coverage_stats_minimum_thresholds():
    stats = coverage_stats()
    assert stats["checks_total"] >= 25
    assert stats["checks_aws"] >= 5
    assert stats["checks_azure"] >= 8
    assert stats["checks_gcp"] >= 6
    assert stats["unique_measures"] >= 8


def test_detect_provider_from_check_id():
    assert detect_provider_from_check("azure-storage-account-blob-public") == "azure"
    assert detect_provider_from_check("gcp-compute-firewall-rule-allow-any") == "gcp"
    assert detect_provider_from_check("iam-root-account-used-recently") == "aws"
    assert detect_provider_from_check("cloudtrail-no-global-trail") == "aws"
    assert detect_provider_from_check("unknown-prefix") is None


def test_aws_coverage_complementary_to_prowler():
    """ScoutSuite AWS aporta >=5 checks que Prowler NO cubre."""
    prowler_check_ids = set(CIS_TO_ENS.keys())
    ss_aws_checks = [
        c for c in SCOUTSUITE_TO_ENS
        if detect_provider_from_check(c) == "aws"
    ]
    exclusive_to_scoutsuite = [
        c for c in ss_aws_checks
        if c.replace("-", "_") not in prowler_check_ids
    ]
    # Al menos 5 checks exclusivos de ScoutSuite
    assert len(exclusive_to_scoutsuite) >= 5, (
        f"solo {len(exclusive_to_scoutsuite)} exclusivos: {exclusive_to_scoutsuite}"
    )


# ════════════════════════════════════════════════════════════════════
# Fixture mode
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fixture_aws_iam_findings_multiple():
    path = FIXTURES_DIR / "scoutsuite_aws_iam_findings.json"
    assert path.exists()
    result = await ScoutSuiteRunner.run_mode(
        targets=["aws"], mode="fixture", fixture_path=path,
    )
    # root (1 item) + mfaless (2 items) + multikeys (1) + no-global-trail (0 items=1 finding)
    assert len(result.findings) >= 4
    check_ids = {f["tool_metadata"]["check_id"] for f in result.findings}
    assert "iam-root-account-used-recently" in check_ids
    assert "iam-user-with-password-and-no-mfa" in check_ids
    assert "cloudtrail-no-global-trail" in check_ids


@pytest.mark.asyncio
async def test_fixture_azure_storage_mixed_severities_and_ens():
    path = FIXTURES_DIR / "scoutsuite_azure_storage_mixed.json"
    result = await ScoutSuiteRunner.run_mode(
        targets=["azure"], mode="fixture", fixture_path=path,
    )
    summary = ScoutSuiteRunner.summarize(result.findings)
    assert summary["total"] >= 4  # 1+2+1+1
    # ScoutSuite level="danger" -> severity="high"
    assert summary["by_severity"].get("high", 0) >= 2
    assert summary["by_severity"].get("medium", 0) >= 1  # warning
    assert "mp.info.2" in summary["ens_measures_unique"]
    assert "mp.com.1" in summary["ens_measures_unique"]
    # Todos los findings con provider detectado como azure
    for f in result.findings:
        assert f["tool_metadata"]["provider"] == "azure"


@pytest.mark.asyncio
async def test_fixture_gcp_compute_violations_firewall_and_iam():
    path = FIXTURES_DIR / "scoutsuite_gcp_compute_violations.json"
    result = await ScoutSuiteRunner.run_mode(
        targets=["gcp"], mode="fixture", fixture_path=path,
    )
    check_ids = {f["tool_metadata"]["check_id"] for f in result.findings}
    assert "gcp-compute-firewall-rule-allow-any" in check_ids
    assert "gcp-iam-service-account-with-user-keys" in check_ids
    # Instance public IP tiene 2 items -> 2 findings
    public_ip_findings = [
        f for f in result.findings
        if f["tool_metadata"]["check_id"] == "gcp-compute-instance-public-ip"
    ]
    assert len(public_ip_findings) == 2


# ════════════════════════════════════════════════════════════════════
# Mock moto AWS
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_mock_aws_iam_detects_mfaless_and_multi_keys():
    result = await ScoutSuiteRunner.run_mode(
        targets=["aws"], mode="mock", services=("iam",),
    )
    check_ids = {f["tool_metadata"]["check_id"] for f in result.findings}
    assert "iam-user-with-password-and-no-mfa" in check_ids
    assert "iam-user-with-multiple-access-keys" in check_ids


@pytest.mark.asyncio
async def test_mock_aws_cloudtrail_no_global_trail_detected():
    result = await ScoutSuiteRunner.run_mode(
        targets=["aws"], mode="mock", services=("cloudtrail",),
    )
    check_ids = [
        f["tool_metadata"]["check_id"] for f in result.findings
    ]
    assert "cloudtrail-no-global-trail" in check_ids


# ════════════════════════════════════════════════════════════════════
# Real degradado
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_real_without_scout_binary_returns_controlled_error(monkeypatch):
    monkeypatch.setattr(
        "backend.app.motors.m08_verification.tools.scoutsuite_runner.is_binary_available",
        lambda binary: False,
    )
    result = await ScoutSuiteRunner.run_mode(
        targets=["aws"], mode="real", provider="aws",
    )
    assert result.error == "scoutsuite_not_installed"
    assert result.findings == []


@pytest.mark.asyncio
async def test_real_without_aws_credentials_skips(monkeypatch):
    monkeypatch.setattr(
        "backend.app.motors.m08_verification.tools.scoutsuite_runner.is_binary_available",
        lambda binary: True,
    )
    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("os.path.exists", lambda p: False)
    result = await ScoutSuiteRunner.run_mode(
        targets=["aws"], mode="real", provider="aws",
    )
    assert result.error == "aws_credentials_missing"
    assert result.findings == []


# ════════════════════════════════════════════════════════════════════
# Orchestrator complementariedad
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_orchestrator_aws_runs_prowler_plus_scoutsuite():
    scope = {"cloud_accounts": [{"provider": "aws"}]}
    prowler_fixture = FIXTURES_DIR / "prowler_iam_non_conformant.asff.json"
    scout_fixture = FIXTURES_DIR / "scoutsuite_aws_iam_findings.json"
    out = await run_cloud_audit(
        scope, "MEDIA", mode="fixture",
        fixture_path=prowler_fixture,
        scoutsuite_fixture_path=scout_fixture,
    )
    assert out["skipped"] is False
    assert out["tools_run"]["aws"] == ["prowler", "scoutsuite"]
    by_tool = out["summary"]["by_tool"]
    assert by_tool.get("prowler", 0) >= 3
    assert by_tool.get("scoutsuite", 0) >= 4


@pytest.mark.asyncio
async def test_orchestrator_azure_scoutsuite_only_no_prowler():
    scope = {"cloud_accounts": [{"provider": "azure"}]}
    scout_fixture = FIXTURES_DIR / "scoutsuite_azure_storage_mixed.json"
    out = await run_cloud_audit(
        scope, "ALTA", mode="fixture",
        fixture_path=None,
        scoutsuite_fixture_path=scout_fixture,
    )
    assert out["skipped"] is False
    assert out["tools_run"]["azure"] == ["scoutsuite"]
    # Prowler no se invoca para azure
    assert "azure" not in out["per_tool"].get("prowler", {})
    by_tool = out["summary"]["by_tool"]
    assert by_tool.get("scoutsuite", 0) >= 4
    assert "prowler" not in by_tool
