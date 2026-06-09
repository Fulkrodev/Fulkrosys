"""M22 Paso 6 — Orquestador end-to-end.

Ejecuta la secuencia completa de discovery tecnico:
1. Lanzar conectores (M365 + AWS) con fetcher inyectado o real
2. Persistir identidades via identity_discovery legacy
3. Persistir assets enriquecidos con owner M21 + ubicacion (paso6_asset_discoverer)
4. Feed MAGERIT M2 desde assets descubiertos
5. Config detector ENS baseline
6. Vuln inventory import + feed M8
7. Data flow mapper por procesos criticos
8. Build seccion 3.2 E-090 + merge con organizacional (M21)
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m22_discovery import (
    identity_discovery,
    paso6_asset_discoverer,
    paso6_aws_connector,
    paso6_config_detector,
    paso6_data_flow_mapper,
    paso6_e090_technical,
    paso6_m365_connector,
    paso6_vuln_inventory,
)
from backend.app.motors.m22_discovery.orchestrator import (
    PROVIDER_DIRECTORIO_MAP, create_run,
)

logger = logging.getLogger(__name__)


async def run_full_paso6(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    m365_connector: Optional[paso6_m365_connector.M365Paso6Connector] = None,
    aws_connector: Optional[paso6_aws_connector.AWSPaso6Connector] = None,
    ens_category: str = "MEDIA",
    password_policy: Optional[dict[str, Any]] = None,
    security_hub_findings: Optional[list[dict]] = None,
    m365_defender_alerts: Optional[list[dict]] = None,
    nuclei_results: Optional[list[dict]] = None,
    azure_activity_enabled: Optional[bool] = None,
    vault_enabled: Optional[bool] = None,
) -> dict[str, Any]:
    """Orquesta Paso 6 completo. Devuelve resumen rico para logging / UI."""

    # --- 1. Crear run ---
    modules = [
        "identities", "assets", "configurations",
        "vulnerabilities", "dataflow",
    ]
    connector_sources: dict[str, dict] = {}
    if m365_connector is not None:
        connector_sources["microsoft_365"] = {"configured": True}
    if aws_connector is not None:
        connector_sources["aws"] = {"configured": True}
    run = await create_run(
        db, project_id, modules=modules,
        connector_sources=connector_sources,
        triggered_by="paso6",
    )

    report: dict[str, Any] = {
        "run_id": str(run.id),
        "ens_category": ens_category,
        "connectors_used": list(connector_sources.keys()),
    }

    # --- 2. M365 discovery ---
    m365_result: Optional[paso6_m365_connector.M365DiscoveryResult] = None
    if m365_connector is not None:
        m365_result = await m365_connector.run_paso6_discovery()
        provider = "microsoft_365"
        directorio = PROVIDER_DIRECTORIO_MAP.get(provider, provider)
        idents, alerts = await identity_discovery.discover_from_connector(
            db, project_id, run.id, provider, directorio,
            list(m365_result.identities),
        )
        assets_summary = await paso6_asset_discoverer.discover_and_enrich(
            db, project_id, run.id, provider,
            list(m365_result.assets),
        )
        report["m365"] = {
            "identities": len(idents),
            "identities_alerts": len(alerts),
            "assets": assets_summary,
            "ca_policies": len(m365_result.conditional_access_policies),
            "ca_enabled": sum(
                1 for p in m365_result.conditional_access_policies
                if p.state == "enabled"
            ),
            "secure_score_pct": (
                m365_result.secure_score.percentage
                if m365_result.secure_score else None
            ),
            "privileged_users": len(m365_result.privileged_users),
            "mfa_covered": sum(1 for v in m365_result.mfa_by_user.values() if v),
            "mfa_total": len(m365_result.mfa_by_user),
            "errors": list(m365_result.errors),
        }

    # --- 3. AWS discovery ---
    aws_result: Optional[paso6_aws_connector.AWSDiscoveryResult] = None
    if aws_connector is not None:
        aws_result = await aws_connector.run_paso6_discovery()
        provider = "aws"
        directorio = PROVIDER_DIRECTORIO_MAP.get(provider, provider)
        idents, alerts = await identity_discovery.discover_from_connector(
            db, project_id, run.id, provider, directorio,
            list(aws_result.identities),
        )
        assets_summary = await paso6_asset_discoverer.discover_and_enrich(
            db, project_id, run.id, provider,
            list(aws_result.assets),
        )
        report["aws"] = {
            "identities": len(idents),
            "identities_alerts": len(alerts),
            "assets": assets_summary,
            "cloudtrail_trails": len(aws_result.cloudtrail),
            "cloudtrail_logging_ok": sum(
                1 for t in aws_result.cloudtrail if t.is_logging
            ),
            "guardduty_findings": len(aws_result.guardduty_findings),
            "security_hub_pct": (
                aws_result.security_hub.percentage
                if aws_result.security_hub else None
            ),
            "s3_buckets": len(aws_result.s3_buckets),
            "s3_unencrypted": sum(
                1 for b in aws_result.s3_buckets if not b.encryption_enabled
            ),
            "rds_instances": len(aws_result.rds_instances),
            "rds_unencrypted": sum(
                1 for r in aws_result.rds_instances if not r.storage_encrypted
            ),
            "active_regions": list(aws_result.active_regions),
            "errors": list(aws_result.errors),
        }

    # --- 4. Feed MAGERIT (M2) ---
    magerit_feed = await paso6_asset_discoverer.feed_magerit_assets(
        db, project_id,
    )
    report["magerit_feed"] = magerit_feed

    # --- 5. Config detector ---
    s3_buckets = aws_result.s3_buckets if aws_result else []
    rds_instances = aws_result.rds_instances if aws_result else []
    cloudtrail = aws_result.cloudtrail if aws_result else []
    configs, cfg_alerts = await paso6_config_detector.run_all_config_checks(
        db, project_id, run.id,
        ens_category=ens_category,
        password_policy=password_policy,
        s3_buckets=s3_buckets,
        rds_instances=rds_instances,
        cloudtrail=cloudtrail,
        azure_activity_enabled=azure_activity_enabled,
        vault_enabled=vault_enabled,
    )
    report["config_checks"] = {
        "total": len(configs),
        "alerts": len(cfg_alerts),
        "gaps_alta_critica": sum(
            1 for c in configs if c.gap_severidad in {"alta", "critica"}
        ),
    }

    # --- 6. Vulnerability inventory + feed M8 ---
    if any([security_hub_findings, m365_defender_alerts, nuclei_results]):
        vuln_summary = await paso6_vuln_inventory.run_paso6_import(
            db, project_id, run.id,
            security_hub_findings=security_hub_findings,
            m365_defender_alerts=m365_defender_alerts,
            nuclei_results=nuclei_results,
        )
        report["vulns"] = vuln_summary
    else:
        report["vulns"] = await paso6_vuln_inventory.feed_m8_initial_context(
            db, project_id,
        )

    # --- 7. Data flow mapping procesos criticos ---
    dfds = await paso6_data_flow_mapper.map_flows_for_critical_processes(
        db, project_id, run.id,
    )
    flow_rows = await paso6_data_flow_mapper.build_data_flow_table(
        db, project_id,
    )
    report["data_flows"] = {
        "dfds_generados": len(dfds),
        "filas_data_flows": len(flow_rows),
        "observaciones_total": sum(
            len(d.observaciones_seguridad or []) for d in dfds
        ),
    }

    # --- 8. Seccion 3.2 E-090 ---
    technical_section = await paso6_e090_technical.build_technical_section(
        db, project_id, ens_category=ens_category,
    )
    report["e090_tecnica"] = {
        "madurez_nivel": technical_section["madurez_tecnica"]["nivel"],
        "madurez_score": technical_section["madurez_tecnica"]["score_pct"],
        "total_activos": technical_section["inventario_activos"]["total"],
        "mfa_pct": technical_section["estado_identidades"]["mfa_coverage_pct"],
        "vulns_abiertas": technical_section["vulnerabilidades"]["total_abiertas"],
    }
    report["e090_full_section"] = technical_section

    # --- Actualizar progress del run ---
    run.status = "completed"
    from datetime import datetime, timezone
    run.completed_at = datetime.now(timezone.utc)
    progress = dict(run.progress or {})
    for mod in modules:
        progress[mod] = {**progress.get(mod, {}), "status": "completed"}
    run.progress = progress
    await db.flush()

    return report


__all__ = ["run_full_paso6"]
