"""LLM prioritizer puro para M4 Gap Analysis (Sesion 9 Paso 3.3).

Absorbe la logica conceptual del A7 Gap Analyzer eliminado en STEP B
como FUNCION PURA dentro de M04 (NO agente separado). Patron similar
a M05 `personalization.enrich_description_with_llm`.

Uso:

    from backend.app.motors.m04_gap.llm_prioritizer import (
        prioritize_gaps_with_llm,
    )

    result = await prioritize_gaps_with_llm(
        gaps=[{"id": "...", "medida_afectada": "mp.info.3", ...}],
        client_context={"sector": "sanidad", "ens_category": "MEDIA",
                        "size": "PYME"},
    )

Modelo: Sonnet 4.6 + prompt caching. Output JSON strict con
prioritized_gaps (rank + rationale + effort + impact + quick_win)
+ summary agregado.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from backend.app.config import get_settings
from backend.app.motors.m04_gap.prompt_prioritize import PROMPT

logger = logging.getLogger(__name__)


# Sonnet 4.6 pricing (USD/Mtoken).
_SONNET_46_USD_IN: float = 3.0
_SONNET_46_USD_OUT: float = 15.0
_SONNET_46_USD_CACHE_WRITE: float = 3.75
_SONNET_46_USD_CACHE_READ: float = 0.30
_USD_TO_EUR: float = 0.93

_VALID_SECTORS = {"sanidad", "aapp", "fintech", "otro"}
_VALID_CATEGORIES = {"BASICA", "MEDIA", "ALTA"}
_VALID_IMPACTS = {"alto", "medio", "bajo"}

_MAX_TOKENS = 3000
_TEMPERATURE = 0.2
_MODEL = "sonnet-4.6"


def _build_user_message(
    gaps: list[dict[str, Any]],
    client_context: dict[str, Any],
) -> str:
    lines = [
        "Prioriza estos gaps ENS segun impacto contextual sector del cliente.",
        "",
        "CLIENT CONTEXT:",
        f"- sector: {client_context.get('sector')}",
        f"- ens_category: {client_context.get('ens_category')}",
        f"- size: {client_context.get('size', 'PYME')}",
        "",
        f"GAPS DETECTADOS (total {len(gaps)}):",
    ]
    for g in gaps[:30]:
        lines.append(
            f"- id={g.get('id', '?')} "
            f"medida_afectada={g.get('medida_afectada', '?')} "
            f"severidad={g.get('severidad', '?')}"
        )
        desc = g.get("descripcion", "")
        if desc:
            lines.append(f"  descripcion: {desc[:200]}")
    lines.append("")
    lines.append(
        "Devuelve SOLO JSON con 2 claves obligatorias (prioritized_gaps, "
        "summary). Sin markdown, sin backticks."
    )
    return "\n".join(lines)


def _validate_output(
    parsed: dict[str, Any],
    input_gap_ids: set[str],
    input_gap_codes: set[str],
) -> list[str]:
    errs: list[str] = []
    if "prioritized_gaps" not in parsed:
        errs.append("falta 'prioritized_gaps'")
    if "summary" not in parsed:
        errs.append("falta 'summary'")
    if errs:
        return errs

    pg = parsed["prioritized_gaps"]
    if not isinstance(pg, list):
        errs.append("prioritized_gaps no lista")
        return errs

    seen_ranks: set[int] = set()
    for i, g in enumerate(pg):
        if not isinstance(g, dict):
            errs.append(f"prioritized_gaps[{i}] no dict")
            continue
        for fld in (
            "gap_id", "medida_afectada", "priority_rank",
            "priority_rationale", "estimated_effort_days",
            "business_impact", "is_quick_win",
        ):
            if fld not in g:
                errs.append(f"prioritized_gaps[{i}] falta '{fld}'")

        # gap_id debe existir en input (no inventar nuevos)
        gap_id = str(g.get("gap_id", ""))
        if gap_id and gap_id not in input_gap_ids:
            errs.append(
                f"prioritized_gaps[{i}].gap_id '{gap_id}' no esta en input"
            )

        # medida_afectada debe venir del input (NO inventar)
        medida = str(g.get("medida_afectada", ""))
        if medida and medida not in input_gap_codes:
            errs.append(
                f"prioritized_gaps[{i}].medida_afectada '{medida}' no esta en input"
            )

        # priority_rank unico
        try:
            rank = int(g.get("priority_rank", -1))
            if rank < 1:
                errs.append(
                    f"prioritized_gaps[{i}].priority_rank < 1: {rank}"
                )
            if rank in seen_ranks:
                errs.append(f"priority_rank duplicado: {rank}")
            seen_ranks.add(rank)
        except (TypeError, ValueError):
            errs.append(
                f"prioritized_gaps[{i}].priority_rank no entero"
            )

        # effort en rango
        try:
            eff = int(g.get("estimated_effort_days", -1))
            if not (0 < eff <= 60):
                errs.append(
                    f"prioritized_gaps[{i}].estimated_effort_days fuera (0,60]: {eff}"
                )
        except (TypeError, ValueError):
            errs.append(
                f"prioritized_gaps[{i}].estimated_effort_days no entero"
            )

        if g.get("business_impact") not in _VALID_IMPACTS:
            errs.append(
                f"prioritized_gaps[{i}].business_impact invalido: "
                f"{g.get('business_impact')!r}"
            )

        if not isinstance(g.get("is_quick_win"), bool):
            errs.append(f"prioritized_gaps[{i}].is_quick_win no bool")

        rationale = g.get("priority_rationale", "")
        if not isinstance(rationale, str) or len(rationale) > 250:
            errs.append(
                f"prioritized_gaps[{i}].priority_rationale invalido o >250 chars"
            )

    # Verificar cobertura: todos los gap_ids del input deben aparecer
    output_ids = {str(g.get("gap_id", "")) for g in pg if isinstance(g, dict)}
    missing = input_gap_ids - output_ids
    if missing:
        errs.append(
            f"prioritized_gaps no cubre todos los gaps del input: "
            f"faltan {sorted(missing)[:5]}"
        )

    return errs


def _deterministic_fallback(
    gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Fallback sin LLM: orden por severidad determinista."""
    # Vocabulario canónico de severidad (get_severidad_for_categoria / catálogo):
    # critica/alta/media/baja/informativa. El anterior (mayor/menor/info) NUNCA
    # casaba → todos los gaps caían al default 99 (sin orden real) y el impacto
    # quedaba mal clasificado.
    sev_order = {"critica": 0, "alta": 1, "media": 2, "baja": 3, "informativa": 4}
    sorted_gaps = sorted(
        gaps,
        key=lambda g: sev_order.get(
            str(g.get("severidad", "")).lower(), 99,
        ),
    )
    pg: list[dict[str, Any]] = []
    quick_wins = 0
    alto = 0
    total_effort = 0
    for i, g in enumerate(sorted_gaps):
        sev = str(g.get("severidad", "")).lower()
        impact = (
            "alto" if sev in ("critica", "alta")
            else "medio" if sev == "media"
            else "bajo"
        )
        effort = 5 if sev in ("critica", "alta") else 3
        is_qw = sev in ("baja", "informativa") and effort <= 3
        total_effort += effort
        if is_qw:
            quick_wins += 1
        if impact == "alto":
            alto += 1
        pg.append({
            "gap_id": str(g.get("id", f"g{i}")),
            "medida_afectada": str(g.get("medida_afectada", "")),
            "priority_rank": i + 1,
            "priority_rationale": (
                f"Fallback determinista por severidad {sev}. "
                "Revisar manualmente."
            )[:200],
            "estimated_effort_days": effort,
            "business_impact": impact,
            "is_quick_win": is_qw,
        })
    return {
        "prioritized_gaps": pg,
        "summary": {
            "total_gaps": len(pg),
            "quick_wins_count": quick_wins,
            "alto_impacto_count": alto,
            "esfuerzo_total_dias": total_effort,
        },
    }


