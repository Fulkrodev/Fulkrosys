"""LLM observability service · MB-7 Q3.A admin panel.

Reads from llm_interaction_log table (see knowledge.py LLMInteractionLog).
Admin-only · cliente NEVER sees tokens or cost (no-internal-refs-externally).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.ai.llm_log_status import (
    ESTIMADO,
    NO_CONTABILIZABLES,
    SQL_SOLO_CONTABILIZABLE,
)


async def _elevate_admin(db: AsyncSession) -> None:
    """FIX(RLS): dashboard de observabilidad LLM es admin cross-cliente.
    llm_interaction_log tiene RLS y los endpoints (require_owner) NO fijan tenant
    context → bajo fulkro_app las queries devolvían vacío/cero en prod. Elevar a
    fulkro_app_bypassrls (transaction-scoped) como operations.py."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))


PERIODS: dict[str, Optional[int]] = {
    "today": 1,
    "week": 7,
    "month": 30,
    "all": None,
}


def _cutoff_for(period: str) -> Optional[datetime]:
    """Convert a named period into a UTC cutoff timestamp (None == all-time)."""
    days = PERIODS.get(period, -1)
    if days == -1:
        raise ValueError(f"Unknown period '{period}'")
    if days is None:
        return None
    return datetime.now(timezone.utc) - timedelta(days=int(days))


async def get_cost_summary(
    db: AsyncSession, period: str = "today",
) -> dict:
    """Aggregate tokens + cost over a period."""
    await _elevate_admin(db)
    cutoff = _cutoff_for(period)
    # D1 · las filas `mock` (sin clave de API) y `error` (la llamada fallo) NO
    # son gasto y quedan FUERA de la suma. `n_calls_no_contabilizados` las
    # publica aparte para que la exclusion se vea, en vez de estrechar el
    # denominador en silencio.
    where_clause = f"WHERE {SQL_SOLO_CONTABILIZABLE}"
    where_todas = ""
    params: dict = {}
    if cutoff is not None:
        where_clause += " AND created_at > :cutoff"
        where_todas = "WHERE created_at > :cutoff"
        params["cutoff"] = cutoff

    row = (await db.execute(
        text(
            "SELECT count(*) AS n_calls, "
            "COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens, "
            "COALESCE(SUM(completion_tokens), 0) AS completion_tokens, "
            "COALESCE(SUM(total_tokens), 0) AS total_tokens, "
            "COALESCE(SUM(cached_input_tokens), 0) AS cached_input_tokens, "
            "COALESCE(SUM(cost_usd), 0)::float AS cost_usd, "
            "COALESCE(AVG(latency_ms), 0)::float AS avg_latency_ms "
            f"FROM llm_interaction_log {where_clause}"
        ),
        params,
    )).mappings().first()

    excluidas = (await db.execute(
        text(
            "SELECT COALESCE(count(*), 0) AS n "
            f"FROM llm_interaction_log {where_todas}"
            + (" AND " if where_todas else " WHERE ")
            + f"NOT ({SQL_SOLO_CONTABILIZABLE})"
        ),
        params,
    )).scalar()

    prompt_t = int(row["prompt_tokens"]) if row else 0
    cached_t = int(row["cached_input_tokens"]) if row else 0
    denom = prompt_t + cached_t
    hit_rate = (cached_t / denom) if denom > 0 else 0.0
    return {
        "period": period,
        "n_calls": int(row["n_calls"]) if row else 0,
        "prompt_tokens": prompt_t,
        "completion_tokens": int(row["completion_tokens"]) if row else 0,
        "total_tokens": int(row["total_tokens"]) if row else 0,
        "cached_input_tokens": cached_t,
        "cache_hit_rate": hit_rate,
        "cost_usd": float(row["cost_usd"]) if row else 0.0,
        "avg_latency_ms": float(row["avg_latency_ms"]) if row else 0.0,
        # D1 · llamadas registradas que NO entran en las cifras de arriba
        # (status mock/error). Si esto crece, el coste que se ve es de menos
        # llamadas de las que hubo, y conviene saberlo.
        "n_calls_no_contabilizados": int(excluidas or 0),
    }


