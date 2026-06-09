"""Discovery Orchestrator (M22).

Coordina un DiscoveryRun: crea el registro, valida modulos y connector_sources,
delega la recuperacion de DTOs crudos al connector de M16 (reusable para mocking
en tests) y persiste assets/identities normalizados. Modulos no implementados
en M22-A se marcan como skipped.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.discovery import DiscoveryRun
from backend.app.models.onboarding import ConnectorConfig
from backend.app.motors.m16_onboarding.connectors.base import (
    ConnectorProvider,
    DiscoveryResult,
)

from . import (
    asset_discovery,
    config_discovery,
    continuity_service,
    data_discovery,
    dataflow_service,
    identity_discovery,
    log_assessment,
)


class OrchestratorError(ValueError):
    pass


SUPPORTED_MODULES = {
    "assets", "identities", "configurations", "vulnerabilities",
    "data", "logs", "dataflow", "continuity",
}
# Modulos con ejecucion automatica (vulnerabilities usa import manual)
AUTO_MODULES = {
    "assets", "identities", "configurations", "data",
    "logs", "dataflow", "continuity",
}
VALID_STATUSES = {"pending", "running", "completed", "failed", "cancelled"}

# Mapping provider -> directorio para identidades
PROVIDER_DIRECTORIO_MAP = {
    "microsoft_365": "entra_id",
    "google_workspace": "google_workspace",
    "github": "github",
    "aws": "aws_iam",
    "azure": "entra_id",
}


# Fetcher signature: async (provider: str, config: dict) -> DiscoveryResult
DTOFetcher = Callable[[str, dict], Awaitable[DiscoveryResult]]


async def _default_fetcher(provider: str, config: dict) -> DiscoveryResult:
    """Fetcher por defecto: devuelve DiscoveryResult vacio. Tests lo sobrescriben."""
    return DiscoveryResult(provider=provider, success=True)


def validate_modules(modules: list[str]) -> list[str]:
    if not modules:
        raise OrchestratorError("modules no puede estar vacio")
    invalid = [m for m in modules if m not in SUPPORTED_MODULES]
    if invalid:
        raise OrchestratorError(
            f"Modulos invalidos: {invalid}. Validos: {sorted(SUPPORTED_MODULES)}"
        )
    return list(modules)


async def _validate_connector_sources(
    session: AsyncSession, project_id: uuid.UUID, sources: dict,
) -> dict:
    """Verifica que los connectors referenciados existen y estan configurados."""
    if not isinstance(sources, dict):
        raise OrchestratorError("connector_sources debe ser dict")
    if not sources:
        return {}
    valid_providers = {p.value for p in ConnectorProvider}
    invalid = [p for p in sources.keys() if p not in valid_providers]
    if invalid:
        raise OrchestratorError(
            f"Providers invalidos: {invalid}. Validos: {sorted(valid_providers)}"
        )
    # Validar existencia de config en DB (no bloquea si no existe: se guarda como sin-config)
    r = await session.execute(
        select(ConnectorConfig.provider).where(
            ConnectorConfig.project_id == project_id,
            ConnectorConfig.provider.in_(list(sources.keys())),
        )
    )
    configured = {row[0] for row in r.all()}
    # Devolvemos solo los que tengan configured=True explicitamente o el flag del caller
    for p, cfg in sources.items():
        if isinstance(cfg, dict):
            cfg.setdefault("configured", p in configured)
    return sources


async def create_run(
    session: AsyncSession,
    project_id: uuid.UUID,
    modules: list[str],
    connector_sources: dict,
    triggered_by: str = "manual",
) -> DiscoveryRun:
    modules = validate_modules(modules)
    connector_sources = await _validate_connector_sources(
        session, project_id, connector_sources or {}
    )

    progress = {
        m: {"status": "pending", "count": 0, "alerts": 0} for m in modules
    }
    run = DiscoveryRun(
        project_id=project_id,
        modules=modules,
        connector_sources=connector_sources,
        status="pending",
        progress=progress,
        triggered_by=triggered_by,
    )
    session.add(run)
    await session.flush()
    return run


async def _execute_assets(
    session: AsyncSession,
    run: DiscoveryRun,
    fetcher: DTOFetcher,
) -> dict:
    total = 0
    for provider, cfg in (run.connector_sources or {}).items():
        result = await fetcher(provider, cfg or {})
        if not result.success:
            continue
        await asset_discovery.discover_from_connector(
            session, run.project_id, run.id, provider, list(result.assets)
        )
        total += len(result.assets)
    return {"status": "completed", "count": total, "alerts": 0}


async def _execute_identities(
    session: AsyncSession,
    run: DiscoveryRun,
    fetcher: DTOFetcher,
) -> dict:
    total = 0
    alerts_total = 0
    for provider, cfg in (run.connector_sources or {}).items():
        result = await fetcher(provider, cfg or {})
        if not result.success:
            continue
        directorio = PROVIDER_DIRECTORIO_MAP.get(provider, provider)
        identities, alerts = await identity_discovery.discover_from_connector(
            session, run.project_id, run.id, provider, directorio, list(result.identities)
        )
        total += len(identities)
        alerts_total += len(alerts)
    return {"status": "completed", "count": total, "alerts": alerts_total}


async def _execute_configurations(
    session: AsyncSession,
    run: DiscoveryRun,
    extras: "ExecuteExtras",
) -> dict:
    configs, alerts = await config_discovery.discover_all_configurations(
        session, run.project_id, run.id,
        connector_sources=run.connector_sources or {},
        fqdns=extras.fqdns,
        domains=extras.domains,
        tls_checker=extras.tls_checker,
        dns_checker=extras.dns_checker,
        cloud_checker=extras.cloud_checker,
    )
    return {"status": "completed", "count": len(configs), "alerts": len(alerts)}


async def _execute_data(
    session: AsyncSession,
    run: DiscoveryRun,
    extras: "ExecuteExtras",
) -> dict:
    stores, alerts = await data_discovery.discover_all_data_stores(
        session, run.project_id, run.id,
        connector_sources=run.connector_sources or {},
        fetcher=extras.data_fetcher,
    )
    return {"status": "completed", "count": len(stores), "alerts": len(alerts)}


async def _execute_logs(
    session: AsyncSession,
    run: DiscoveryRun,
    extras: "ExecuteExtras",
) -> dict:
    assessment, alerts = await log_assessment.assess(
        session, run.project_id, run.id, extras.logging_data,
    )
    return {
        "status": "completed", "count": 1, "alerts": len(alerts),
        "assessment_id": str(assessment.id),
        "nivel_madurez": assessment.nivel_madurez_logging,
    }


async def _execute_dataflow(
    session: AsyncSession,
    run: DiscoveryRun,
    extras: "ExecuteExtras",
) -> dict:
    dfds = await dataflow_service.generate_all_dfds(
        session, run.project_id, run.id,
    )
    return {"status": "completed", "count": len(dfds), "alerts": 0}


async def _execute_continuity(
    session: AsyncSession,
    run: DiscoveryRun,
    extras: "ExecuteExtras",
) -> dict:
    assessment, alerts = await continuity_service.assess(
        session, run.project_id, run.id, extras.continuity_data,
    )
    return {
        "status": "completed", "count": 1, "alerts": len(alerts),
        "assessment_id": str(assessment.id),
        "nivel_madurez": assessment.nivel_madurez_continuidad,
    }


class ExecuteExtras:
    """Dependencias opcionales inyectables para execute_run (tests/prod)."""

    def __init__(
        self,
        fqdns: Optional[list[str]] = None,
        domains: Optional[list[str]] = None,
        tls_checker=None,
        dns_checker=None,
        cloud_checker=None,
        data_fetcher=None,
        logging_data: Optional[dict] = None,
        continuity_data: Optional[dict] = None,
    ) -> None:
        self.fqdns = fqdns or []
        self.domains = domains or []
        self.tls_checker = tls_checker
        self.dns_checker = dns_checker
        self.cloud_checker = cloud_checker
        self.data_fetcher = data_fetcher
        self.logging_data = logging_data
        self.continuity_data = continuity_data


async def execute_run(
    session: AsyncSession,
    run_id: uuid.UUID,
    fetcher: Optional[DTOFetcher] = None,
    extras: Optional[ExecuteExtras] = None,
) -> DiscoveryRun:
    """Ejecuta los modulos del run. fetcher y extras se inyectan en tests."""
    run = await get_run(session, run_id)
    if run is None:
        raise OrchestratorError(f"DiscoveryRun {run_id} no existe")
    if run.status == "cancelled":
        raise OrchestratorError("El run ya fue cancelado")
    if run.status == "completed":
        return run

    fetcher = fetcher or _default_fetcher
    extras = extras or ExecuteExtras()
    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    progress = dict(run.progress or {})

    for module in run.modules or []:
        progress[module] = {**progress.get(module, {}), "status": "running"}
        run.progress = progress
        try:
            if module == "assets":
                progress[module] = await _execute_assets(session, run, fetcher)
            elif module == "identities":
                progress[module] = await _execute_identities(session, run, fetcher)
            elif module == "configurations":
                progress[module] = await _execute_configurations(session, run, extras)
            elif module == "data":
                progress[module] = await _execute_data(session, run, extras)
            elif module == "logs":
                progress[module] = await _execute_logs(session, run, extras)
            elif module == "dataflow":
                progress[module] = await _execute_dataflow(session, run, extras)
            elif module == "continuity":
                progress[module] = await _execute_continuity(session, run, extras)
            elif module == "vulnerabilities":
                progress[module] = {
                    "status": "awaiting_import", "count": 0, "alerts": 0,
                    "reason": "m22_is_importer_not_scanner",
                }
            else:
                progress[module] = {
                    "status": "skipped", "count": 0, "alerts": 0,
                    "reason": "not_supported",
                }
        except Exception as exc:  # continuar con siguientes modulos
            progress[module] = {"status": "failed", "error": str(exc)}
        run.progress = dict(progress)

    any_failed = any(p.get("status") == "failed" for p in progress.values())
    run.status = "failed" if any_failed else "completed"
    run.completed_at = datetime.now(timezone.utc)
    run.progress = dict(progress)
    await session.flush()
    return run


async def get_run(session: AsyncSession, run_id: uuid.UUID) -> Optional[DiscoveryRun]:
    r = await session.execute(
        select(DiscoveryRun).where(
            DiscoveryRun.id == run_id,
            DiscoveryRun.deleted_at.is_(None),
        )
    )
    return r.scalar_one_or_none()


async def list_runs(
    session: AsyncSession, project_id: uuid.UUID
) -> list[DiscoveryRun]:
    r = await session.execute(
        select(DiscoveryRun)
        .where(
            DiscoveryRun.project_id == project_id,
            DiscoveryRun.deleted_at.is_(None),
        )
        .order_by(DiscoveryRun.created_at.desc())
    )
    return list(r.scalars().all())


async def cancel_run(session: AsyncSession, run_id: uuid.UUID) -> DiscoveryRun:
    run = await get_run(session, run_id)
    if run is None:
        raise OrchestratorError(f"DiscoveryRun {run_id} no existe")
    if run.status in {"completed", "failed", "cancelled"}:
        raise OrchestratorError(f"No se puede cancelar run en estado {run.status}")
    run.status = "cancelled"
    run.completed_at = datetime.now(timezone.utc)
    await session.flush()
    return run


async def soft_delete_run(session: AsyncSession, run_id: uuid.UUID) -> bool:
    run = await get_run(session, run_id)
    if run is None:
        return False
    run.deleted_at = datetime.now(timezone.utc)
    await session.flush()
    return True


def run_to_dict(run: DiscoveryRun) -> dict:
    return {
        "id": str(run.id),
        "project_id": str(run.project_id),
        "modules": run.modules or [],
        "connector_sources": run.connector_sources or {},
        "status": run.status,
        "progress": run.progress or {},
        "triggered_by": run.triggered_by,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error_details": run.error_details,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }
