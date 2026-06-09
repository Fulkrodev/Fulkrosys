"""Drift compute service · MB-7.bis atom 7.bis.2.

Auto-compute drift across the 10 DRIFT_DIMENSIONS cementadas (Q3.D):
  infraestructura · identidad · proveedores · normativa · overlay
  cpstic · roles · continuidad · evidencias · contratos

For each retainer active, runs 10 lightweight cross-motor read-only queries
and registers `RetainerDriftEvent` rows when a delta is detected vs the
prior baseline (last computation timestamp).

Cómputo concentrado en M23 (Q3.A rejected B distributed pattern · keep
read-only side here). Severity heuristic per dim:
  CRITICAL · evidencias caducadas · contratos lapsed
  HIGH     · normativa alerts last 30d critical
  MEDIUM   · stakeholder changes · DdA delta
  LOW      · informational
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.retainer import RetainerContract, RetainerDriftEvent


logger = logging.getLogger(__name__)


# Lookback window for "last computation" baseline · default 7 days.
LOOKBACK_DAYS = 7


@dataclass
class DimResult:
    """Single dimension compute result."""

    dimension: str
    delta_detected: bool
    severity: str  # LOW | MEDIUM | HIGH | CRITICAL
    impacto: str   # EVIDENCE | DOCUMENT | CONTROL | ROUTE | AUDIT
    descripcion: str


@dataclass
class DriftComputeResult:
    """Aggregated result per retainer."""

    retainer_id: str
    project_id: str
    dims_computed: int
    drifts_registered: int
    results: list[DimResult] = field(default_factory=list)


async def _count(db: AsyncSession, sql: str, params: dict) -> int:
    row = (await db.execute(text(sql), params)).first()
    return int(row[0] or 0) if row else 0


async def _dim_evidencias(db: AsyncSession, project_id: str) -> DimResult:
    """Count expired evidence rows."""
    expired = await _count(
        db,
        "SELECT count(*) FROM evidence "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "AND fecha_caducidad IS NOT NULL "
        "AND fecha_caducidad < NOW()",
        {"pid": project_id},
    )
    return DimResult(
        dimension="evidencias",
        delta_detected=expired > 0,
        severity="CRITICAL" if expired >= 5 else "HIGH" if expired > 0 else "LOW",
        impacto="EVIDENCE",
        descripcion=f"{expired} evidencias caducadas",
    )


async def _dim_normativa(
    db: AsyncSession, lookback_dt: datetime,
) -> DimResult:
    """Count normativa_alerts critical/high in last lookback days."""
    rows = (await db.execute(
        text(
            "SELECT count(*) FROM normativa_alerts "
            "WHERE detected_at > :cutoff "
            "AND severity IN ('critical', 'high')"
        ),
        {"cutoff": lookback_dt},
    )).first()
    cnt = int(rows[0] or 0) if rows else 0
    return DimResult(
        dimension="normativa",
        delta_detected=cnt > 0,
        severity="HIGH" if cnt >= 3 else "MEDIUM" if cnt > 0 else "LOW",
        impacto="DOCUMENT",
        descripcion=f"{cnt} alertas normativa critic/high últimos {LOOKBACK_DAYS}d",
    )


async def _dim_identidad(
    db: AsyncSession, project_id: str, lookback_dt: datetime,
) -> DimResult:
    """Stakeholder identity changes (m30 client_contacts updated since)."""
    cnt = await _count(
        db,
        "SELECT count(*) FROM client_contacts "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "AND updated_at > :cutoff",
        {"pid": project_id, "cutoff": lookback_dt},
    )
    return DimResult(
        dimension="identidad",
        delta_detected=cnt > 0,
        severity="MEDIUM" if cnt > 0 else "LOW",
        impacto="ROUTE",
        descripcion=f"{cnt} contactos M30 actualizados últimos {LOOKBACK_DAYS}d",
    )


async def _dim_contratos(db: AsyncSession, project_id: str) -> DimResult:
    """Provider contracts renewing in next 60d (documents.expires_at)."""
    cnt = await _count(
        db,
        "SELECT count(*) FROM documents "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "AND clasificacion = 'contrato' "
        "AND expires_at IS NOT NULL "
        "AND expires_at BETWEEN NOW() AND NOW() + INTERVAL '60 days'",
        {"pid": project_id},
    )
    return DimResult(
        dimension="contratos",
        delta_detected=cnt > 0,
        severity="HIGH" if cnt >= 3 else "MEDIUM" if cnt > 0 else "LOW",
        impacto="DOCUMENT",
        descripcion=f"{cnt} contratos vencen próximos 60d",
    )


async def _dim_proveedores(db: AsyncSession, project_id: str) -> DimResult:
    """Provider list size delta (count active providers · simple)."""
    cnt = await _count(
        db,
        "SELECT count(*) FROM providers "
        "WHERE project_id = :pid AND deleted_at IS NULL",
        {"pid": project_id},
    )
    return DimResult(
        dimension="proveedores",
        delta_detected=False,  # baseline tracking deferred
        severity="LOW",
        impacto="ROUTE",
        descripcion=f"{cnt} proveedores activos (baseline tracking pendiente)",
    )


async def _dim_roles(
    db: AsyncSession, project_id: str, lookback_dt: datetime,
) -> DimResult:
    """Role assignment changes."""
    cnt = await _count(
        db,
        "SELECT count(*) FROM project_role_assignments "
        "WHERE project_id = :pid "
        "AND created_at > :cutoff",
        {"pid": project_id, "cutoff": lookback_dt},
    )
    return DimResult(
        dimension="roles",
        delta_detected=cnt > 0,
        severity="MEDIUM" if cnt > 0 else "LOW",
        impacto="ROUTE",
        descripcion=f"{cnt} cambios de rol últimos {LOOKBACK_DAYS}d",
    )


async def _dim_infraestructura(db: AsyncSession, project_id: str) -> DimResult:
    """MAGERIT assets count · used as proxy for infra change."""
    cnt = await _count(
        db,
        "SELECT count(*) FROM magerit_assets a "
        "JOIN magerit_analysis ma ON ma.id = a.analysis_id "
        "WHERE ma.project_id = :pid AND a.deleted_at IS NULL",
        {"pid": project_id},
    )
    return DimResult(
        dimension="infraestructura",
        delta_detected=False,  # baseline tracking deferred
        severity="LOW",
        impacto="AUDIT",
        descripcion=f"{cnt} activos MAGERIT inventariados",
    )


async def _dim_overlay(db: AsyncSession, project_id: str) -> DimResult:
    """Conformity overlay changes (m27 routes · PCE/uCeENS)."""
    return DimResult(
        dimension="overlay",
        delta_detected=False,
        severity="LOW",
        impacto="CONTROL",
        descripcion="overlay PCE/uCeENS (baseline tracking pendiente)",
    )


async def _dim_cpstic(db: AsyncSession) -> DimResult:
    """CCN-STIC alerts last lookback days (overlap normativa but specific)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    cnt = await _count(
        db,
        "SELECT count(*) FROM normativa_alerts "
        "WHERE source = 'ccn_stic' AND detected_at > :cutoff",
        {"cutoff": cutoff},
    )
    return DimResult(
        dimension="cpstic",
        delta_detected=cnt > 0,
        severity="MEDIUM" if cnt > 0 else "LOW",
        impacto="CONTROL",
        descripcion=f"{cnt} actualizaciones CCN-STIC últimos {LOOKBACK_DAYS}d",
    )


async def _dim_continuidad(db: AsyncSession, project_id: str) -> DimResult:
    """Continuity activities overdue · retainer_activities."""
    cnt = await _count(
        db,
        "SELECT count(*) FROM retainer_activities ra "
        "JOIN retainer_contracts rc ON rc.id = ra.retainer_contract_id "
        "WHERE rc.project_id = :pid AND ra.deleted_at IS NULL "
        "AND ra.estado = 'vencida'",
        {"pid": project_id},
    )
    return DimResult(
        dimension="continuidad",
        delta_detected=cnt > 0,
        severity="HIGH" if cnt > 0 else "LOW",
        impacto="AUDIT",
        descripcion=f"{cnt} actividades vencidas",
    )


class DriftComputeService:
    """Service to compute drift events per retainer · invoked by Celery weekly."""

    async def compute_drift_for_retainer(
        self,
        db: AsyncSession,
        retainer_id: uuid.UUID,
    ) -> DriftComputeResult:
        """Compute all 10 drift dimensions for a single retainer.

        Persists `RetainerDriftEvent` row per dim with detected delta.
        Cómputo cross-motor read-only · safe to run concurrently.
        """
        retainer = (await db.execute(
            select(RetainerContract).where(RetainerContract.id == retainer_id)
        )).scalar_one_or_none()
        if not retainer:
            raise ValueError(f"Retainer {retainer_id} not found")

        project_id = str(retainer.project_id)
        lookback_dt = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

        results: list[DimResult] = [
            await _dim_evidencias(db, project_id),
            await _dim_normativa(db, lookback_dt),
            await _dim_identidad(db, project_id, lookback_dt),
            await _dim_contratos(db, project_id),
            await _dim_proveedores(db, project_id),
            await _dim_roles(db, project_id, lookback_dt),
            await _dim_infraestructura(db, project_id),
            await _dim_overlay(db, project_id),
            await _dim_cpstic(db),
            await _dim_continuidad(db, project_id),
        ]

        drifts_registered = 0
        for dim in results:
            if not dim.delta_detected:
                continue
            event = RetainerDriftEvent(
                retainer_contract_id=retainer_id,
                project_id=retainer.project_id,
                dimension=dim.dimension,
                descripcion=dim.descripcion,
                severidad=dim.severity,
                impacto=dim.impacto,
                estado="open",
            )
            db.add(event)
            drifts_registered += 1

        await db.flush()
        return DriftComputeResult(
            retainer_id=str(retainer_id),
            project_id=project_id,
            dims_computed=len(results),
            drifts_registered=drifts_registered,
            results=results,
        )

    async def compute_drift_all_active(
        self, db: AsyncSession,
    ) -> list[DriftComputeResult]:
        """Iterate active retainers and compute drift for each."""
        retainers = (await db.execute(
            select(RetainerContract).where(
                RetainerContract.deleted_at.is_(None),
                RetainerContract.estado == "activo",
            )
        )).scalars().all()

        out: list[DriftComputeResult] = []
        for r in retainers:
            try:
                result = await self.compute_drift_for_retainer(db, r.id)
                out.append(result)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Drift compute failed for retainer %s: %s", r.id, exc,
                )
        return out
