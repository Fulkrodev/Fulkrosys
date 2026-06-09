"""M22 Paso 6 — Mocks de DataForma para demo sin credenciales reales.

Entregables Paso 6.8: 45 activos, MFA 68%, 3 S3 sin cifrar, 15 vulns,
8 flujos (3 criticos), madurez tecnica L1.

Uso:
    from backend.app.motors.m22_discovery.paso6_demo_mocks import (
        build_m365_connector_dataforma,
        build_aws_connector_dataforma,
        dataforma_security_hub_findings,
    )

    m365 = build_m365_connector_dataforma()
    aws = build_aws_connector_dataforma()
    sh = dataforma_security_hub_findings()

    await paso6_orchestrator.run_full_paso6(
        db, project_id,
        m365_connector=m365, aws_connector=aws,
        security_hub_findings=sh,
    )
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from backend.app.motors.m22_discovery.paso6_aws_connector import (
    AWSPaso6Connector,
)
from backend.app.motors.m22_discovery.paso6_m365_connector import (
    M365Paso6Connector,
)


# ════════════════════════════════════════════════════════════════════
# DataForma M365 — 20 usuarios + 4 grupos + 8 dispositivos
# ════════════════════════════════════════════════════════════════════

def _now() -> datetime:
    return datetime.now(timezone.utc)


def dataforma_users() -> list[dict]:
    """20 usuarios: 6 con MFA, 14 sin. 3 privilegiados (2 con MFA)."""
    base_date = (_now() - timedelta(days=400)).isoformat()
    users = []
    nombres = [
        ("marcos.ruiz", "Marcos Ruiz", "CEO", "direccion"),
        ("elena.sanchez", "Elena Sanchez", "CTO", "sistemas"),
        ("raul.jimenez", "Raul Jimenez", "CISO", "seguridad"),
        ("ana.moreno", "Ana Moreno", "DPO", "legal"),
        ("pedro.torres", "Pedro Torres", "Jefe Sistemas", "sistemas"),
        ("laura.garcia", "Laura Garcia", "Admin RRHH", "rrhh"),
        ("carlos.marin", "Carlos Marin", "Admin Facturacion", "administracion"),
        ("sofia.vega", "Sofia Vega", "Medico Jefe", "clinico"),
        ("javier.lopez", "Javier Lopez", "Medico", "clinico"),
        ("rocio.diaz", "Rocio Diaz", "Medico", "clinico"),
        ("oscar.pena", "Oscar Pena", "Enfermero", "clinico"),
        ("marta.ruiz", "Marta Ruiz", "Enfermera", "clinico"),
        ("pablo.molina", "Pablo Molina", "Recepcion", "recepcion"),
        ("lucia.castro", "Lucia Castro", "Recepcion", "recepcion"),
        ("alejandro.serrano", "Alejandro Serrano", "Administrativo", "administracion"),
        ("maria.alvarez", "Maria Alvarez", "Administrativa", "administracion"),
        ("david.ruiz", "David Ruiz", "Facturacion", "administracion"),
        ("carmen.nunez", "Carmen Nunez", "RRHH", "rrhh"),
        ("sergio.cruz", "Sergio Cruz", "Sistemas Junior", "sistemas"),
        ("isabel.ramos", "Isabel Ramos", "Desarrollo", "sistemas"),
    ]
    for upn, display, cargo, dept in nombres:
        users.append({
            "id": str(uuid.uuid4()),
            "displayName": display,
            "userPrincipalName": f"{upn}@dataforma.es",
            "mail": f"{upn}@dataforma.es",
            "accountEnabled": True,
            "userType": "Member",
            "createdDateTime": base_date,
            "department": dept,
            "jobTitle": cargo,
            "last_sign_in": (_now() - timedelta(days=5)).isoformat(),
        })
    return users


def dataforma_groups() -> list[dict]:
    return [
        {
            "id": str(uuid.uuid4()),
            "displayName": "All Staff",
            "groupTypes": [],
            "securityEnabled": True,
            "mailEnabled": True,
        },
        {
            "id": str(uuid.uuid4()),
            "displayName": "Administradores Globales",
            "groupTypes": [],
            "securityEnabled": True,
            "mailEnabled": False,
        },
        {
            "id": str(uuid.uuid4()),
            "displayName": "Medicos",
            "groupTypes": [],
            "securityEnabled": True,
            "mailEnabled": True,
        },
        {
            "id": str(uuid.uuid4()),
            "displayName": "RRHH",
            "groupTypes": [],
            "securityEnabled": True,
            "mailEnabled": True,
        },
    ]


def dataforma_devices() -> list[dict]:
    return [
        {
            "id": str(uuid.uuid4()),
            "deviceName": f"DF-LAPTOP-{i:02d}",
            "operatingSystem": "Windows",
            "osVersion": "11.0.22631",
            "model": "Latitude 7430",
            "manufacturer": "Dell",
            "complianceState": "compliant" if i % 3 != 0 else "noncompliant",
            "managementAgent": "mdm",
        }
        for i in range(1, 9)
    ]


def dataforma_ca_policies() -> list[dict]:
    return [
        {
            "id": "ca-001",
            "displayName": "Requerir MFA a administradores globales",
            "state": "enabled",
            "conditions": {
                "users": {"includeRoles": ["Global Admin"]},
            },
            "grantControls": {"builtInControls": ["mfa"]},
            "sessionControls": {},
        },
        {
            "id": "ca-002",
            "displayName": "Bloquear accesos desde paises no listados",
            "state": "enabled",
            "conditions": {"users": {"includeUsers": ["All"]}},
            "grantControls": {"builtInControls": ["block"]},
            "sessionControls": {},
        },
        {
            "id": "ca-003",
            "displayName": "MFA general (en planificacion)",
            "state": "disabled",
            "conditions": {"users": {"includeUsers": ["All"]}},
            "grantControls": {"builtInControls": ["mfa"]},
            "sessionControls": {},
        },
    ]


def dataforma_secure_score() -> dict:
    return {
        "value": [
            {
                "currentScore": 324,
                "maxScore": 720,
                "createdDateTime": _now().isoformat(),
                "controlScores": [
                    {"controlName": c, "score": s}
                    for c, s in [
                        ("AdminMFAV2", 5), ("UserMFA", 0),
                        ("DefenderSignUp", 10), ("CAPolicyMFAAdmins", 5),
                        ("ConditionalAccessPolicies", 5),
                        ("MalwareProtection", 0), ("PasswordPolicy", 5),
                        ("ExternalSharingBlocked", 0), ("MailboxAudit", 5),
                    ]
                ],
            },
        ],
    }


def dataforma_auth_methods(user_ids: list[str]) -> dict[str, dict]:
    """MFA habilitado para 6 de 20 (30% — antes de normalizar)."""
    mfa_count = 6
    methods: dict[str, dict] = {}
    for i, uid in enumerate(user_ids):
        if i < mfa_count:
            methods[uid] = {
                "value": [
                    {"@odata.type": "#microsoft.graph.microsoftAuthenticatorAuthenticationMethod"}
                ],
            }
        else:
            methods[uid] = {"value": []}
    return methods


def dataforma_directory_roles() -> list[dict]:
    """3 privilegiados: CTO + CISO + Admin Sistemas Junior."""
    return [
        {"id": "role-global-admin"},
        {"id": "role-security-admin"},
    ]


def dataforma_role_members(role_id: str, users: list[dict]) -> list[dict]:
    priv_upns = {"elena.sanchez", "raul.jimenez", "sergio.cruz"}
    matching = [
        u for u in users if u["userPrincipalName"].split("@")[0] in priv_upns
    ]
    return matching


def build_m365_fetcher(
    users: Optional[list[dict]] = None,
    groups: Optional[list[dict]] = None,
    devices: Optional[list[dict]] = None,
    ca_policies: Optional[list[dict]] = None,
    secure_score: Optional[dict] = None,
):
    """Construye un fetcher async que simula Graph API para DataForma."""
    users = users or dataforma_users()
    groups = groups or dataforma_groups()
    devices = devices or dataforma_devices()
    ca_policies = ca_policies or {"value": dataforma_ca_policies()}
    if isinstance(ca_policies, list):
        ca_policies = {"value": ca_policies}
    secure_score = secure_score or dataforma_secure_score()
    user_ids = [u["id"] for u in users]
    auth_methods = dataforma_auth_methods(user_ids)
    roles_list = {"value": dataforma_directory_roles()}
    role_members_by_id = {
        "role-global-admin": {
            "value": dataforma_role_members("role-global-admin", users),
        },
        "role-security-admin": {
            "value": dataforma_role_members("role-security-admin", users),
        },
    }

    async def fetcher(path: str, params: Optional[dict] = None) -> dict:
        if path == "/users":
            return {"value": users}
        if path == "/groups":
            return {"value": groups}
        if path == "/deviceManagement/managedDevices":
            return {"value": devices}
        if path == "/identity/conditionalAccess/policies":
            return ca_policies
        if path == "/security/secureScores":
            return secure_score
        if path == "/directoryRoles":
            return roles_list
        if path.startswith("/directoryRoles/") and path.endswith("/members"):
            rid = path.split("/")[-2]
            return role_members_by_id.get(rid, {"value": []})
        if path.startswith("/beta/users/") and path.endswith("/authentication/methods"):
            uid = path.split("/")[-3]
            return auth_methods.get(uid, {"value": []})
        return {"value": []}

    return fetcher


def build_m365_connector_dataforma() -> M365Paso6Connector:
    fetcher = build_m365_fetcher()
    return M365Paso6Connector(
        credentials={
            "tenant_id": "dataforma-tenant",
            "client_id": "mock-client",
            "client_secret": "mock-secret",
        },
        fetcher=fetcher,
    )


# ════════════════════════════════════════════════════════════════════
# DataForma AWS — IAM + EC2 + S3 + RDS + CloudTrail + GuardDuty
# ════════════════════════════════════════════════════════════════════

def dataforma_aws_iam_users() -> dict:
    return {"Users": [
        {"UserId": "AIDAUSER01", "UserName": "ci-deploy", "Path": "/"},
        {"UserId": "AIDAUSER02", "UserName": "backup-runner", "Path": "/"},
    ]}


def dataforma_aws_iam_roles() -> dict:
    return {"Roles": [
        {"RoleId": "AROAROLE01", "RoleName": "DataFormaAppServerRole", "Path": "/"},
        {"RoleId": "AROAROLE02", "RoleName": "DataFormaReadOnlyAuditor", "Path": "/"},
        {"RoleId": "AROAROLE03", "RoleName": "DataFormaAdminRole", "Path": "/"},
    ]}


def dataforma_aws_ec2() -> dict:
    return {
        "Reservations": [{
            "Instances": [
                {
                    "InstanceId": f"i-{i:013x}",
                    "InstanceType": "t3.medium",
                    "State": {"Name": "running"},
                    "Tags": [
                        {"Key": "Name", "Value": name},
                        {"Key": "Environment", "Value": env},
                    ],
                }
                for i, (name, env) in enumerate([
                    ("df-app-prod-01", "prod"),
                    ("df-app-prod-02", "prod"),
                    ("df-db-prod-01", "prod"),
                    ("df-web-stg-01", "stg"),
                    ("df-bastion-01", "prod"),
                ], start=1)
            ],
        }],
    }


def dataforma_aws_s3_buckets() -> list[dict]:
    return [
        {"Name": "dataforma-backups", "CreationDate": _now()},
        {"Name": "dataforma-historia-clinica", "CreationDate": _now()},
        {"Name": "dataforma-informes", "CreationDate": _now()},
        {"Name": "dataforma-public-marketing", "CreationDate": _now()},
        {"Name": "dataforma-logs", "CreationDate": _now()},
    ]


def dataforma_aws_rds() -> dict:
    return {"DBInstances": [
        {
            "DBInstanceIdentifier": "df-hce-prod",
            "Engine": "postgres",
            "StorageEncrypted": True,
            "BackupRetentionPeriod": 14,
            "MultiAZ": True,
            "PubliclyAccessible": False,
        },
        {
            "DBInstanceIdentifier": "df-facturacion-prod",
            "Engine": "mysql",
            "StorageEncrypted": False,
            "BackupRetentionPeriod": 7,
            "MultiAZ": False,
            "PubliclyAccessible": False,
        },
    ]}


def dataforma_aws_cloudtrail() -> dict:
    return {"trailList": [
        {
            "Name": "DataFormaTrail",
            "TrailARN": "arn:aws:cloudtrail:eu-west-1:123:trail/DataFormaTrail",
            "HomeRegion": "eu-west-1",
            "IsMultiRegionTrail": True,
            "LogFileValidationEnabled": True,
            "KmsKeyId": "arn:aws:kms:eu-west-1:123:key/abcdef",
            "IsOrganizationTrail": False,
        },
    ]}


def dataforma_aws_guardduty() -> list[dict]:
    return [
        {
            "Id": "gd-finding-01",
            "Severity": 7.5,
            "Title": "UnauthorizedAccess:EC2/SSHBruteForce",
            "Description": "Ataques SSH fuerza bruta detectados.",
            "Region": "eu-west-1",
            "Resource": {
                "ResourceType": "Instance",
                "InstanceDetails": {"InstanceId": "i-0000000000001"},
            },
        },
        {
            "Id": "gd-finding-02",
            "Severity": 5.0,
            "Title": "Recon:EC2/PortProbeUnprotectedPort",
            "Description": "Sondeo de puertos en instancia sin firewall.",
            "Region": "eu-west-1",
            "Resource": {
                "ResourceType": "Instance",
                "InstanceDetails": {"InstanceId": "i-0000000000002"},
            },
        },
    ]


def dataforma_aws_security_hub_findings() -> list[dict]:
    """15 findings para poblar vulnerability_inventory."""
    findings = []
    templates = [
        ("S3.4", "HIGH", "S3 buckets should have server-side encryption enabled", 85.0),
        ("RDS.3", "HIGH", "RDS instances should have encryption at-rest", 80.0),
        ("IAM.4", "HIGH", "IAM root user access key should not exist", 90.0),
        ("IAM.1", "MEDIUM", "IAM policies should not allow full administrative privileges", 55.0),
        ("EC2.2", "MEDIUM", "Security group should not allow unrestricted inbound SSH", 60.0),
        ("CloudTrail.2", "MEDIUM", "CloudTrail log file validation should be enabled", 50.0),
        ("GuardDuty.1", "LOW", "GuardDuty should be enabled in all regions", 30.0),
        ("EC2.18", "MEDIUM", "Security groups should only allow unrestricted access to approved ports", 55.0),
        ("RDS.2", "HIGH", "RDS DB instances should prohibit public access", 70.0),
        ("S3.5", "MEDIUM", "S3 buckets should require TLS", 45.0),
        ("CloudWatch.1", "LOW", "Log metric filter and alarm exist", 25.0),
        ("EC2.8", "MEDIUM", "EC2 instances should use IMDSv2", 50.0),
        ("S3.8", "MEDIUM", "S3 Block Public Access should be enabled", 55.0),
        ("IAM.8", "MEDIUM", "Unused IAM user credentials should be removed", 40.0),
        ("RDS.4", "HIGH", "RDS snapshots should not be publicly accessible", 85.0),
    ]
    for i, (control, sev, title, score) in enumerate(templates):
        findings.append({
            "Id": f"arn:aws:securityhub:eu-west-1:123:finding/{i:04d}",
            "ProductArn": "arn:aws:securityhub:eu-west-1::product/aws/securityhub",
            "Title": title,
            "Description": f"Security Hub control {control} detectado fallando.",
            "Severity": {"Label": sev, "Normalized": score},
            "Types": [
                f"Software and Configuration Checks/AWS Security Best Practices/{control}",
            ],
            "Resources": [{
                "Id": f"arn:aws:resource/{i}",
                "ResourceRole": "Target",
                "Type": "AwsS3Bucket" if control.startswith("S3")
                         else "AwsRdsDbInstance" if control.startswith("RDS")
                         else "AwsEc2Instance",
            }],
            "Compliance": {"Status": "FAILED"},
            "Remediation": {"Recommendation": {
                "Text": f"Ver documentacion Security Hub control {control}.",
            }},
        })
    return findings


def dataforma_aws_security_hub_summary() -> dict:
    findings = dataforma_aws_security_hub_findings()
    return {
        "describe": {"SubscribedAt": _now().isoformat()},
        "findings_sample": findings[:5],
    }


def dataforma_aws_regions() -> dict:
    return {"Regions": [
        {"RegionName": "eu-west-1"},
        {"RegionName": "eu-south-2"},
    ]}


def build_aws_fetcher():
    """Fetcher async (service, operation, params) -> dict simulando boto3."""

    s3_buckets = dataforma_aws_s3_buckets()
    bucket_names = [b["Name"] for b in s3_buckets]

    def s3_encryption(bucket: str) -> dict:
        unencrypted = {"dataforma-public-marketing", "dataforma-informes", "dataforma-logs"}
        if bucket in unencrypted:
            return {}
        return {
            "ServerSideEncryptionConfiguration": {
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
                }],
            },
        }

    def s3_public_access_block(bucket: str) -> dict:
        open_buckets = {"dataforma-public-marketing"}
        if bucket in open_buckets:
            return {"PublicAccessBlockConfiguration": {
                "BlockPublicAcls": False, "IgnorePublicAcls": False,
                "BlockPublicPolicy": False, "RestrictPublicBuckets": False,
            }}
        return {"PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True, "IgnorePublicAcls": True,
            "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
        }}

    async def fetcher(service: str, operation: str, params: Optional[dict] = None) -> Any:
        params = params or {}
        if service == "iam" and operation == "list_users":
            return dataforma_aws_iam_users()
        if service == "iam" and operation == "list_roles":
            return dataforma_aws_iam_roles()
        if service == "ec2" and operation == "describe_instances":
            return dataforma_aws_ec2()
        if service == "ec2" and operation == "describe_regions":
            return dataforma_aws_regions()
        if service == "s3" and operation == "list_buckets":
            return {"Buckets": s3_buckets}
        if service == "s3" and operation == "get_bucket_encryption":
            return s3_encryption(params.get("Bucket", ""))
        if service == "s3" and operation == "get_public_access_block":
            return s3_public_access_block(params.get("Bucket", ""))
        if service == "s3" and operation == "get_bucket_versioning":
            return {"Status": "Enabled"}
        if service == "s3" and operation == "get_bucket_logging":
            return {"LoggingEnabled": {"TargetBucket": "dataforma-logs"}}
        if service == "s3" and operation == "get_bucket_location":
            return {"LocationConstraint": "eu-west-1"}
        if service == "rds" and operation == "describe_db_instances":
            return dataforma_aws_rds()
        if service == "cloudtrail" and operation == "describe_trails":
            return dataforma_aws_cloudtrail()
        if service == "cloudtrail" and operation == "get_trail_status":
            return {"IsLogging": True}
        if service == "guardduty" and operation == "list_detectors":
            return {"DetectorIds": ["det-dataforma-01"]}
        if service == "guardduty" and operation == "list_findings":
            return {"FindingIds": ["gd-finding-01", "gd-finding-02"]}
        if service == "guardduty" and operation == "get_findings":
            return {"Findings": dataforma_aws_guardduty()}
        if service == "securityhub" and operation == "describe_hub":
            return {"SubscribedAt": _now().isoformat()}
        if service == "securityhub" and operation == "get_findings":
            # Emitimos algunos PASSED + FAILED para dar score
            findings = [
                {"Compliance": {"Status": "PASSED"}} for _ in range(15)
            ] + [
                {"Compliance": {"Status": "FAILED"}} for _ in range(10)
            ]
            return {"Findings": findings}
        return {}

    return fetcher


def build_aws_connector_dataforma() -> AWSPaso6Connector:
    fetcher = build_aws_fetcher()
    return AWSPaso6Connector(
        credentials={
            "role_arn": "arn:aws:iam::123:role/DataFormaReadOnly",
            "region": "eu-west-1",
        },
        fetcher=fetcher,
    )


def dataforma_security_hub_findings() -> list[dict]:
    """Alias publico para el orquestador."""
    return dataforma_aws_security_hub_findings()


def dataforma_password_policy() -> dict:
    return {
        "min_length": 8,
        "complexity": True,
        "rotation_days": 0,
        "history": 3,
        "lockout_after": 10,
        "source": "m365",
    }


def dataforma_m365_defender_alerts() -> list[dict]:
    return [
        {
            "id": "alert-001",
            "title": "Sospecha de phishing credential theft",
            "description": "Usuario recibio email malicioso + intento login.",
            "severity": "High",
            "category": "InitialAccess",
            "status": "New",
            "mitreTechniques": ["T1566"],
            "evidence": [{
                "@odata.type": "#microsoft.graph.security.userEvidence",
                "userAccount": {"userPrincipalName": "laura.garcia@dataforma.es"},
            }],
        },
    ]


# ════════════════════════════════════════════════════════════════════
# Cifras esperadas de la demo (para validacion en tests)
# ════════════════════════════════════════════════════════════════════

EXPECTED_DATAFORMA_METRICS = {
    "m365_users": 20,
    "m365_groups": 4,
    "m365_devices": 8,
    "aws_iam_users": 2,
    "aws_iam_roles": 3,
    "aws_ec2": 5,
    "aws_s3": 5,
    "aws_s3_unencrypted_names": [
        "dataforma-public-marketing", "dataforma-informes", "dataforma-logs",
    ],
    "aws_rds": 2,
    "aws_rds_unencrypted": 1,
    "ca_policies_enabled": 2,
    "privileged_users": 3,
    "mfa_covered_users": 6,
    "total_assets_estimated": 20,  # users no son assets; se cuentan devices+ec2+s3+rds
    "security_hub_findings": 15,
}


__all__ = [
    "build_m365_connector_dataforma",
    "build_aws_connector_dataforma",
    "build_m365_fetcher",
    "build_aws_fetcher",
    "dataforma_security_hub_findings",
    "dataforma_password_policy",
    "dataforma_m365_defender_alerts",
    "EXPECTED_DATAFORMA_METRICS",
]
