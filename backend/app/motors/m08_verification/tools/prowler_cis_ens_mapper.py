"""M8 v5.1 — Mapper CIS AWS controls -> medidas ENS Anexo II (RD 311/2022).

Cada check_id de Prowler (columna ``ProwlerCheckId`` en ProductFields ASFF) se
mapea a una o mas medidas ENS. La cobertura inicial (Sesion 10 Paso 4.1) es
IAM + S3 + EC2 (~20 mappings) por ser los servicios de mayor exposicion en
los pilotos previstos.

Ampliaciones naturales:
- RDS/Aurora -> mp.info.3 (cifrado) + op.exp.8 (log)
- CloudTrail/CloudWatch -> op.exp.8 + op.exp.10
- KMS -> mp.info.3 + op.acc.4
- Secrets Manager -> op.acc.2 + mp.info.4
"""
from __future__ import annotations


# ────────────────────────────────────────────────────────────────────
# Mapping CIS check_id -> lista de medidas ENS
# ────────────────────────────────────────────────────────────────────
#
# Cada entrada devuelve la lista ordenada de medidas afectadas (principal
# primero). Una medida puede aparecer en varios checks; un check puede
# mapear a varias medidas si la medida ENS es transversal.

CIS_TO_ENS: dict[str, list[str]] = {
    # ── IAM ────────────────────────────────────────────────────────
    "iam_root_mfa_enabled": ["op.acc.5", "op.acc.4"],
    "iam_root_hardware_mfa_enabled": ["op.acc.5"],
    "iam_user_mfa_enabled_console_access": ["op.acc.5"],
    "iam_password_policy_minimum_length_14": ["op.acc.2"],
    "iam_password_policy_uppercase": ["op.acc.2"],
    "iam_password_policy_lowercase": ["op.acc.2"],
    "iam_password_policy_symbol": ["op.acc.2"],
    "iam_password_policy_number": ["op.acc.2"],
    "iam_password_policy_reuse_24": ["op.acc.2"],
    "iam_avoid_root_usage": ["op.acc.4"],
    "iam_no_inline_policies": ["op.acc.4"],
    "iam_rotate_access_key_90_days": ["op.acc.2"],
    "iam_user_no_setup_initial_access_key": ["op.acc.2"],
    # ── S3 ─────────────────────────────────────────────────────────
    # Exposición pública de almacenamiento = clasificación + control de acceso
    # (mp.s.5 NO existe en RD 311/2022; era código fantasma RD 3/2010).
    "s3_bucket_public_access": ["mp.info.2", "op.acc.4"],
    "s3_bucket_public_read": ["mp.info.2", "op.acc.4"],
    "s3_bucket_public_write": ["mp.info.2", "op.acc.4"],
    "s3_bucket_default_encryption": ["mp.si.2"],  # Criptografía (no mp.info.3=Firma)
    "s3_bucket_no_mfa_delete": ["op.acc.5", "mp.info.6"],
    "s3_bucket_secure_transport_policy": ["mp.com.2"],
    "s3_bucket_server_access_logging_enabled": ["op.exp.8"],
    "s3_bucket_object_versioning": ["mp.info.6"],  # Copias de seguridad
    # ── EC2 ────────────────────────────────────────────────────────
    "ec2_securitygroup_allow_ingress_from_internet_to_ssh": ["mp.com.1"],
    "ec2_securitygroup_allow_ingress_from_internet_to_rdp": ["mp.com.1"],
    "ec2_securitygroup_allow_ingress_from_internet_to_any": ["mp.com.1"],
    "ec2_ebs_default_encryption": ["mp.si.2"],  # Criptografía
    "ec2_instance_public_ip": ["mp.com.1"],
    "ec2_metadata_service_enabled_v1": ["op.exp.2"],
    # ── CloudTrail / Logging (aplicable cross-service) ─────────────
    "cloudtrail_multi_region_enabled": ["op.exp.8"],
    "cloudwatch_log_group_retention_days": ["op.exp.8"],  # Registro (no op.exp.10=claves)
}


# Descripciones cortas de cada medida ENS (Anexo II RD 311/2022).
ENS_MEASURE_LABEL: dict[str, str] = {
    "op.acc.2": "Requisitos de acceso (passwords/MFA)",
    "op.acc.4": "Derechos de acceso (minimo privilegio)",
    "op.acc.5": "Mecanismo de autenticacion",
    "op.exp.2": "Configuracion de seguridad",
    "op.exp.8": "Registro de la actividad",
    "op.exp.10": "Proteccion de claves criptograficas",
    "mp.com.1": "Perimetro seguro",
    "mp.com.2": "Proteccion de la confidencialidad",
    "mp.com.3": "Proteccion de la integridad",
    "mp.si.2": "Criptografia",
    "mp.info.2": "Calificacion de la informacion",
    "mp.info.3": "Firma electronica",
    "mp.info.4": "Sellos de tiempo",
    "mp.info.6": "Copias de seguridad",
}


def map_check_to_ens(check_id: str) -> list[str]:
    """Devuelve la lista de medidas ENS para un CIS check_id.

    Si el check_id no esta mapeado devuelve lista vacia: el finding queda
    disponible pero sin imputacion ENS automatica (revisable a mano).
    """
    if not check_id:
        return []
    return CIS_TO_ENS.get(check_id, [])


def describe_ens_measure(measure: str) -> str:
    """Etiqueta humana corta para una medida ENS."""
    return ENS_MEASURE_LABEL.get(measure, measure)


def coverage_stats() -> dict[str, int]:
    """Estadisticas de cobertura del mapper (para tests)."""
    unique_measures: set[str] = set()
    for measures in CIS_TO_ENS.values():
        unique_measures.update(measures)
    return {
        "checks_mapped": len(CIS_TO_ENS),
        "unique_measures": len(unique_measures),
        "labels_defined": len(ENS_MEASURE_LABEL),
    }