async def get_interactions_paginated(
    db: AsyncSession,
    *,
    feature: Optional[str] = None,
    model: Optional[str] = None,
    status_filter: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Paginated interaction log with optional filters."""
    await _elevate_admin(db)
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    where_clauses: list[str] = []
    params: dict = {"lim": limit, "off": offset}
    if feature:
        where_clauses.append("feature = :feature")
        params["feature"] = feature
    if model:
        where_clauses.append("model = :model")
        params["model"] = model
    if status_filter:
        where_clauses.append("status = :status")
        params["status"] = status_filter
    if project_id:
        where_clauses.append("project_id::text = :project_id")
        params["project_id"] = project_id
    where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    total = (await db.execute(
        text(f"SELECT count(*) FROM llm_interaction_log {where}"),
        params,
    )).scalar() or 0

    rows = (await db.execute(
        text(
            "SELECT id, project_id, feature, model, "
            "prompt_tokens, completion_tokens, total_tokens, "
            "cost_usd, latency_ms, status, error_message, "
            "prompt_preview, response_preview, created_at "
            f"FROM llm_interaction_log {where} "
            "ORDER BY created_at DESC LIMIT :lim OFFSET :off"
        ),
        params,
    )).mappings().all()

    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": int(r["id"]),
                "project_id": (
                    str(r["project_id"]) if r["project_id"] else None
                ),
                "feature": r["feature"],
                "model": r["model"],
                "prompt_tokens": int(r["prompt_tokens"]),
                "completion_tokens": int(r["completion_tokens"]),
                "total_tokens": int(r["total_tokens"]),
                "cost_usd": (
                    float(r["cost_usd"]) if r["cost_usd"] is not None
                    else None
                ),
                "latency_ms": int(r["latency_ms"]),
                "status": r["status"],
                "error_message": r["error_message"],
                "prompt_preview": r["prompt_preview"],
                "response_preview": r["response_preview"],
                "created_at": (
                    r["created_at"].isoformat() if r["created_at"] else None
                ),
            }
            for r in rows
        ],
    }


async def get_top_consumers(
    db: AsyncSession, limit: int = 10, period: str = "month",
) -> list[dict]:
    """Top features by total_tokens consumed over the period."""
    await _elevate_admin(db)
    cutoff = _cutoff_for(period)
    limit = max(1, min(int(limit), 50))
    # D1 · mismo filtro que get_cost_summary: mock/error no son consumo.
    where_clause = f"WHERE {SQL_SOLO_CONTABILIZABLE}"
    params: dict = {"lim": limit}
    if cutoff is not None:
        where_clause += " AND created_at > :cutoff"
        params["cutoff"] = cutoff

    rows = (await db.execute(
        text(
            "SELECT feature, count(*) AS n_calls, "
            "COALESCE(SUM(total_tokens), 0) AS total_tokens, "
            "COALESCE(SUM(cost_usd), 0)::float AS cost_usd "
            f"FROM llm_interaction_log {where_clause} "
            "GROUP BY feature ORDER BY total_tokens DESC LIMIT :lim"
        ),
        params,
    )).mappings().all()

    return [
        {
            "feature": r["feature"],
            "n_calls": int(r["n_calls"]),
            "total_tokens": int(r["total_tokens"]),
            "cost_usd": float(r["cost_usd"]),
        }
        for r in rows
    ]


async def get_anomaly_alerts(
    db: AsyncSession,
    *,
    threshold_usd: float = 10.0,
    threshold_latency_ms: int = 60_000,
    period: str = "today",
) -> list[dict]:
    """Detect anomalous calls (high cost or high latency or error status)."""
    await _elevate_admin(db)
    cutoff = _cutoff_for(period)
    where_clauses: list[str] = []
    params: dict = {
        "cost": float(threshold_usd),
        "lat": int(threshold_latency_ms),
    }
    if cutoff is not None:
        where_clauses.append("created_at > :cutoff")
        params["cutoff"] = cutoff
    # D1 · antes era `status != 'success'`, que ahora marcaria como anomalia
    # TODA fila `estimado` (el streaming del copiloto, que es lo normal). La
    # anomalia es la fila que NO cuenta como gasto: `mock` (falta la clave de
    # API en un entorno que deberia tenerla) o `error` (la llamada fallo).
    where_clauses.append(
        f"(cost_usd >= :cost OR latency_ms >= :lat OR NOT ({SQL_SOLO_CONTABILIZABLE}))"
    )
    where = "WHERE " + " AND ".join(where_clauses)

    rows = (await db.execute(
        text(
            "SELECT id, feature, model, total_tokens, cost_usd, "
            "latency_ms, status, error_message, created_at "
            f"FROM llm_interaction_log {where} "
            "ORDER BY created_at DESC LIMIT 100"
        ),
        params,
    )).mappings().all()

    return [
        {
            "id": int(r["id"]),
            "feature": r["feature"],
            "model": r["model"],
            # D1 · NULL cuando no hubo llamada (mock) o fallo (error). Se
            # publica como None, no como 0: 0 diria "medido y salio cero".
            "total_tokens": (
                int(r["total_tokens"]) if r["total_tokens"] is not None else None
            ),
            "cost_usd": (
                float(r["cost_usd"]) if r["cost_usd"] is not None else None
            ),
            "latency_ms": int(r["latency_ms"]),
            "status": r["status"],
            "error_message": r["error_message"],
            "created_at": (
                r["created_at"].isoformat() if r["created_at"] else None
            ),
            "reason": _explain_anomaly(
                cost_usd=r["cost_usd"],
                latency_ms=r["latency_ms"],
                status=r["status"],
                threshold_usd=threshold_usd,
                threshold_latency_ms=threshold_latency_ms,
            ),
        }
        for r in rows
    ]


def _explain_anomaly(
    *,
    cost_usd: Optional[float],
    latency_ms: int,
    status: str,
    threshold_usd: float,
    threshold_latency_ms: int,
) -> str:
    reasons: list[str] = []
    if cost_usd is not None and cost_usd >= threshold_usd:
        reasons.append(f"cost ${cost_usd:.2f} >= ${threshold_usd:.2f}")
    if latency_ms >= threshold_latency_ms:
        reasons.append(f"latency {latency_ms}ms >= {threshold_latency_ms}ms")
    if status in NO_CONTABILIZABLES:
        reasons.append(f"status={status}")
    elif status == ESTIMADO:
        # No es una anomalia por si misma, pero si la fila sale listada hay que
        # decir que su coste es una estimacion por longitud, no una medida.
        reasons.append("coste estimado, no medido")
    return " · ".join(reasons) or "n/a"


async def get_project_token_usage(
    db: AsyncSession, project_id: str, days: int = 30,
) -> dict:
    """Aggregate token usage per agent for a project over the last N days.

    Reads from canonical ``llm_interaction_log`` table (ADR-025 · NO duplicate
    table). Returns total + per-agent breakdown including cached_input_tokens
    + cache_hit_rate.
    """
    await _elevate_admin(db)
    days = max(1, min(int(days), 365))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    params = {"project_id": project_id, "cutoff": cutoff}

    total_row = (await db.execute(
        text(
            "SELECT count(*) AS n_calls, "
            "COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens, "
            "COALESCE(SUM(completion_tokens), 0) AS completion_tokens, "
            "COALESCE(SUM(total_tokens), 0) AS total_tokens, "
            "COALESCE(SUM(cached_input_tokens), 0) AS cached_input_tokens, "
            "COALESCE(SUM(cost_usd), 0)::float AS cost_usd "
            "FROM llm_interaction_log "
            "WHERE project_id::text = :project_id AND created_at > :cutoff "
            f"AND {SQL_SOLO_CONTABILIZABLE}"  # D1
        ),
        params,
    )).mappings().first()

    by_agent_rows = (await db.execute(
        text(
            "SELECT feature AS agent, count(*) AS n_calls, "
            "COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens, "
            "COALESCE(SUM(completion_tokens), 0) AS completion_tokens, "
            "COALESCE(SUM(cached_input_tokens), 0) AS cached_input_tokens, "
            "COALESCE(SUM(cost_usd), 0)::float AS cost_usd "
            "FROM llm_interaction_log "
            "WHERE project_id::text = :project_id AND created_at > :cutoff "
            f"AND {SQL_SOLO_CONTABILIZABLE} "  # D1
            "GROUP BY feature ORDER BY SUM(total_tokens) DESC NULLS LAST"
        ),
        params,
    )).mappings().all()

    prompt_t = int(total_row["prompt_tokens"]) if total_row else 0
    cached_t = int(total_row["cached_input_tokens"]) if total_row else 0
    denom = prompt_t + cached_t
    hit_rate = (cached_t / denom) if denom > 0 else 0.0

    return {
        "project_id": project_id,
        "days": days,
        "n_calls": int(total_row["n_calls"]) if total_row else 0,
        "prompt_tokens": prompt_t,
        "completion_tokens": (
            int(total_row["completion_tokens"]) if total_row else 0
        ),
        "total_tokens": int(total_row["total_tokens"]) if total_row else 0,
        "cached_input_tokens": cached_t,
        "cache_hit_rate": hit_rate,
        "cost_usd": float(total_row["cost_usd"]) if total_row else 0.0,
        "by_agent": [
            {
                "agent": r["agent"],
                "n_calls": int(r["n_calls"]),
                "prompt_tokens": int(r["prompt_tokens"]),
                "completion_tokens": int(r["completion_tokens"]),
                "cached_input_tokens": int(r["cached_input_tokens"]),
                "cost_usd": float(r["cost_usd"]),
            }
            for r in by_agent_rows
        ],
    }


async def get_agent_cache_stats(
    db: AsyncSession, agent_name: str, days: int = 30,
) -> dict:
    """Cache hit-rate stats for a single agent (feature) over last N days.

    hit_rate = cached / (prompt_tokens + cached). 0.0 si denom == 0.
    """
    await _elevate_admin(db)
    days = max(1, min(int(days), 365))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    row = (await db.execute(
        text(
            "SELECT count(*) AS n_calls, "
            "COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens, "
            "COALESCE(SUM(cached_input_tokens), 0) AS cached_input_tokens, "
            "COALESCE(SUM(cost_usd), 0)::float AS cost_usd "
            "FROM llm_interaction_log "
            "WHERE feature = :agent AND created_at > :cutoff "
            f"AND {SQL_SOLO_CONTABILIZABLE}"  # D1
        ),
        {"agent": agent_name, "cutoff": cutoff},
    )).mappings().first()

    prompt_t = int(row["prompt_tokens"]) if row else 0
    cached_t = int(row["cached_input_tokens"]) if row else 0
    denom = prompt_t + cached_t
    hit_rate = (cached_t / denom) if denom > 0 else 0.0

    return {
        "agent": agent_name,
        "days": days,
        "n_calls": int(row["n_calls"]) if row else 0,
        "prompt_tokens": prompt_t,
        "cached_input_tokens": cached_t,
        "cache_hit_rate": hit_rate,
        "cost_usd": float(row["cost_usd"]) if row else 0.0,
    }
