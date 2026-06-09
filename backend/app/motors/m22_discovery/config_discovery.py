"""Configuration Discovery Service (M22-B).

Ejecuta checks de seguridad sobre los servicios del cliente (TLS, DNS,
cloud security scores) y los normaliza a DiscoveredConfiguration.

Los checkers externos (TLS, DNS, M365 Graph, AWS SecurityHub) se inyectan
como callables — en produccion se usan implementaciones con
testssl.sh/dnspython/boto3; en tests se pasan mocks para evitar I/O real.
"""
from __future__ import annotations

import uuid
from typing import Awaitable, Callable, Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.discovery import DiscoveredConfiguration, DiscoveryAlert


# ========== Tipado de checkers inyectables ==========

# Cada checker devuelve lista de dicts con claves minimas:
#   control_id, estado, valor_actual, valor_esperado, gap_severidad,
#   medidas_ens, control_description (opcional), raw (opcional)
TLSChecker = Callable[[str], Awaitable[list[dict]]]
DNSChecker = Callable[[str], Awaitable[list[dict]]]
CloudScoreChecker = Callable[[str, dict], Awaitable[list[dict]]]


async def _noop_tls_checker(fqdn: str) -> list[dict]:
    return []


async def _noop_dns_checker(domain: str) -> list[dict]:
    return []


async def _noop_cloud_checker(provider: str, config: dict) -> list[dict]:
    return []


# ========== TLS defaults (referencia: no ejecuta testssl.sh) ==========

TLS_BASELINE = {
    "tls_version": {
        "expected": "TLS 1.2+",
        "medidas": ["mp.com.2"],
    },
    "tls_certificate_valid": {
        "expected": "vigente",
        "medidas": ["mp.com.2", "mp.com.3"],
    },
    "tls_certificate_expiry": {
        "expected": ">= 30 dias",
        "medidas": ["mp.com.2"],
    },
    "tls_strong_ciphers": {
        "expected": "solo cifrados fuertes",
        "medidas": ["mp.com.2"],
    },
    "hsts_enabled": {
        "expected": "HSTS activo",
        "medidas": ["mp.com.2"],
    },
}

DNS_BASELINE = {
    "spf_record": {"expected": "v=spf1 ... -all|~all", "medidas": ["mp.com.1"]},
    "dkim_record": {"expected": "selector valido", "medidas": ["mp.com.1"]},
    "dmarc_record": {"expected": "policy reject|quarantine", "medidas": ["mp.com.1"]},
    "dnssec_enabled": {"expected": "DNSSEC activo", "medidas": ["mp.com.2"]},
}


def _persist_config(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    sistema: str,
    fuente: str,
    herramienta: str,
    item: dict,
) -> DiscoveredConfiguration:
    cfg = DiscoveredConfiguration(
        project_id=project_id,
        discovery_run_id=run_id,
        fuente_conector=fuente,
        sistema=sistema,
        control_id=item["control_id"],
        control_description=item.get("control_description"),
        estado=item["estado"],
        valor_actual=item.get("valor_actual"),
        valor_esperado=item.get("valor_esperado"),
        gap_severidad=item.get("gap_severidad"),
        herramienta_deteccion=herramienta,
        medidas_ens_afectadas=list(item.get("medidas_ens", []) or []),
        raw_output=dict(item.get("raw", {}) or {}),
    )
    session.add(cfg)
    return cfg


def _alert_from_config(
    cfg: DiscoveredConfiguration,
) -> Optional[DiscoveryAlert]:
    if cfg.gap_severidad not in {"alta", "critica"}:
        return None
    sev = "critica" if cfg.gap_severidad == "critica" else "alta"
    return DiscoveryAlert(
        project_id=cfg.project_id,
        discovery_run_id=cfg.discovery_run_id,
        modulo="configurations",
        severidad=sev,
        codigo=f"CFG_{cfg.control_id.upper()}",
        titulo=f"Gap {sev}: {cfg.control_id} en {cfg.sistema}",
        descripcion=(
            f"{cfg.control_description or cfg.control_id} - "
            f"Actual: {cfg.valor_actual or '(sin dato)'} | "
            f"Esperado: {cfg.valor_esperado or '(n/a)'}"
        ),
        entity_type="discovered_configuration",
        entity_id=cfg.id,
        medidas_ens_afectadas=list(cfg.medidas_ens_afectadas or []),
    )


async def check_tls_for_fqdns(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    fqdns: Iterable[str],
    checker: Optional[TLSChecker] = None,
) -> list[DiscoveredConfiguration]:
    """Ejecuta TLSChecker por cada FQDN y persiste los resultados."""
    checker = checker or _noop_tls_checker
    out: list[DiscoveredConfiguration] = []
    for fqdn in fqdns or []:
        items = await checker(fqdn)
        for item in items:
            cfg = _persist_config(
                session, project_id, run_id,
                sistema=fqdn, fuente="tls", herramienta="testssl_sh",
                item=item,
            )
            out.append(cfg)
    await session.flush()
    return out


