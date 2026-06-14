"""M8 v5.1 — Mapper ScoutSuite cloud checks -> medidas ENS Anexo II.

ScoutSuite cubre AWS + Azure + GCP + Alibaba + Oracle. Sesion 10 Paso 4.2
mapea AWS (complementario a Prowler) + Azure + GCP (cobertura unica que
Prowler no da).

Diseno de complementariedad AWS:
- Prowler ya cubre IAM MFA basico, S3 public/encryption, EC2 SG (4.1).
- ScoutSuite añade: root account usage, multiple access keys,
  cloudtrail global/log validation, VPC/default SG analysis.
- Sin solape (comprobar coverage_stats via test).

Azure/GCP: cobertura nativa ScoutSuite, Prowler no soporta con la misma
profundidad.
"""
from __future__ import annotations


SCOUTSUITE_TO_ENS: dict[str, list[str]] = {
    # ── AWS (complementario a Prowler) ────────────────────────────
    "iam-root-account-used-recently": ["op.acc.4", "op.exp.8"],
    "iam-user-with-password-and-no-mfa": ["op.acc.5"],
    "iam-root-access-keys-exist": ["op.acc.4"],
    "iam-user-with-multiple-access-keys": ["op.acc.2"],
    "cloudtrail-no-global-trail": ["op.exp.8"],
    "cloudtrail-no-log-file-validation": ["op.exp.8"],
    "vpc-default-in-use": ["op.exp.2"],
    "ec2-default-security-group-open": ["mp.com.1"],
    "rds-instance-no-encryption": ["mp.si.2"],
    "kms-key-rotation-disabled": ["op.exp.10", "mp.si.2"],
    # ── Azure (cobertura unica) ───────────────────────────────────
    # almacenamiento público: clasificación + control de acceso (mp.s.5 NO existe).
    "azure-storage-account-blob-public": ["mp.info.2", "op.acc.4"],
    "azure-storage-account-no-soft-delete": ["mp.info.6"],
    "azure-sqldatabase-no-encryption": ["mp.si.2"],
    "azure-sqlserver-no-ad-admin": ["op.acc.4", "op.acc.5"],
    "azure-keyvault-no-rbac": ["op.acc.4"],
    "azure-keyvault-no-purge-protection": ["op.exp.10"],
    "azure-network-security-group-open": ["mp.com.1"],
    "azure-subscription-no-mfa": ["op.acc.5"],
    "azure-monitor-no-diagnostic-settings": ["op.exp.8"],
    "azure-appservice-no-https-only": ["mp.com.2"],
    # ── GCP (cobertura unica) ─────────────────────────────────────
    "gcp-compute-firewall-rule-allow-any": ["mp.com.1"],
    "gcp-compute-instance-public-ip": ["mp.com.1"],
    "gcp-storage-bucket-public": ["mp.info.2", "op.acc.4"],
    "gcp-iam-service-account-with-user-keys": ["op.acc.4"],
    "gcp-iam-primitive-role-assigned": ["op.acc.4"],
    "gcp-logging-audit-configs-disabled": ["op.exp.8"],
    "gcp-cloudsql-no-ssl": ["mp.com.2", "mp.si.2"],
    "gcp-bigquery-dataset-public": ["mp.info.2", "op.acc.4"],
    "gcp-kms-key-rotation-disabled": ["op.exp.10", "mp.si.2"],
}


ENS_MEASURE_LABEL: dict[str, str] = {
    "op.acc.2": "Requisitos de acceso (passwords/MFA)",
    "op.acc.4": "Derechos de acceso (minimo privilegio)",
    "op.acc.5": "Mecanismo de autenticacion",
    "op.exp.2": "Configuracion de seguridad",
    "op.exp.8": "Registro de la actividad",
    "op.exp.10": "Proteccion de claves criptograficas",
    "mp.com.1": "Perimetro seguro",
    "mp.com.2": "Proteccion de la confidencialidad",
    "mp.info.2": "Calificacion de la informacion",
    "mp.info.6": "Copias de seguridad",
    "mp.si.2": "Criptografia",
}


# Reexportamos para que orchestrator/consumidores sepan la cobertura.
PROVIDERS_SUPPORTED: frozenset[str] = frozenset({"aws", "azure", "gcp"})


def map_check_to_ens(check_id: str) -> list[str]:
    """Devuelve la lista de medidas ENS para un finding_id ScoutSuite.

    Si el check_id no esta mapeado devuelve lista vacia (revisable manual).
    """
    if not check_id:
        return []
    return SCOUTSUITE_TO_ENS.get(check_id, [])


def describe_ens_measure(measure: str) -> str:
    return ENS_MEASURE_LABEL.get(measure, measure)


def detect_provider_from_check(check_id: str) -> str | None:
    """Infiere el provider por el prefijo del finding_id.

    Returns 'aws' | 'azure' | 'gcp' | None.
    """
    if not check_id:
        return None
    lower = check_id.lower()
    if lower.startswith("azure-"):
        return "azure"
    if lower.startswith("gcp-"):
        return "gcp"
    # ScoutSuite AWS finding_ids no llevan prefijo 'aws-' explicito
    # (iam-*, ec2-*, s3-*, cloudtrail-*, rds-*, kms-*, vpc-*...)
    aws_prefixes = ("iam-", "ec2-", "s3-", "cloudtrail-", "rds-", "kms-",
                    "vpc-", "elb-", "efs-", "sns-", "sqs-", "lambda-",
                    "dynamodb-", "cloudformation-", "awslambda-")
    if lower.startswith(aws_prefixes):
        return "aws"
    return None


def coverage_stats() -> dict[str, int]:
    """Estadisticas de cobertura por provider."""
    per_provider: dict[str, int] = {"aws": 0, "azure": 0, "gcp": 0, "unknown": 0}
    unique_measures: set[str] = set()
    for check_id, measures in SCOUTSUITE_TO_ENS.items():
        provider = detect_provider_from_check(check_id) or "unknown"
        per_provider[provider] = per_provider.get(provider, 0) + 1
        unique_measures.update(measures)
    return {
        "checks_total": len(SCOUTSUITE_TO_ENS),
        "checks_aws": per_provider["aws"],
        "checks_azure": per_provider["azure"],
        "checks_gcp": per_provider["gcp"],
        "unique_measures": len(unique_measures),
        "labels_defined": len(ENS_MEASURE_LABEL),
    }


# ══════════════════════════════════════════════════════════════════
# Complementariedad con Prowler (AWS)
# ══════════════════════════════════════════════════════════════════
#
# Prowler 4.1 mapea (principalmente): iam_root_mfa, iam_user_mfa_console,
# password_policy, s3_bucket_*, ec2_securitygroup_internet_*.
# ScoutSuite 4.2 mapea (en AWS): iam-root-account-used-recently,
# iam-user-with-multiple-access-keys, cloudtrail-*, vpc-*, rds-*, kms-*.
#
# Hay solape intencional en "iam-user-with-password-and-no-mfa" (Prowler
# tiene 'iam_user_mfa_enabled_console_access' equivalente). El orchestrator
# consolida por (provider, ens_measure, affected_host) para evitar doble
# conteo aguas abajo en ZFP y reporting.

def prowler_overlap_aws_checks() -> list[str]:
    """Checks AWS de ScoutSuite que tambien cubre Prowler 4.1.

    El orchestrator puede usar esta lista para consolidar sin perder
    findings: si ambos reportan MFA-less user sobre la misma ARN, se deja
    la version con mas contexto (normalmente Prowler ASFF).
    """
    return ["iam-user-with-password-and-no-mfa"]
