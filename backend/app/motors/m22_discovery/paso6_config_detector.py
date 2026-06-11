"""M22 Paso 6 — Config Detector ENS baseline.

Evalua configuraciones de seguridad actuales frente a baseline ENS
(Esquema Nacional de Seguridad, RD 311/2022). No modifica nada:
solo observa y persiste hallazgos en DiscoveredConfiguration.

Checks Paso 6:
- MFA coverage % (desde DiscoveredIdentity.mfa_activo)
- Password policy (tenant default + overrides, desde raw metadata)
- Cifrado at-rest (S3 buckets, RDS StorageEncrypted)
- Logging habilitado (CloudTrail trails, Azure Activity Log)
- Backup configuration (RDS BackupRetentionPeriod > 0)

Cada check produce DiscoveredConfiguration + DiscoveryAlert si gap
es alta/critica.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.discovery import DiscoveredConfiguration, DiscoveryAlert
from backend.app.models.onboarding import DiscoveredIdentity

from backend.app.motors.m22_discovery.paso6_aws_connector import (
    CloudTrailStatus,
    RDSInstanceConfig,
    S3BucketConfig,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# Umbrales ENS por categoria
# ════════════════════════════════════════════════════════════════════
#
# Basado en ENS v2 (RD 311/2022) + CCN-STIC 801. Los objetivos son
# deterministas para trazabilidad en auditoria:
#
# - op.acc.6 (mec. autenticacion): MFA obligatorio privilegiados (todos
#   los niveles), general en MEDIA/ALTA.
# - mp.info.3 (cifrado): at-rest obligatorio en MEDIA/ALTA.
# - op.exp.8 (monitorizacion): logging habilitado y revisado en BASICA+.
# - mp.info.6 (copias de seguridad): backups regulares con prueba de restauracion.

MFA_TARGET_PCT = {"BASICA": 60.0, "MEDIA": 90.0, "ALTA": 100.0}
ENCRYPTION_TARGET_PCT = {"BASICA": 50.0, "MEDIA": 90.0, "ALTA": 100.0}
BACKUP_MIN_RETENTION_DAYS = {"BASICA": 7, "MEDIA": 14, "ALTA": 30}


def _gap_severity(actual: float, target: float) -> str:
    """Severidad de gap:
    - >= target: ok (usamos 'info')
    - target - 10pp: baja
    - target - 30pp: media
    - target - 60pp: alta
    - >= target - 60pp: critica
    """
    delta = target - actual
    if delta <= 0:
        return "info"
    if delta <= 10:
        return "baja"
    if delta <= 30:
        return "media"
    if delta <= 60:
        return "alta"
    return "critica"


def _alert_from_config(cfg: DiscoveredConfiguration) -> Optional[DiscoveryAlert]:
    if cfg.gap_severidad not in {"alta", "critica"}:
        return None
    return DiscoveryAlert(
        project_id=cfg.project_id,
        discovery_run_id=cfg.discovery_run_id,
        modulo="configurations",
        severidad=cfg.gap_severidad,
        codigo=f"CFG_{(cfg.control_id or '').upper()}",
        titulo=f"Gap {cfg.gap_severidad}: {cfg.control_id} en {cfg.sistema}",
        descripcion=(
            f"{cfg.control_description or cfg.control_id} — "
            f"Actual: {cfg.valor_actual or '(sin dato)'} | "
            f"Esperado: {cfg.valor_esperado or '(n/a)'}"
        ),
        entity_type="discovered_configuration",
        entity_id=cfg.id,
        medidas_ens_afectadas=list(cfg.medidas_ens_afectadas or []),
    )


# ════════════════════════════════════════════════════════════════════
# Checks individuales
# ════════════════════════════════════════════════════════════════════

async def detect_mfa_coverage(
    db: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    ens_category: str = "MEDIA",
) -> list[DiscoveredConfiguration]:
    """Cobertura MFA global + privilegiados. Produce 2 DiscoveredConfiguration."""
    target_general = MFA_TARGET_PCT.get(ens_category.upper(), 90.0)
    base_where = (
        DiscoveredIdentity.project_id == project_id,
        DiscoveredIdentity.deleted_at.is_(None),
        DiscoveredIdentity.tipo_cuenta.in_(
            ["standard", "privilegiada", "externa"]
        ),
    )
    evaluated = (await db.execute(
        select(func.count(DiscoveredIdentity.id)).where(
            *base_where, DiscoveredIdentity.mfa_activo.isnot(None),
        )
    )).scalar_one() or 0
    with_mfa = (await db.execute(
        select(func.count(DiscoveredIdentity.id)).where(
            *base_where, DiscoveredIdentity.mfa_activo.is_(True),
        )
    )).scalar_one() or 0
    pct_general = (100.0 * with_mfa / evaluated) if evaluated else 0.0

    configs: list[DiscoveredConfiguration] = []

    cfg_general = DiscoveredConfiguration(
        project_id=project_id,
        discovery_run_id=run_id,
        fuente_conector="identities",
        sistema="todos_los_usuarios",
        control_id="op.acc.6_mfa_general",
        control_description=(
            f"Cobertura MFA general para ENS {ens_category} (objetivo "
            f"{target_general:.0f}%)."
        ),
        estado="ok" if pct_general >= target_general else "gap",
        valor_actual=f"{pct_general:.1f}% ({with_mfa}/{evaluated})",
        valor_esperado=f">= {target_general:.0f}%",
        gap_severidad=_gap_severity(pct_general, target_general),
        herramienta_deteccion="m22_config_detector",
        medidas_ens_afectadas=["op.acc.6"],
        raw_output={"evaluated": evaluated, "with_mfa": with_mfa},
    )
    db.add(cfg_general)
    configs.append(cfg_general)

    # Privilegiados: objetivo 100% en todos los niveles ENS
    priv_where = base_where + (DiscoveredIdentity.es_privilegiada.is_(True),)
    priv_eval = (await db.execute(
        select(func.count(DiscoveredIdentity.id)).where(
            *priv_where, DiscoveredIdentity.mfa_activo.isnot(None),
        )
    )).scalar_one() or 0
    priv_mfa = (await db.execute(
        select(func.count(DiscoveredIdentity.id)).where(
            *priv_where, DiscoveredIdentity.mfa_activo.is_(True),
        )
    )).scalar_one() or 0
    pct_priv = (100.0 * priv_mfa / priv_eval) if priv_eval else 0.0

    cfg_priv = DiscoveredConfiguration(
        project_id=project_id,
        discovery_run_id=run_id,
        fuente_conector="identities",
        sistema="cuentas_privilegiadas",
        control_id="op.acc.6_mfa_privilegiadas",
        control_description=(
            "Cobertura MFA para cuentas privilegiadas "
            "(objetivo 100% en cualquier nivel ENS)."
        ),
        estado="ok" if pct_priv >= 100.0 else "gap",
        valor_actual=f"{pct_priv:.1f}% ({priv_mfa}/{priv_eval})",
        valor_esperado="100%",
        gap_severidad=_gap_severity(pct_priv, 100.0),
        herramienta_deteccion="m22_config_detector",
        medidas_ens_afectadas=["op.acc.6", "op.acc.5"],
        raw_output={"evaluated": priv_eval, "with_mfa": priv_mfa},
    )
    db.add(cfg_priv)
    configs.append(cfg_priv)

    await db.flush()
    return configs


async def detect_password_policy(
    db: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    policy: dict[str, Any],
) -> list[DiscoveredConfiguration]:
    """Evalua password policy del tenant. `policy` viene del connector.

    Expected keys en `policy`:
    - min_length (int)
    - complexity (bool)
    - rotation_days (int | None) — 0 = sin rotacion
    - history (int) — numero de pwds anteriores bloqueadas
    - lockout_after (int) — intentos antes de bloqueo
    - source (str) — 'm365' | 'aws_iam' | 'on_prem' | 'desconocida'
    """
    configs: list[DiscoveredConfiguration] = []
    min_len = int(policy.get("min_length") or 0)
    complexity = bool(policy.get("complexity"))
    source = policy.get("source", "desconocida")

    # ENS requiere min 12 chars + complejidad en MEDIA/ALTA
    ok = min_len >= 12 and complexity
    gap = "info" if ok else ("alta" if min_len < 8 else "media")
    cfg = DiscoveredConfiguration(
        project_id=project_id,
        discovery_run_id=run_id,
        fuente_conector=source,
        sistema="politica_contrasenas",
        control_id="op.acc.5_password_policy",
        control_description=(
            "Politica de contrasenas: min 12 caracteres + complejidad (ENS v2)."
        ),
        estado="ok" if ok else "gap",
        valor_actual=(
            f"min_length={min_len} complexity={complexity} "
            f"rotation={policy.get('rotation_days') or 'sin rotacion'}d"
        ),
        valor_esperado="min_length>=12 AND complexity=True",
        gap_severidad=gap,
        herramienta_deteccion="m22_config_detector",
        medidas_ens_afectadas=["op.acc.5"],
        raw_output=dict(policy),
    )
    db.add(cfg)
    configs.append(cfg)
    await db.flush()
    return configs


async def detect_encryption_at_rest(
    db: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    s3_buckets: list[S3BucketConfig],
    rds_instances: list[RDSInstanceConfig],
    ens_category: str = "MEDIA",
) -> list[DiscoveredConfiguration]:
    """Cifrado en reposo: S3 + RDS."""
    target = ENCRYPTION_TARGET_PCT.get(ens_category.upper(), 90.0)
    configs: list[DiscoveredConfiguration] = []

    # Por bucket S3
    unencrypted_buckets: list[str] = []
    for b in s3_buckets or []:
        estado = "ok" if b.encryption_enabled else "gap"
        gap = "info" if b.encryption_enabled else "alta"
        cfg = DiscoveredConfiguration(
            project_id=project_id,
            discovery_run_id=run_id,
            fuente_conector="aws",
            sistema=f"s3://{b.name}",
            control_id="mp.info.3_s3_encryption",
            control_description="Cifrado en reposo del bucket S3 (SSE).",
            estado=estado,
            valor_actual=(
                b.encryption_algorithm if b.encryption_enabled
                else "sin cifrado at-rest"
            ),
            valor_esperado="AES256 o aws:kms",
            gap_severidad=gap,
            herramienta_deteccion="m22_config_detector",
            medidas_ens_afectadas=["mp.info.3", "mp.com.2"],
            raw_output={"bucket": b.name, "region": b.region},
        )
        db.add(cfg)
        configs.append(cfg)
        if not b.encryption_enabled:
            unencrypted_buckets.append(b.name)

    # Por instancia RDS
    for r in rds_instances or []:
        estado = "ok" if r.storage_encrypted else "gap"
        gap = "info" if r.storage_encrypted else "alta"
        cfg = DiscoveredConfiguration(
            project_id=project_id,
            discovery_run_id=run_id,
            fuente_conector="aws",
            sistema=f"rds:{r.instance_id}",
            control_id="mp.info.3_rds_encryption",
            control_description="Cifrado en reposo del volumen RDS.",
            estado=estado,
            valor_actual=(
                "StorageEncrypted=True" if r.storage_encrypted
                else "StorageEncrypted=False"
            ),
            valor_esperado="StorageEncrypted=True",
            gap_severidad=gap,
            herramienta_deteccion="m22_config_detector",
            medidas_ens_afectadas=["mp.info.3"],
            raw_output={"engine": r.engine, "instance_id": r.instance_id},
        )
        db.add(cfg)
        configs.append(cfg)

    # Summary global
    total = len(s3_buckets) + len(rds_instances)
    encrypted = (
        sum(1 for b in s3_buckets if b.encryption_enabled)
        + sum(1 for r in rds_instances if r.storage_encrypted)
    )
    pct = (100.0 * encrypted / total) if total else 100.0
    summary_cfg = DiscoveredConfiguration(
        project_id=project_id,
        discovery_run_id=run_id,
        fuente_conector="aws",
        sistema="cifrado_at_rest_global",
        control_id="mp.info.3_global",
        control_description=(
            f"Cobertura de cifrado en reposo ENS {ens_category} "
            f"(objetivo {target:.0f}%)."
        ),
        estado="ok" if pct >= target else "gap",
        valor_actual=f"{pct:.1f}% ({encrypted}/{total})",
        valor_esperado=f">= {target:.0f}%",
        gap_severidad=_gap_severity(pct, target),
        herramienta_deteccion="m22_config_detector",
        medidas_ens_afectadas=["mp.info.3"],
        raw_output={
            "total": total, "encrypted": encrypted,
            "unencrypted_buckets": unencrypted_buckets,
        },
    )
    db.add(summary_cfg)
    configs.append(summary_cfg)
    await db.flush()
    return configs


async def detect_logging_enabled(
    db: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    cloudtrail_status: list[CloudTrailStatus],
    azure_activity_enabled: Optional[bool] = None,
) -> list[DiscoveredConfiguration]:
    configs: list[DiscoveredConfiguration] = []

    total = len(cloudtrail_status)
    logging_ok = sum(1 for t in cloudtrail_status if t.is_logging)
    multi_region = any(t.is_multi_region for t in cloudtrail_status)

    ok = total > 0 and logging_ok == total and multi_region
    if total == 0:
        gap = "alta"
        estado = "gap"
        actual = "sin CloudTrail configurado"
    elif not multi_region:
        gap = "media"
        estado = "parcial"
        actual = f"{logging_ok}/{total} trails logging, NO multi-region"
    elif logging_ok < total:
        gap = "alta"
        estado = "gap"
        actual = f"{logging_ok}/{total} trails logging activo"
    else:
        gap = "info"
        estado = "ok"
        actual = f"{logging_ok}/{total} trails logging activos + multi-region"

    cfg = DiscoveredConfiguration(
        project_id=project_id,
        discovery_run_id=run_id,
        fuente_conector="aws",
        sistema="cloudtrail",
        control_id="op.exp.8_cloudtrail",
        control_description=(
            "Registro y monitorizacion CloudTrail multi-region con logging activo."
        ),
        estado=estado,
        valor_actual=actual,
        valor_esperado="al menos 1 trail multi-region con logging activo",
        gap_severidad=gap,
        herramienta_deteccion="m22_config_detector",
        medidas_ens_afectadas=["op.exp.8", "op.exp.10"],
        raw_output={
            "trails": [
                {
                    "name": t.trail_name,
                    "multi_region": t.is_multi_region,
                    "logging": t.is_logging,
                }
                for t in cloudtrail_status
            ],
        },
    )
    db.add(cfg)
    configs.append(cfg)

    if azure_activity_enabled is not None:
        cfg_az = DiscoveredConfiguration(
            project_id=project_id,
            discovery_run_id=run_id,
            fuente_conector="azure",
            sistema="azure_activity_log",
            control_id="op.exp.8_azure_activity",
            control_description="Azure Activity Log habilitado globalmente.",
            estado="ok" if azure_activity_enabled else "gap",
            valor_actual="enabled" if azure_activity_enabled else "disabled",
            valor_esperado="enabled",
            gap_severidad="info" if azure_activity_enabled else "alta",
            herramienta_deteccion="m22_config_detector",
            medidas_ens_afectadas=["op.exp.8"],
            raw_output={"enabled": azure_activity_enabled},
        )
        db.add(cfg_az)
        configs.append(cfg_az)

    await db.flush()
    return configs


async def detect_backup_config(
    db: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    rds_instances: list[RDSInstanceConfig],
    vault_enabled: Optional[bool] = None,
    ens_category: str = "MEDIA",
) -> list[DiscoveredConfiguration]:
    target_days = BACKUP_MIN_RETENTION_DAYS.get(ens_category.upper(), 14)
    configs: list[DiscoveredConfiguration] = []

    total = len(rds_instances)
    ok_count = sum(
        1 for r in rds_instances if r.backup_retention_period >= target_days
    )
    for r in rds_instances or []:
        below = r.backup_retention_period < target_days
        cfg = DiscoveredConfiguration(
            project_id=project_id,
            discovery_run_id=run_id,
            fuente_conector="aws",
            sistema=f"rds:{r.instance_id}",
            control_id="mp.info.6_rds_backup",
            control_description=(
                f"Retencion minima de backups RDS {target_days} dias (ENS {ens_category})."
            ),
            estado="ok" if not below else "gap",
            valor_actual=f"{r.backup_retention_period} dias",
            valor_esperado=f">= {target_days} dias",
            gap_severidad=(
                "alta" if r.backup_retention_period == 0
                else ("media" if below else "info")
            ),
            herramienta_deteccion="m22_config_detector",
            medidas_ens_afectadas=["mp.info.6"],
            raw_output={"instance_id": r.instance_id, "retention": r.backup_retention_period},
        )
        db.add(cfg)
        configs.append(cfg)

    # Summary + AWS Backup/vault
    summary_cfg = DiscoveredConfiguration(
        project_id=project_id,
        discovery_run_id=run_id,
        fuente_conector="aws",
        sistema="backups_global",
        control_id="op.cont.3_global",
        control_description=(
            f"Cobertura de backups >= {target_days} dias para RDS."
        ),
        estado="ok" if total and ok_count == total else "gap",
        valor_actual=f"{ok_count}/{total} instancias ok",
        valor_esperado=f"100% retencion >= {target_days}d",
        gap_severidad=(
            "info" if total == 0 or ok_count == total
            else ("alta" if ok_count == 0 else "media")
        ),
        herramienta_deteccion="m22_config_detector",
        medidas_ens_afectadas=["op.cont.3"],
        raw_output={
            "total_rds": total,
            "retention_ok": ok_count,
            "vault_enabled": vault_enabled,
        },
    )
    db.add(summary_cfg)
    configs.append(summary_cfg)
    await db.flush()
    return configs


# ════════════════════════════════════════════════════════════════════
# Wrapper
# ════════════════════════════════════════════════════════════════════

async def run_all_config_checks(
    db: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    *,
    ens_category: str = "MEDIA",
    password_policy: Optional[dict[str, Any]] = None,
    s3_buckets: Optional[list[S3BucketConfig]] = None,
    rds_instances: Optional[list[RDSInstanceConfig]] = None,
    cloudtrail: Optional[list[CloudTrailStatus]] = None,
    azure_activity_enabled: Optional[bool] = None,
    vault_enabled: Optional[bool] = None,
) -> tuple[list[DiscoveredConfiguration], list[DiscoveryAlert]]:
    """Corre todos los checks disponibles y genera alertas para gaps alta/critica."""
    configs: list[DiscoveredConfiguration] = []
    configs += await detect_mfa_coverage(db, project_id, run_id, ens_category)
    if password_policy is not None:
        configs += await detect_password_policy(
            db, project_id, run_id, password_policy,
        )
    configs += await detect_encryption_at_rest(
        db, project_id, run_id,
        s3_buckets or [], rds_instances or [],
        ens_category=ens_category,
    )
    configs += await detect_logging_enabled(
        db, project_id, run_id,
        cloudtrail or [],
        azure_activity_enabled=azure_activity_enabled,
    )
    configs += await detect_backup_config(
        db, project_id, run_id,
        rds_instances or [],
        vault_enabled=vault_enabled,
        ens_category=ens_category,
    )

    alerts: list[DiscoveryAlert] = []
    for cfg in configs:
        alert = _alert_from_config(cfg)
        if alert is not None:
            db.add(alert)
            alerts.append(alert)
    await db.flush()
    return configs, alerts


__all__ = [
    "MFA_TARGET_PCT",
    "ENCRYPTION_TARGET_PCT",
    "BACKUP_MIN_RETENTION_DAYS",
    "detect_mfa_coverage",
    "detect_password_policy",
    "detect_encryption_at_rest",
    "detect_logging_enabled",
    "detect_backup_config",
    "run_all_config_checks",
]