async def check_dns_for_domains(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    domains: Iterable[str],
    checker: Optional[DNSChecker] = None,
) -> list[DiscoveredConfiguration]:
    """Ejecuta DNSChecker por cada dominio y persiste los resultados."""
    checker = checker or _noop_dns_checker
    out: list[DiscoveredConfiguration] = []
    for domain in domains or []:
        items = await checker(domain)
        for item in items:
            cfg = _persist_config(
                session, project_id, run_id,
                sistema=domain, fuente="dns", herramienta="python_dns",
                item=item,
            )
            out.append(cfg)
    await session.flush()
    return out


async def check_cloud_scores(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    connector_sources: dict,
    checker: Optional[CloudScoreChecker] = None,
) -> list[DiscoveredConfiguration]:
    """Consulta secure_scores/security_hub de cada provider del run."""
    checker = checker or _noop_cloud_checker
    out: list[DiscoveredConfiguration] = []
    provider_herr = {
        "microsoft_365": ("m365_secure_score", "graph_api"),
        "aws": ("aws_security_hub", "boto3"),
        "azure": ("azure_defender", "azure_sdk"),
        "google_workspace": ("gws_security_center", "google_api"),
    }
    for provider, cfg_raw in (connector_sources or {}).items():
        items = await checker(provider, cfg_raw or {})
        fuente, herram = provider_herr.get(provider, (f"cloud_{provider}", "cloud_api"))
        for item in items:
            cfg = _persist_config(
                session, project_id, run_id,
                sistema=item.get("sistema") or provider,
                fuente=fuente, herramienta=herram, item=item,
            )
            out.append(cfg)
    await session.flush()
    return out


async def discover_all_configurations(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    connector_sources: dict,
    fqdns: Optional[Iterable[str]] = None,
    domains: Optional[Iterable[str]] = None,
    tls_checker: Optional[TLSChecker] = None,
    dns_checker: Optional[DNSChecker] = None,
    cloud_checker: Optional[CloudScoreChecker] = None,
) -> tuple[list[DiscoveredConfiguration], list[DiscoveryAlert]]:
    """Ejecuta todos los checks + genera alertas para gaps alta/critica."""
    configs: list[DiscoveredConfiguration] = []
    configs += await check_tls_for_fqdns(
        session, project_id, run_id, fqdns or [], tls_checker,
    )
    configs += await check_dns_for_domains(
        session, project_id, run_id, domains or [], dns_checker,
    )
    configs += await check_cloud_scores(
        session, project_id, run_id, connector_sources or {}, cloud_checker,
    )

    alerts: list[DiscoveryAlert] = []
    for cfg in configs:
        alert = _alert_from_config(cfg)
        if alert is not None:
            session.add(alert)
            alerts.append(alert)
    await session.flush()
    return configs, alerts


async def list_configurations(
    session: AsyncSession,
    project_id: uuid.UUID,
    gap_severidad: Optional[str] = None,
    fuente: Optional[str] = None,
    estado: Optional[str] = None,
) -> list[DiscoveredConfiguration]:
    stmt = select(DiscoveredConfiguration).where(
        DiscoveredConfiguration.project_id == project_id,
        DiscoveredConfiguration.deleted_at.is_(None),
    )
    if gap_severidad:
        stmt = stmt.where(DiscoveredConfiguration.gap_severidad == gap_severidad)
    if fuente:
        stmt = stmt.where(DiscoveredConfiguration.fuente_conector == fuente)
    if estado:
        stmt = stmt.where(DiscoveredConfiguration.estado == estado)
    r = await session.execute(stmt.order_by(DiscoveredConfiguration.created_at.desc()))
    return list(r.scalars().all())


async def get_configuration(
    session: AsyncSession, config_id: uuid.UUID
) -> Optional[DiscoveredConfiguration]:
    r = await session.execute(
        select(DiscoveredConfiguration).where(
            DiscoveredConfiguration.id == config_id,
            DiscoveredConfiguration.deleted_at.is_(None),
        )
    )
    return r.scalar_one_or_none()


async def configurations_summary(session: AsyncSession, project_id: uuid.UUID) -> dict:
    base = (
        DiscoveredConfiguration.project_id == project_id,
        DiscoveredConfiguration.deleted_at.is_(None),
    )
    total = (await session.execute(
        select(func.count(DiscoveredConfiguration.id)).where(*base)
    )).scalar_one() or 0

    by_estado: dict[str, int] = {}
    r = await session.execute(
        select(DiscoveredConfiguration.estado, func.count(DiscoveredConfiguration.id))
        .where(*base)
        .group_by(DiscoveredConfiguration.estado)
    )
    for e, c in r.all():
        by_estado[e or "unknown"] = c

    by_gap: dict[str, int] = {}
    r = await session.execute(
        select(
            DiscoveredConfiguration.gap_severidad, func.count(DiscoveredConfiguration.id)
        )
        .where(*base)
        .group_by(DiscoveredConfiguration.gap_severidad)
    )
    for g, c in r.all():
        by_gap[g or "none"] = c

    by_fuente: dict[str, int] = {}
    r = await session.execute(
        select(
            DiscoveredConfiguration.fuente_conector, func.count(DiscoveredConfiguration.id)
        )
        .where(*base)
        .group_by(DiscoveredConfiguration.fuente_conector)
    )
    for f, c in r.all():
        by_fuente[f or "unknown"] = c

    return {
        "total": total,
        "by_estado": by_estado,
        "by_gap_severidad": by_gap,
        "by_fuente": by_fuente,
    }