async def prioritize_gaps_with_llm(
    *,
    gaps: list[dict[str, Any]],
    client_context: dict[str, Any],
) -> dict[str, Any]:
    """Prioriza gaps con LLM Sonnet 4.6 + caching.

    Args:
        gaps: lista de dicts con 'id', 'medida_afectada', 'severidad',
            'descripcion'. Se recomienda pasar <=30 gaps (se trunca).
        client_context: {'sector', 'ens_category', 'size'}.

    Returns:
        Dict con 'prioritized' (lista ordenada), 'summary' (agregados),
        y metadatos LLM (tokens, coste, cached, fallback_used).
    """
    # Validacion input
    sector = client_context.get("sector")
    if sector not in _VALID_SECTORS:
        raise ValueError(f"client_context.sector invalido: {sector!r}")
    cat = client_context.get("ens_category")
    if cat not in _VALID_CATEGORIES:
        raise ValueError(f"client_context.ens_category invalida: {cat!r}")

    if not gaps:
        return {
            "prioritized": [],
            "summary": {
                "total_gaps": 0, "quick_wins_count": 0,
                "alto_impacto_count": 0, "esfuerzo_total_dias": 0,
            },
            "fallback_used": False,
            "tokens_input": 0, "tokens_output": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "cost_eur_estimated": 0.0,
            "retry_count": 0,
            "model": _MODEL,
        }

    # Sin API key -> fallback directo
    if not get_settings().anthropic_api_key.get_secret_value().strip():
        logger.info("M4 LLM prioritizer: sin API key, usando fallback determinista")
        fb = _deterministic_fallback(gaps)
        return {
            **fb,
            "prioritized": fb["prioritized_gaps"],
            "fallback_used": True,
            "tokens_input": 0, "tokens_output": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "cost_eur_estimated": 0.0,
            "retry_count": 0,
            "model": "fallback",
        }

    input_gap_ids = {str(g.get("id", "")) for g in gaps}
    input_gap_codes = {str(g.get("medida_afectada", "")) for g in gaps}
    user_msg = _build_user_message(gaps, client_context)

    last_errors: list[str] = []
    last_response_meta: dict[str, Any] = {}
    retry_count = 0

    for attempt in range(2):  # primer intento + 1 retry
        msg = user_msg
        if attempt > 0 and last_errors:
            msg = user_msg + (
                "\n\nRECORDATORIO TRAS REINTENTO: errores: "
                + "; ".join(last_errors[:5])
                + ". Corrige y responde solo JSON valido."
            )

        try:
            from backend.app.core.ai.llm_router import get_default_llm_router
            router = get_default_llm_router()
            messages = [
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": msg},
            ]
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: router.complete(
                    messages=messages,
                    model="claude-sonnet-4-6",
                    max_tokens=_MAX_TOKENS,
                    temperature=_TEMPERATURE,
                    enable_prompt_caching=True,
                ),
            )
            last_response_meta = {
                "tokens_input": resp.prompt_tokens,
                "tokens_output": resp.completion_tokens,
                "cache_creation_input_tokens": resp.cache_creation_input_tokens,
                "cache_read_input_tokens": resp.cache_read_input_tokens,
                "model": resp.model,
                "latency_ms": resp.latency_ms,
            }

            # Parse JSON (strip fences defensivo)
            text = resp.content.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            parsed = json.loads(text.strip())
        except (json.JSONDecodeError, ValueError) as exc:
            last_errors = [f"JSON parse: {exc}"]
            retry_count = attempt + 1
            continue
        except Exception as exc:
            logger.warning(
                "M4 LLM prioritizer: error router (%s), fallback", exc,
            )
            fb = _deterministic_fallback(gaps)
            return {
                **fb, "prioritized": fb["prioritized_gaps"],
                "fallback_used": True,
                "tokens_input": 0, "tokens_output": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "cost_eur_estimated": 0.0,
                "retry_count": retry_count, "model": "fallback",
            }

        errors = _validate_output(parsed, input_gap_ids, input_gap_codes)
        if not errors:
            # Exito
            ti = last_response_meta["tokens_input"]
            to = last_response_meta["tokens_output"]
            cw = last_response_meta["cache_creation_input_tokens"]
            cr = last_response_meta["cache_read_input_tokens"]
            cost = (
                (ti / 1_000_000) * _SONNET_46_USD_IN
                + (cw / 1_000_000) * _SONNET_46_USD_CACHE_WRITE
                + (cr / 1_000_000) * _SONNET_46_USD_CACHE_READ
                + (to / 1_000_000) * _SONNET_46_USD_OUT
            ) * _USD_TO_EUR
            return {
                "prioritized": parsed["prioritized_gaps"],
                "summary": parsed["summary"],
                "fallback_used": False,
                "tokens_input": ti,
                "tokens_output": to,
                "cache_creation_input_tokens": cw,
                "cache_read_input_tokens": cr,
                "cost_eur_estimated": round(cost, 5),
                "retry_count": attempt,
                "model": last_response_meta["model"],
                "latency_ms": last_response_meta["latency_ms"],
            }
        last_errors = errors
        retry_count = attempt + 1

    # Agotados retries -> fallback
    logger.warning(
        "M4 LLM prioritizer agoto reintentos (%d errores finales), fallback",
        len(last_errors),
    )
    fb = _deterministic_fallback(gaps)
    ti = last_response_meta.get("tokens_input", 0)
    to = last_response_meta.get("tokens_output", 0)
    cw = last_response_meta.get("cache_creation_input_tokens", 0)
    cr = last_response_meta.get("cache_read_input_tokens", 0)
    cost = (
        (ti / 1_000_000) * _SONNET_46_USD_IN
        + (cw / 1_000_000) * _SONNET_46_USD_CACHE_WRITE
        + (cr / 1_000_000) * _SONNET_46_USD_CACHE_READ
        + (to / 1_000_000) * _SONNET_46_USD_OUT
    ) * _USD_TO_EUR
    return {
        **fb,
        "prioritized": fb["prioritized_gaps"],
        "fallback_used": True,
        "tokens_input": ti, "tokens_output": to,
        "cache_creation_input_tokens": cw,
        "cache_read_input_tokens": cr,
        "cost_eur_estimated": round(cost, 5),
        "retry_count": retry_count,
        "model": last_response_meta.get("model", "fallback"),
        "schema_errors": last_errors[:5],
    }
