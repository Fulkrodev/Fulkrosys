"""M8 v5.1 — Prowler runner (cloud security: AWS/Azure/GCP/M365).

Prowler escanea cuentas cloud produciendo findings en formato ASFF
(AWS Security Finding Format) al que el runner aplica dos enriquecimientos:

1. Parser a ``FindingCandidate`` normalizado (todas las tools comparten schema).
2. Mapeo ``ProwlerCheckId`` -> medidas ENS Anexo II (ver prowler_cis_ens_mapper).

Tres modos de ejecucion:

- ``fixture`` (default tests): carga JSON ASFF pre-grabado. Determinista, sin
  deps externas. Uso: ``ProwlerRunner.run_mode(["aws"], mode="fixture",
  fixture_path=Path("...asff.json"))``.

- ``mock``: levanta moto (mock AWS) con recursos sembrados por el runner
  (IAM users sin MFA, S3 bucket publico, EC2 SG abierto) y produce findings
  ASFF sinteticos introspeccionando el mock. Sirve para tests de integracion
  sin cuenta real ni binario prowler.

- ``real``: invoca el binario ``prowler`` como subprocess contra la cuenta
  AWS real. Requiere (a) prowler en PATH, (b) credenciales AWS (env o
  ``~/.aws/credentials``). Si falta algo devuelve resultado vacio con error
  descriptivo, sin romper la invocacion.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Sequence

from .base import (
    BaseRunner,
    FindingCandidate,
    RunnerResult,
    excerpt,
    is_binary_available,
    normalize_severity,
    run_subprocess,
)
from .prowler_cis_ens_mapper import describe_ens_measure, map_check_to_ens

logger = logging.getLogger(__name__)


ProwlerMode = Literal["fixture", "mock", "real"]


# ────────────────────────────────────────────────────────────────────
# Runner
# ────────────────────────────────────────────────────────────────────


class ProwlerRunner(BaseRunner):
    TOOL = "prowler"
    BINARY = "prowler"
    DEFAULT_TIMEOUT_SECONDS = 60 * 60  # 60 min

    # ══════════════════════════════════════════════════════════════
    # API publica — contrato BaseRunner (``run``) + extended (``run_mode``)
    # ══════════════════════════════════════════════════════════════

    @classmethod
    async def run(
        cls,
        targets: Sequence[str],
        *,
        timeout_seconds: int | None = None,
        provider: str = "aws",
    ) -> RunnerResult:
        """Compatibilidad con BaseRunner: intenta real, skip si no hay creds."""
        return await cls.run_mode(
            targets, mode="real", timeout_seconds=timeout_seconds, provider=provider,
        )

    @classmethod
    async def run_mode(
        cls,
        targets: Sequence[str],
        *,
        mode: ProwlerMode = "fixture",
        timeout_seconds: int | None = None,
        provider: str = "aws",
        fixture_path: Path | None = None,
        services: Sequence[str] = ("iam", "s3", "ec2"),
    ) -> RunnerResult:
        """Ejecuta en el modo elegido. Devuelve RunnerResult normalizado."""
        started = datetime.now(timezone.utc)
        targets_list = list(targets)

        # SAN-B.MB-7.bis · MCP wire-up (real mode only · fixture/mock para tests)
        if mode == "real":
            from backend.app.mcp_client import try_invoke_mcp_or_none
            mcp_resp = await try_invoke_mcp_or_none(
                server="cloud", tool="prowler_audit",
                args={"target": targets_list[0] if targets_list else "", "provider": provider},
                timeout_seconds=timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS,
            )
            if mcp_resp is not None:
                return cls.from_mcp_response(mcp_resp, targets_list, started)

        if mode == "fixture":
            return cls._run_fixture(targets_list, started, fixture_path)

        if mode == "mock":
            return cls._run_mock(targets_list, started, services)

        if mode == "real":
            return await cls._run_real(
                targets_list,
                started,
                provider=provider,
                timeout_seconds=timeout_seconds,
                services=services,
            )

        raise ValueError(f"prowler: mode invalido {mode!r}")

    # ══════════════════════════════════════════════════════════════
    # Modo fixture
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def _run_fixture(
        cls,
        targets: list[str],
        started: datetime,
        fixture_path: Path | None,
    ) -> RunnerResult:
        if fixture_path is None or not fixture_path.exists():
            return cls.make_result(
                targets=targets, started_at=started, return_code=0,
                raw_output=b"", findings=[],
                error=f"fixture path no existe: {fixture_path!r}",
            )
        raw = fixture_path.read_bytes()
        findings = cls.parse_output(raw)
        return cls.make_result(
            targets=targets, started_at=started, return_code=0,
            raw_output=raw, findings=findings,
        )

    # ══════════════════════════════════════════════════════════════
    # Modo mock (moto)
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def _run_mock(
        cls,
        targets: list[str],
        started: datetime,
        services: Sequence[str],
    ) -> RunnerResult:
        try:
            from moto import mock_aws  # type: ignore
        except ImportError:
            return cls.make_result(
                targets=targets, started_at=started, return_code=0,
                raw_output=b"moto not installed",
                findings=[],
                error="moto no instalado: pip install 'moto[iam,s3,ec2]>=5.0'",
            )

        with mock_aws():
            cls._seed_mock_aws_environment(services)
            synthetic_asff = cls._introspect_mock_for_findings(services)

        raw = json.dumps({"Findings": synthetic_asff}).encode("utf-8")
        findings = cls.parse_output(raw)
        return cls.make_result(
            targets=targets, started_at=started, return_code=0,
            raw_output=raw, findings=findings,
        )

    @staticmethod
    def _seed_mock_aws_environment(services: Sequence[str]) -> None:
        """Crea recursos AWS inseguros en el mock para que haya findings."""
        import boto3  # type: ignore

        region = "eu-central-1"
        if "iam" in services:
            iam = boto3.client("iam", region_name=region)
            iam.create_user(UserName="fulkro-admin")
            # Le damos consola pero no MFA
            iam.create_login_profile(
                UserName="fulkro-admin", Password="AdminTemp1!", PasswordResetRequired=False,
            )
        if "s3" in services:
            s3 = boto3.client("s3", region_name=region)
            s3.create_bucket(
                Bucket="fulkro-public-bucket",
                CreateBucketConfiguration={"LocationConstraint": region},
            )
            # No encryption, intencionalmente
            s3.create_bucket(
                Bucket="fulkro-unencrypted-bucket",
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        if "ec2" in services:
            ec2 = boto3.client("ec2", region_name=region)
            vpcs = ec2.describe_vpcs()["Vpcs"]
            vpc_id = vpcs[0]["VpcId"] if vpcs else ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
            sg = ec2.create_security_group(
                GroupName="fulkroOpen", Description="Dangerous ingress", VpcId=vpc_id,
            )
            ec2.authorize_security_group_ingress(
                GroupId=sg["GroupId"],
                IpPermissions=[{
                    "IpProtocol": "tcp", "FromPort": 22, "ToPort": 22,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                }],
            )

    @staticmethod
    def _introspect_mock_for_findings(services: Sequence[str]) -> list[dict]:
        """Recorre el mock AWS y genera ASFF sinteticos realistas."""
        import boto3  # type: ignore

        region = "eu-central-1"
        now_iso = datetime.now(timezone.utc).isoformat()
        account_id = "123456789012"
        findings: list[dict] = []

        def _asff(check_id: str, title: str, severity: str, resource_arn: str,
                  resource_type: str, related_req: str) -> dict:
            return {
                "SchemaVersion": "2018-10-08",
                "Id": f"prowler-{check_id}-{account_id}-{uuid.uuid4().hex[:8]}",
                "ProductArn": f"arn:aws:securityhub:{region}::product/prowler/prowler",
                "GeneratorId": f"prowler-{check_id}",
                "AwsAccountId": account_id,
                "Types": ["Software and Configuration Checks/Industry and Regulatory Standards/CIS AWS Foundations Benchmark"],
                "CreatedAt": now_iso,
                "UpdatedAt": now_iso,
                "Severity": {"Label": severity.upper()},
                "Title": title,
                "Description": title,
                "Resources": [{"Type": resource_type, "Id": resource_arn, "Region": region}],
                "Compliance": {"Status": "FAILED", "RelatedRequirements": [related_req]},
                "ProductFields": {"ProviderName": "prowler", "ProwlerCheckId": check_id},
            }

        if "iam" in services:
            iam = boto3.client("iam", region_name=region)
            for user in iam.list_users().get("Users", []):
                name = user["UserName"]
                try:
                    iam.get_login_profile(UserName=name)
                    has_console = True
                except iam.exceptions.NoSuchEntityException:
                    has_console = False
                if has_console:
                    mfa = iam.list_mfa_devices(UserName=name).get("MFADevices", [])
                    if not mfa:
                        findings.append(_asff(
                            "iam_user_mfa_enabled_console_access",
                            f"User {name} has console access without MFA",
                            "high",
                            user["Arn"],
                            "AwsIamUser",
                            "CIS-1.10",
                        ))
        if "s3" in services:
            s3 = boto3.client("s3", region_name=region)
            for bucket in s3.list_buckets().get("Buckets", []):
                name = bucket["Name"]
                arn = f"arn:aws:s3:::{name}"
                # Default encryption?
                try:
                    s3.get_bucket_encryption(Bucket=name)
                except s3.exceptions.ClientError:
                    findings.append(_asff(
                        "s3_bucket_default_encryption",
                        f"S3 bucket {name} has no default encryption",
                        "high",
                        arn, "AwsS3Bucket", "CIS-2.1.1",
                    ))
                # Public access block?
                try:
                    s3.get_public_access_block(Bucket=name)
                except s3.exceptions.ClientError:
                    findings.append(_asff(
                        "s3_bucket_public_access",
                        f"S3 bucket {name} has no public access block",
                        "critical",
                        arn, "AwsS3Bucket", "CIS-2.1.5",
                    ))
        if "ec2" in services:
            ec2 = boto3.client("ec2", region_name=region)
            for sg in ec2.describe_security_groups().get("SecurityGroups", []):
                sg_name = sg.get("GroupName", "")
                sg_id = sg.get("GroupId", "")
                if sg_name == "default":
                    continue
                arn = f"arn:aws:ec2:{region}:{account_id}:security-group/{sg_id}"
                for perm in sg.get("IpPermissions", []):
                    from_port = perm.get("FromPort")
                    for ip_range in perm.get("IpRanges", []):
                        cidr = ip_range.get("CidrIp", "")
                        if cidr == "0.0.0.0/0" and from_port == 22:
                            findings.append(_asff(
                                "ec2_securitygroup_allow_ingress_from_internet_to_ssh",
                                f"Security group {sg_name} allows SSH from 0.0.0.0/0",
                                "critical",
                                arn, "AwsEc2SecurityGroup", "CIS-5.2",
                            ))
                        elif cidr == "0.0.0.0/0" and from_port == 3389:
                            findings.append(_asff(
                                "ec2_securitygroup_allow_ingress_from_internet_to_rdp",
                                f"Security group {sg_name} allows RDP from 0.0.0.0/0",
                                "critical",
                                arn, "AwsEc2SecurityGroup", "CIS-5.3",
                            ))

        return findings

    # ══════════════════════════════════════════════════════════════
    # Modo real (subprocess prowler CLI)
    # ══════════════════════════════════════════════════════════════

    @classmethod
    async def _run_real(
        cls,
        targets: list[str],
        started: datetime,
        *,
        provider: str,
        timeout_seconds: int | None,
        services: Sequence[str],
    ) -> RunnerResult:
        if not is_binary_available(cls.BINARY):
            return cls.make_result(
                targets=targets, started_at=started, return_code=0,
                raw_output=b"prowler binary not available in PATH",
                findings=[],
                error="prowler_not_installed",
            )
        # Detectar credenciales AWS presentes
        if provider == "aws":
            has_env = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
            has_file = os.path.exists(os.path.expanduser("~/.aws/credentials"))
            if not (has_env or has_file):
                return cls.make_result(
                    targets=targets, started_at=started, return_code=0,
                    raw_output=b"aws credentials not available",
                    findings=[],
                    error="aws_credentials_missing",
                )
        cmd = [cls.BINARY, provider, "-M", "json-asff", "--quiet"]
        if services:
            cmd += ["--services", *services]
        rc, stdout, stderr, timed_out = await run_subprocess(
            cmd, timeout_seconds=(timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS),
        )
        findings: list[FindingCandidate] = []
        error: str | None = None
        try:
            findings = cls.parse_output(stdout)
        except Exception as exc:  # pragma: no cover
            error = f"parse error: {exc}"
        return cls.make_result(
            targets=targets, started_at=started, return_code=rc,
            raw_output=stdout, findings=findings,
            error=error or (stderr.decode(errors="replace") if rc != 0 else None),
            timed_out=timed_out,
        )

    # ══════════════════════════════════════════════════════════════
    # Parser ASFF
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def parse_output(cls, raw: bytes) -> list[FindingCandidate]:
        if not raw:
            return []
        text = raw.decode("utf-8", errors="replace").strip()
        if not text or text.startswith("prowler "):
            return []
        # Admite tres formas: JSON envuelto ({"Findings":[...]}), lista JSON o NDJSON.
        entries: list[dict[str, Any]] = []
        try:
            loaded = json.loads(text)
            if isinstance(loaded, dict) and "Findings" in loaded:
                entries = list(loaded.get("Findings", []))
            elif isinstance(loaded, list):
                entries = list(loaded)
        except json.JSONDecodeError:
            for line in text.splitlines():
                line = line.strip().rstrip(",")
                if not line.startswith("{"):
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        findings: list[FindingCandidate] = []
        for e in entries:
            if not isinstance(e, dict):
                continue
            sev_label = (e.get("Severity", {}) or {}).get("Label", "INFORMATIONAL")
            sev_alias = {
                "INFORMATIONAL": "info", "LOW": "low", "MEDIUM": "medium",
                "HIGH": "high", "CRITICAL": "critical",
            }.get(sev_label, "info")
            resources = e.get("Resources") or []
            host = resources[0].get("Id", "") if resources else ""
            product_fields = e.get("ProductFields", {}) or {}
            check_id = product_fields.get("ProwlerCheckId", "") or ""
            ens_measures = map_check_to_ens(check_id)
            compliance = e.get("Compliance", {}) or {}
            findings.append({
                "title": e.get("Title", "Prowler finding"),
                "description": e.get("Description", "")[:1000],
                "severity": normalize_severity(sev_alias),
                "cve_id": None,
                "cvss_score": None,
                "cvss_vector": None,
                "cwe_id": None,
                "affected_host": host or "cloud",
                "affected_port": None,
                "affected_service": "cloud",
                "affected_service_version": None,
                "affected_url": (e.get("SourceUrl") or None),
                "affected_os": None,
                "raw_output_excerpt": excerpt(json.dumps(e)),
                "tool": "prowler",
                "tool_metadata": {
                    "provider": product_fields.get("ProviderName"),
                    "check_id": check_id,
                    "compliance_status": compliance.get("Status"),
                    "related_requirements": compliance.get("RelatedRequirements") or [],
                    "ens_measures": ens_measures,
                    "ens_measures_labels": [describe_ens_measure(m) for m in ens_measures],
                },
            })
        return findings

    # ══════════════════════════════════════════════════════════════
    # Helper de reporting
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def summarize(cls, findings: list[FindingCandidate]) -> dict[str, Any]:
        """Resumen agregado: totales, por severity, medidas ENS unicas."""
        by_sev: dict[str, int] = {}
        ens_hits: dict[str, int] = {}
        for f in findings:
            sev = str(f.get("severity", "info"))
            by_sev[sev] = by_sev.get(sev, 0) + 1
            for m in (f.get("tool_metadata", {}) or {}).get("ens_measures", []):
                ens_hits[m] = ens_hits.get(m, 0) + 1
        return {
            "total": len(findings),
            "by_severity": by_sev,
            "ens_measures_hit": ens_hits,
            "ens_measures_unique": sorted(ens_hits.keys()),
        }
