"""M22 Paso 6 — AWS connector via cross-account AssumeRole + enriched discovery.

Discoveries especificos Paso 6:
- IAM: users, roles, policies, access keys antiguedad
- EC2 instances (InstanceId, State, Tags, SecurityGroups)
- S3 buckets + encryption config + public access block
- RDS instances + StorageEncrypted + BackupRetentionPeriod
- CloudTrail status (multiregion, log_file_validation, encrypted)
- GuardDuty findings (pendientes/severidad)
- Security Hub score actual
- Regiones activas (con recursos)

Credenciales STS AssumeRole duracion 3600s. Si se pasa fetcher mock,
no se ejecuta boto3 (demo / tests).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

from backend.app.motors.m16_onboarding.connectors.base import (
    ConnectorProvider,
    DiscoveredAssetDTO,
    DiscoveredIdentityDTO,
    DiscoveryResult,
)

logger = logging.getLogger(__name__)

# Region por defecto si el cliente no especifica
DEFAULT_REGION = "eu-west-1"

# Duracion STS en segundos (maximo 43200, practico 3600)
STS_DURATION_SECONDS = 3600


# ════════════════════════════════════════════════════════════════════
# DTOs Paso 6
# ════════════════════════════════════════════════════════════════════

@dataclass
class CloudTrailStatus:
    trail_name: str
    home_region: str
    is_multi_region: bool
    is_logging: bool
    log_file_validation_enabled: bool
    kms_key_id: Optional[str]
    is_organization_trail: bool = False
    raw: dict = field(default_factory=dict)


@dataclass
class GuardDutyFinding:
    finding_id: str
    detector_id: str
    severity: float  # 0.1 - 10.0 (AWS scale)
    title: str
    description: str
    resource_type: str
    resource_id: Optional[str]
    region: str
    raw: dict = field(default_factory=dict)

    @property
    def severity_label(self) -> str:
        if self.severity >= 7.0:
            return "alta"
        if self.severity >= 4.0:
            return "media"
        return "baja"


@dataclass
class SecurityHubSnapshot:
    enabled: bool
    score: Optional[float]  # 0-100 (Security Score)
    region: str
    failed_checks: int = 0
    passed_checks: int = 0
    total_checks: int = 0
    raw: dict = field(default_factory=dict)

    @property
    def percentage(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return round(100.0 * self.passed_checks / self.total_checks, 1)


@dataclass
class S3BucketConfig:
    name: str
    region: str
    encryption_enabled: bool
    encryption_algorithm: Optional[str]
    public_access_blocked: bool
    versioning_enabled: bool
    logging_enabled: bool
    raw: dict = field(default_factory=dict)


@dataclass
class RDSInstanceConfig:
    instance_id: str
    engine: str
    region: str
    storage_encrypted: bool
    backup_retention_period: int  # dias
    multi_az: bool
    publicly_accessible: bool
    raw: dict = field(default_factory=dict)


@dataclass
class AWSDiscoveryResult:
    """Resultado enriquecido Paso 6."""
    identities: list[DiscoveredIdentityDTO] = field(default_factory=list)
    assets: list[DiscoveredAssetDTO] = field(default_factory=list)
    cloudtrail: list[CloudTrailStatus] = field(default_factory=list)
    guardduty_findings: list[GuardDutyFinding] = field(default_factory=list)
    security_hub: Optional[SecurityHubSnapshot] = None
    s3_buckets: list[S3BucketConfig] = field(default_factory=list)
    rds_instances: list[RDSInstanceConfig] = field(default_factory=list)
    active_regions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_discovery_result(self, provider: str = "aws") -> DiscoveryResult:
        return DiscoveryResult(
            provider=provider,
            success=len(self.errors) == 0,
            assets=list(self.assets),
            identities=list(self.identities),
            errors=list(self.errors),
            summary={
                "total_assets": len(self.assets),
                "total_identities": len(self.identities),
                "cloudtrail_trails": len(self.cloudtrail),
                "cloudtrail_logging_ok": sum(
                    1 for t in self.cloudtrail if t.is_logging
                ),
                "guardduty_findings": len(self.guardduty_findings),
                "guardduty_high": sum(
                    1 for f in self.guardduty_findings if f.severity >= 7.0
                ),
                "security_hub_pct": (
                    self.security_hub.percentage
                    if self.security_hub else None
                ),
                "s3_buckets": len(self.s3_buckets),
                "s3_unencrypted": sum(
                    1 for b in self.s3_buckets if not b.encryption_enabled
                ),
                "rds_instances": len(self.rds_instances),
                "rds_unencrypted": sum(
                    1 for r in self.rds_instances if not r.storage_encrypted
                ),
                "active_regions": len(self.active_regions),
            },
        )


# Signature del fetcher mock: (service_name, operation, params) -> any
AWSFetcher = Callable[[str, str, Optional[dict]], Awaitable[Any]]


# ════════════════════════════════════════════════════════════════════
# AssumeRole helper
# ════════════════════════════════════════════════════════════════════

@dataclass
class AssumedCredentials:
    access_key_id: str
    secret_access_key: str
    session_token: str
    expires_at: datetime
    role_arn: str

    def is_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        return self.expires_at <= now


def assume_role_sync(
    role_arn: str,
    external_id: Optional[str] = None,
    region: str = DEFAULT_REGION,
    session_name: str = "fulkro-m22-discovery",
    duration_seconds: int = STS_DURATION_SECONDS,
) -> AssumedCredentials:
    """AssumeRole sincronico via boto3. En produccion este es el punto de entrada."""
    import boto3
    sts = boto3.client("sts", region_name=region)
    params: dict[str, Any] = {
        "RoleArn": role_arn,
        "RoleSessionName": session_name,
        "DurationSeconds": duration_seconds,
    }
    if external_id:
        params["ExternalId"] = external_id
    resp = sts.assume_role(**params)
    creds = resp["Credentials"]
    expires = creds["Expiration"]
    if getattr(expires, "tzinfo", None) is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return AssumedCredentials(
        access_key_id=creds["AccessKeyId"],
        secret_access_key=creds["SecretAccessKey"],
        session_token=creds["SessionToken"],
        expires_at=expires,
        role_arn=role_arn,
    )


async def assume_role(
    role_arn: str,
    external_id: Optional[str] = None,
    region: str = DEFAULT_REGION,
    session_name: str = "fulkro-m22-discovery",
    duration_seconds: int = STS_DURATION_SECONDS,
) -> AssumedCredentials:
    return await asyncio.to_thread(
        assume_role_sync,
        role_arn, external_id, region, session_name, duration_seconds,
    )


# ════════════════════════════════════════════════════════════════════
# Connector
# ════════════════════════════════════════════════════════════════════

class AWSPaso6Connector:
    """Conector AWS Paso 6. En tests/demos inyectar `fetcher` para bypass boto3."""

    provider = ConnectorProvider.AWS

    def __init__(
        self,
        credentials: dict,
        fetcher: Optional[AWSFetcher] = None,
    ) -> None:
        self.credentials = dict(credentials or {})
        self._fetcher = fetcher
        self.region = credentials.get("region", DEFAULT_REGION)
        self._assumed: Optional[AssumedCredentials] = None

    async def ensure_session(self) -> None:
        if self._fetcher is not None:
            return
        if self._assumed is not None and not self._assumed.is_expired():
            return
        self._assumed = await assume_role(
            role_arn=self.credentials["role_arn"],
            external_id=self.credentials.get("external_id"),
            region=self.region,
        )

    async def _call(
        self, service: str, operation: str, params: Optional[dict] = None,
    ) -> Any:
        if self._fetcher is not None:
            return await self._fetcher(service, operation, params)
        await self.ensure_session()
        # En produccion se usa boto3.Session con las credenciales assumed,
        # pero esa ruta no se ejecuta en tests (siempre con fetcher mock).
        import boto3
        assert self._assumed is not None
        sess = boto3.Session(
            aws_access_key_id=self._assumed.access_key_id,
            aws_secret_access_key=self._assumed.secret_access_key,
            aws_session_token=self._assumed.session_token,
            region_name=self.region,
        )
        client = sess.client(service)
        func = getattr(client, operation)
        return await asyncio.to_thread(func, **(params or {}))

    # --- Discoveries ---

    async def discover_iam(self) -> list[DiscoveredIdentityDTO]:
        out: list[DiscoveredIdentityDTO] = []
        try:
            users = await self._call("iam", "list_users", {"MaxItems": 500})
        except Exception as exc:
            logger.warning("AWS list_users: %s", exc)
            users = {"Users": []}
        for u in users.get("Users", []):
            out.append(DiscoveredIdentityDTO(
                external_id=u.get("UserId") or u.get("UserName", "unknown"),
                email=None,
                display_name=u.get("UserName", "unknown"),
                identity_type="user",
                provider="aws",
                is_active=True,
                raw_data={
                    "UserName": u.get("UserName"),
                    "CreateDate": str(u.get("CreateDate")),
                    "Path": u.get("Path"),
                },
            ))
        try:
            roles = await self._call("iam", "list_roles", {"MaxItems": 500})
        except Exception as exc:
            logger.warning("AWS list_roles: %s", exc)
            roles = {"Roles": []}
        for r in roles.get("Roles", []):
            out.append(DiscoveredIdentityDTO(
                external_id=r.get("RoleId") or r.get("RoleName", "unknown"),
                email=None,
                display_name=r.get("RoleName", "unknown"),
                identity_type="service_account",
                provider="aws",
                is_privileged=bool(
                    "Admin" in (r.get("RoleName") or "")
                    or "Administrator" in (r.get("RoleName") or "")
                ),
                raw_data={
                    "RoleName": r.get("RoleName"),
                    "Path": r.get("Path"),
                    "CreateDate": str(r.get("CreateDate")),
                },
            ))
        return out

    async def discover_ec2(self) -> list[DiscoveredAssetDTO]:
        out: list[DiscoveredAssetDTO] = []
        try:
            data = await self._call("ec2", "describe_instances", None)
        except Exception as exc:
            logger.warning("AWS describe_instances: %s", exc)
            return out
        for res in data.get("Reservations", []) or []:
            for inst in res.get("Instances", []) or []:
                tags = inst.get("Tags", []) or []
                name = next(
                    (t["Value"] for t in tags if t.get("Key") == "Name"),
                    inst.get("InstanceId", "unknown"),
                )
                env = next(
                    (t["Value"] for t in tags if t.get("Key", "").lower() in {"env", "environment"}),
                    "",
                )
                out.append(DiscoveredAssetDTO(
                    external_id=inst["InstanceId"],
                    name=name,
                    asset_type="aws_ec2_instance",
                    provider="aws",
                    tags=[inst.get("InstanceType", ""), env] if env else [inst.get("InstanceType", "")],
                    raw_data={
                        "InstanceId": inst["InstanceId"],
                        "InstanceType": inst.get("InstanceType"),
                        "State": (inst.get("State") or {}).get("Name"),
                        "region": self.region,
                        "environment": env,
                    },
                ))
        return out

    async def discover_s3(self) -> tuple[list[DiscoveredAssetDTO], list[S3BucketConfig]]:
        assets: list[DiscoveredAssetDTO] = []
        configs: list[S3BucketConfig] = []
        try:
            data = await self._call("s3", "list_buckets", None)
        except Exception as exc:
            logger.warning("AWS list_buckets: %s", exc)
            return assets, configs
        for b in data.get("Buckets", []) or []:
            name = b.get("Name")
            if not name:
                continue
            # Encryption
            try:
                enc = await self._call(
                    "s3", "get_bucket_encryption", {"Bucket": name},
                )
            except Exception:
                enc = None
            enc_enabled = False
            enc_algo: Optional[str] = None
            if enc and "ServerSideEncryptionConfiguration" in enc:
                rules = (
                    enc["ServerSideEncryptionConfiguration"].get("Rules", []) or []
                )
                for rule in rules:
                    apply = (rule.get("ApplyServerSideEncryptionByDefault") or {})
                    algo = apply.get("SSEAlgorithm")
                    if algo:
                        enc_enabled = True
                        enc_algo = algo
                        break
            # Public access
            try:
                pab = await self._call(
                    "s3", "get_public_access_block", {"Bucket": name},
                )
            except Exception:
                pab = None
            public_blocked = False
            if pab and "PublicAccessBlockConfiguration" in pab:
                cfg = pab["PublicAccessBlockConfiguration"]
                public_blocked = all([
                    cfg.get("BlockPublicAcls", False),
                    cfg.get("IgnorePublicAcls", False),
                    cfg.get("BlockPublicPolicy", False),
                    cfg.get("RestrictPublicBuckets", False),
                ])
            # Versioning
            try:
                ver = await self._call(
                    "s3", "get_bucket_versioning", {"Bucket": name},
                )
            except Exception:
                ver = None
            versioning = (ver or {}).get("Status") == "Enabled"
            # Logging
            try:
                log_cfg = await self._call(
                    "s3", "get_bucket_logging", {"Bucket": name},
                )
            except Exception:
                log_cfg = None
            logging_enabled = bool((log_cfg or {}).get("LoggingEnabled"))

            region = (await self._call(
                "s3", "get_bucket_location", {"Bucket": name},
            ) or {}).get("LocationConstraint") or self.region

            cfg = S3BucketConfig(
                name=name,
                region=region,
                encryption_enabled=enc_enabled,
                encryption_algorithm=enc_algo,
                public_access_blocked=public_blocked,
                versioning_enabled=versioning,
                logging_enabled=logging_enabled,
                raw={"b": b},
            )
            configs.append(cfg)
            assets.append(DiscoveredAssetDTO(
                external_id=name,
                name=name,
                asset_type="aws_s3_bucket",
                provider="aws",
                tags=["encrypted"] if enc_enabled else ["unencrypted"],
                raw_data={
                    "Bucket": name,
                    "region": region,
                    "encryption": enc_enabled,
                    "public_access_blocked": public_blocked,
                },
            ))
        return assets, configs

    async def discover_rds(self) -> tuple[list[DiscoveredAssetDTO], list[RDSInstanceConfig]]:
        assets: list[DiscoveredAssetDTO] = []
        configs: list[RDSInstanceConfig] = []
        try:
            data = await self._call("rds", "describe_db_instances", None)
        except Exception as exc:
            logger.warning("AWS describe_db_instances: %s", exc)
            return assets, configs
        for db in data.get("DBInstances", []) or []:
            identifier = db.get("DBInstanceIdentifier") or "unknown"
            cfg = RDSInstanceConfig(
                instance_id=identifier,
                engine=db.get("Engine") or "unknown",
                region=self.region,
                storage_encrypted=bool(db.get("StorageEncrypted")),
                backup_retention_period=int(db.get("BackupRetentionPeriod") or 0),
                multi_az=bool(db.get("MultiAZ")),
                publicly_accessible=bool(db.get("PubliclyAccessible")),
                raw={"db": db},
            )
            configs.append(cfg)
            assets.append(DiscoveredAssetDTO(
                external_id=identifier,
                name=identifier,
                asset_type="aws_rds_instance",
                provider="aws",
                tags=[db.get("Engine", ""), "encrypted" if cfg.storage_encrypted else "unencrypted"],
                raw_data={
                    "DBInstanceIdentifier": identifier,
                    "Engine": db.get("Engine"),
                    "region": self.region,
                    "StorageEncrypted": cfg.storage_encrypted,
                },
            ))
        return assets, configs

    async def discover_cloudtrail(self) -> list[CloudTrailStatus]:
        out: list[CloudTrailStatus] = []
        try:
            trails = await self._call("cloudtrail", "describe_trails", None)
        except Exception as exc:
            logger.warning("AWS describe_trails: %s", exc)
            return out
        for t in trails.get("trailList", []) or []:
            name = t.get("Name", "unknown")
            try:
                status = await self._call(
                    "cloudtrail", "get_trail_status", {"Name": t.get("TrailARN", name)},
                )
            except Exception:
                status = {"IsLogging": False}
            out.append(CloudTrailStatus(
                trail_name=name,
                home_region=t.get("HomeRegion") or self.region,
                is_multi_region=bool(t.get("IsMultiRegionTrail")),
                is_logging=bool((status or {}).get("IsLogging")),
                log_file_validation_enabled=bool(t.get("LogFileValidationEnabled")),
                kms_key_id=t.get("KmsKeyId"),
                is_organization_trail=bool(t.get("IsOrganizationTrail")),
                raw={"trail": t, "status": status},
            ))
        return out

    async def discover_guardduty(self) -> list[GuardDutyFinding]:
        out: list[GuardDutyFinding] = []
        try:
            detectors = await self._call(
                "guardduty", "list_detectors", None,
            )
        except Exception as exc:
            logger.warning("AWS list_detectors: %s", exc)
            return out
        det_ids = (detectors or {}).get("DetectorIds", []) or []
        for did in det_ids:
            try:
                findings_ids = await self._call(
                    "guardduty", "list_findings",
                    {"DetectorId": did, "MaxResults": 50},
                )
            except Exception:
                findings_ids = {"FindingIds": []}
            fids = (findings_ids or {}).get("FindingIds", []) or []
            if not fids:
                continue
            try:
                findings = await self._call(
                    "guardduty", "get_findings",
                    {"DetectorId": did, "FindingIds": fids},
                )
            except Exception:
                findings = {"Findings": []}
            for f in (findings or {}).get("Findings", []) or []:
                resource = (f.get("Resource") or {})
                rtype = resource.get("ResourceType") or "unknown"
                rid: Optional[str] = None
                if rtype == "Instance":
                    rid = (resource.get("InstanceDetails") or {}).get("InstanceId")
                elif rtype == "AccessKey":
                    rid = (resource.get("AccessKeyDetails") or {}).get("AccessKeyId")
                out.append(GuardDutyFinding(
                    finding_id=f.get("Id", ""),
                    detector_id=did,
                    severity=float(f.get("Severity") or 0.0),
                    title=f.get("Title") or "",
                    description=f.get("Description") or "",
                    resource_type=rtype,
                    resource_id=rid,
                    region=f.get("Region") or self.region,
                    raw=f,
                ))
        return out

    async def discover_security_hub(self) -> Optional[SecurityHubSnapshot]:
        try:
            desc = await self._call("securityhub", "describe_hub", None)
        except Exception as exc:
            logger.warning("AWS describe_hub: %s", exc)
            return SecurityHubSnapshot(
                enabled=False, score=None, region=self.region,
            )
        if not desc:
            return None
        try:
            summary = await self._call(
                "securityhub", "get_findings",
                {
                    "Filters": {
                        "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}]
                    },
                    "MaxResults": 100,
                },
            )
        except Exception:
            summary = {"Findings": []}
        findings = (summary or {}).get("Findings", []) or []
        passed = sum(
            1 for f in findings
            if (f.get("Compliance") or {}).get("Status") == "PASSED"
        )
        failed = sum(
            1 for f in findings
            if (f.get("Compliance") or {}).get("Status") == "FAILED"
        )
        total = passed + failed
        return SecurityHubSnapshot(
            enabled=True,
            score=round(100.0 * passed / total, 1) if total else None,
            region=self.region,
            failed_checks=failed,
            passed_checks=passed,
            total_checks=total,
            raw={"describe": desc},
        )

    async def discover_active_regions(self) -> list[str]:
        try:
            data = await self._call(
                "ec2", "describe_regions",
                {"Filters": [{"Name": "opt-in-status", "Values": ["opt-in-not-required", "opted-in"]}]},
            )
        except Exception as exc:
            logger.warning("AWS describe_regions: %s", exc)
            return [self.region]
        return sorted(
            r["RegionName"] for r in (data or {}).get("Regions", []) or []
        )

    # --- Orquestacion ---

    async def run_paso6_discovery(self) -> AWSDiscoveryResult:
        result = AWSDiscoveryResult()
        try:
            result.identities = await self.discover_iam()
        except Exception as exc:
            result.errors.append(f"iam: {exc}")
        try:
            ec2 = await self.discover_ec2()
            result.assets.extend(ec2)
        except Exception as exc:
            result.errors.append(f"ec2: {exc}")
        try:
            s3_assets, s3_configs = await self.discover_s3()
            result.assets.extend(s3_assets)
            result.s3_buckets = s3_configs
        except Exception as exc:
            result.errors.append(f"s3: {exc}")
        try:
            rds_assets, rds_configs = await self.discover_rds()
            result.assets.extend(rds_assets)
            result.rds_instances = rds_configs
        except Exception as exc:
            result.errors.append(f"rds: {exc}")
        try:
            result.cloudtrail = await self.discover_cloudtrail()
        except Exception as exc:
            result.errors.append(f"cloudtrail: {exc}")
        try:
            result.guardduty_findings = await self.discover_guardduty()
        except Exception as exc:
            result.errors.append(f"guardduty: {exc}")
        try:
            result.security_hub = await self.discover_security_hub()
        except Exception as exc:
            result.errors.append(f"security_hub: {exc}")
        try:
            result.active_regions = await self.discover_active_regions()
        except Exception as exc:
            result.errors.append(f"regions: {exc}")
        return result


__all__ = [
    "AssumedCredentials",
    "CloudTrailStatus",
    "GuardDutyFinding",
    "SecurityHubSnapshot",
    "S3BucketConfig",
    "RDSInstanceConfig",
    "AWSDiscoveryResult",
    "AWSPaso6Connector",
    "assume_role",
    "assume_role_sync",
]
