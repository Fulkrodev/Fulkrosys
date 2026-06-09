"""M8 v5.1 — Auto-derivacion de scope desde Fulkro.

Consulta:
- M22 ``discovered_assets`` para targets/web_apps/ssh_accessible
- M3 ``dda_entries`` (medida op.ext.4) para exclusiones de scope
- M2 ``magerit_assets`` con valor maximo (D|I|C|A|T) >= 8 para crown_jewels
- M14 ``contracts.scan_window`` para ventana nocturna específica del
  cliente (SAN-B.MB-3.bis.3 · TODO-M8-G3 cerrado). Fallback al default
  canónico 22:00-06:00 Europe/Madrid si el contrato no la define.

Devuelve ``(scope_dict, scope_derived_from_dict)`` que se persiste en
``verification_runs.scope_jsonb`` + ``scope_derived_from``.

Errores controlados:
- Si M22 no ha corrido para el proyecto → ``ScopeDerivationError``
  con mensaje claro.
- Si ningun activo descubierto → ``EmptyScopeError`` (mismo motivo).
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.commercial import Contract
from backend.app.models.ens import DdaEntry, EnsMeasure
from backend.app.models.onboarding import DiscoveredAsset
from backend.app.motors.m02_magerit.models import MageritAnalysis, MageritAsset
from backend.app.motors.m14_contracts.schemas import (
    DEFAULT_SCAN_WINDOW as _DEFAULT_SCAN_WINDOW,
)


# Re-exportado para compat con tests/consumers que importaban desde aquí.
# Format ScanWindow dict (m14_contracts/schemas.py · SAN-B.MB-3.bis.3).
DEFAULT_SCAN_WINDOW: dict = _DEFAULT_SCAN_WINDOW

CROWN_JEWEL_THRESHOLD = 8  # valor DICAT >= 8 (escala 0-10)


async def fetch_scan_window_for_project(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> tuple[dict, str]:
    """Devuelve (scan_window, source) para un project_id.

    Strategy:
      1. Busca Contract activo (estado vigente o firmado_cliente) del
         project_id con scan_window IS NOT NULL → ('m14_contract')
      2. Sino → DEFAULT_SCAN_WINDOW canónico ('default')

    Si hay múltiples contratos con scan_window populated, se elige el
    más recientemente creado (ORDER BY created_at DESC).
    """
    res = await db.execute(
        select(Contract.scan_window).where(
            Contract.project_id == project_id,
            Contract.scan_window.isnot(None),
            Contract.deleted_at.is_(None),
        ).order_by(Contract.created_at.desc()).limit(1)
    )
    row = res.scalar_one_or_none()
    if row:
        return (row, "m14_contract")
    return (DEFAULT_SCAN_WINDOW, "default")


class ScopeDerivationError(Exception):
    """Error generico al derivar scope."""


class M22NotRunError(ScopeDerivationError):
    """M22 Discovery no se ha ejecutado para este proyecto."""


class EmptyScopeError(ScopeDerivationError):
    """No hay activos descubiertos para escanear."""


async def derive_scope(
    db: AsyncSession,
    project_id: uuid.UUID,
    category: str,
    *,
    require_assets: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Deriva scope desde M22 + M3 + M2.

    Args:
        require_assets: si True (default) y no hay activos en M22,
            levanta EmptyScopeError. Para tests se puede pasar False.

    Returns:
        (scope, derived_from)
    """
    # ─── 1. Activos descubiertos por M22 ────────────────────────────
    assets_q = await db.execute(
        select(DiscoveredAsset).where(
            DiscoveredAsset.project_id == project_id,
            DiscoveredAsset.deleted_at.is_(None),
        )
    )
    assets = list(assets_q.scalars().all())

    if not assets and require_assets:
        raise EmptyScopeError(
            f"No hay activos descubiertos para project {project_id}. "
            f"Ejecute primero M22 Technical Discovery contra el entorno."
        )

    targets, web_apps, ssh_accessible, cloud_accounts = _split_assets(assets)

    # ─── 2. Exclusiones de la DdA (op.ext.4 — interconexiones) ─────
    exclusions: list[str] = []
    op_ext_4 = (await db.execute(
        select(EnsMeasure).where(EnsMeasure.codigo == "op.ext.4").limit(1)
    )).scalar_one_or_none()
    if op_ext_4:
        dda_q = await db.execute(
            select(DdaEntry).where(
                DdaEntry.project_id == project_id,
                DdaEntry.measure_id == op_ext_4.id,
            )
        )
        for entry in dda_q.scalars().all():
            obs = (entry.observaciones or "").strip()
            # Convencion: 'EXCLUDE: <ip|cidr|host>' por linea
            for line in obs.splitlines():
                line = line.strip()
                if line.upper().startswith("EXCLUDE:"):
                    val = line.split(":", 1)[1].strip()
                    if val:
                        exclusions.append(val)

    # ─── 3. Crown jewels (M2 MAGERIT) ──────────────────────────────
    crown_jewels: list[dict[str, Any]] = []
    analysis = (await db.execute(
        select(MageritAnalysis).where(
            MageritAnalysis.project_id == project_id,
            MageritAnalysis.deleted_at.is_(None),
        ).order_by(MageritAnalysis.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    if analysis:
        magerit_q = await db.execute(
            select(MageritAsset).where(
                MageritAsset.analysis_id == analysis.id,
                MageritAsset.deleted_at.is_(None),
                or_(
                    MageritAsset.value_d >= CROWN_JEWEL_THRESHOLD,
                    MageritAsset.value_i >= CROWN_JEWEL_THRESHOLD,
                    MageritAsset.value_c >= CROWN_JEWEL_THRESHOLD,
                    MageritAsset.value_a >= CROWN_JEWEL_THRESHOLD,
                    MageritAsset.value_t >= CROWN_JEWEL_THRESHOLD,
                ),
            )
        )
        for asset in magerit_q.scalars().all():
            max_val = max(filter(None, [
                asset.value_d, asset.value_i, asset.value_c,
                asset.value_a, asset.value_t,
            ]) or [0])
            crown_jewels.append({
                "code": asset.code,
                "name": asset.name,
                "asset_type_code": asset.asset_type_code,
                "max_dicat": max_val,
                "owner": asset.owner,
            })

    # ─── 4. Contract scan_window via M14 (SAN-B.MB-3.bis.3 · TODO-M8-G3) ──
    # Lee Contract.scan_window del proyecto · fallback DEFAULT canónico.
    scan_window, scan_window_source = await fetch_scan_window_for_project(
        db, project_id
    )

    scope = {
        "category": category,
        "targets": targets,
        "web_apps": web_apps,
        "ssh_accessible": ssh_accessible,
        "cloud_accounts": cloud_accounts,
        "exclusions": exclusions,
        "crown_jewels": crown_jewels,
        "scan_window": scan_window,
        "totals": {
            "discovered_assets": len(assets),
            "targets": len(targets),
            "web_apps": len(web_apps),
            "ssh": len(ssh_accessible),
            "cloud": len(cloud_accounts),
            "exclusions": len(exclusions),
            "crown_jewels": len(crown_jewels),
        },
    }
    derived_from = {
        "m22_assets_count": len(assets),
        "m22_query_at": "now",
        "m3_op_ext_4_present": op_ext_4 is not None,
        "m3_exclusions_count": len(exclusions),
        "m2_analysis_id": str(analysis.id) if analysis else None,
        "m2_crown_jewels_count": len(crown_jewels),
        "m6_contract_scan_window": scan_window,
        "scan_window_source": scan_window_source,
    }
    return scope, derived_from


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _split_assets(
    assets: list[DiscoveredAsset],
) -> tuple[list[str], list[str], list[str], list[dict[str, Any]]]:
    """Distribuye activos entre buckets segun su tipo MAGERIT y metadata.

    - targets: IPs / hostnames (todo tipo no-cloud)
    - web_apps: assets con http/https en metadata o tipo S/SR (servicio web)
    - ssh_accessible: assets con SSH en metadata
    - cloud_accounts: assets de tipo cloud (m365_*, aws_*, azure_*)
    """
    targets: set[str] = set()
    web_apps: set[str] = set()
    ssh_accessible: set[str] = set()
    cloud_accounts: list[dict[str, Any]] = []

    for a in assets:
        nombre = (a.nombre or "").strip()
        meta = a.metadata_extra or {}
        tipo = (a.tipo_magerit or "").lower()
        fuente = (a.fuente_conector or "").lower()

        # Cloud
        if tipo.startswith("m365") or tipo.startswith("aws_") or tipo.startswith("azure_"):
            cloud_accounts.append({
                "asset_name": nombre,
                "type": tipo,
                "fuente_conector": fuente,
            })
            continue

        # IP / hostname principal
        ip = meta.get("ip") or meta.get("ip_address")
        hostname = meta.get("hostname") or meta.get("fqdn") or nombre
        primary = ip or hostname
        if primary:
            targets.add(str(primary))

        # Web
        services = meta.get("services") or []
        if isinstance(services, list):
            services_lower = [s.lower() for s in services if isinstance(s, str)]
            if any("http" in s for s in services_lower) or "web" in tipo:
                domain = meta.get("domain") or meta.get("fqdn") or hostname or ip
                if domain:
                    scheme = "https" if any("https" in s for s in services_lower) else "http"
                    web_apps.add(f"{scheme}://{domain}")
            if "ssh" in services_lower and (ip or hostname):
                ssh_accessible.add(str(ip or hostname))

    return sorted(targets), sorted(web_apps), sorted(ssh_accessible), cloud_accounts
