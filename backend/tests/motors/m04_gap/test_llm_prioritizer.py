"""Tests M4 LLM prioritizer (Sesion 9 Paso 3.3).

Cubre:
- Fallback determinista sin API key (orden por severidad).
- Fallback sin gaps (lista vacia).
- Validator output: gap_id desconocido rechazado, medida_afectada
  inventada rechazada, priority_rank duplicado rechazado.
- 2 tests @llm reales: sanidad MEDIA + AAPP BASICA.
- 1 test @llm caching.
"""
from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

load_dotenv()

from backend.app.motors.m04_gap.llm_prioritizer import (
    _deterministic_fallback,
    _validate_output,
    prioritize_gaps_with_llm,
)


def _skip_if_no_api_key() -> None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        pytest.skip("ANTHROPIC_API_KEY no configurado - test LLM saltado")


SANIDAD_CTX = {"sector": "sanidad", "ens_category": "MEDIA", "size": "PYME"}
AAPP_CTX = {"sector": "aapp", "ens_category": "BASICA", "size": "PYME"}


def _make_gaps(n: int = 3) -> list[dict]:
    """Gaps sinteticos con severidad variada."""
    return [
        {
            "id": "g1",
            "medida_afectada": "mp.info.3",
            "severidad": "critica",
            "descripcion": "HCE sin cifrado en reposo",
        },
        {
            "id": "g2",
            "medida_afectada": "mp.per.1",
            "severidad": "baja",
            "descripcion": "Sin formacion anual documentada",
        },
        {
            "id": "g3",
            "medida_afectada": "org.1",
            "severidad": "alta",
            "descripcion": "Sin politica seguridad aprobada formalmente",
        },
    ][:n]


# =======================================================================
# 1) Input validation
# =======================================================================


async def test_prioritize_invalid_sector_raises():
    with pytest.raises(ValueError, match="sector invalido"):
        await prioritize_gaps_with_llm(
            gaps=_make_gaps(),
            client_context={"sector": "espacio", "ens_category": "MEDIA"},
        )


async def test_prioritize_invalid_category_raises():
    with pytest.raises(ValueError, match="ens_category invalida"):
        await prioritize_gaps_with_llm(
            gaps=_make_gaps(),
            client_context={"sector": "sanidad", "ens_category": "MEGA"},
        )


# =======================================================================
# 2) Empty gaps -> returns empty result sin LLM
# =======================================================================


async def test_prioritize_empty_gaps():
    result = await prioritize_gaps_with_llm(
        gaps=[], client_context=SANIDAD_CTX,
    )
    assert result["prioritized"] == []
    assert result["summary"]["total_gaps"] == 0
    assert result["tokens_input"] == 0
    assert result["cost_eur_estimated"] == 0.0
    assert result["fallback_used"] is False


# =======================================================================
# 3) Fallback determinista cuando no hay API key
# =======================================================================


async def test_prioritize_fallback_without_api_key(patched_settings):
    patched_settings(anthropic_api_key="")
    result = await prioritize_gaps_with_llm(
        gaps=_make_gaps(),
        client_context=SANIDAD_CTX,
    )
    assert result["fallback_used"] is True
    assert result["model"] == "fallback"
    # Orden por severidad: critica > alta > baja (vocab canónico catálogo)
    pg = result["prioritized"]
    assert pg[0]["gap_id"] == "g1"   # critica mp.info.3
    assert pg[1]["gap_id"] == "g3"   # alta org.1
    assert pg[2]["gap_id"] == "g2"   # baja mp.per.1
    # Rank consecutivo
    assert [p["priority_rank"] for p in pg] == [1, 2, 3]


# =======================================================================
# 4) _deterministic_fallback directo
# =======================================================================


def test_deterministic_fallback_identifies_quick_wins():
    """Severidad 'baja' + effort 3 -> quick_win=True (vocab canónico catálogo)."""
    gaps = [
        {"id": "g1", "medida_afectada": "org.2", "severidad": "baja"},
    ]
    fb = _deterministic_fallback(gaps)
    assert fb["prioritized_gaps"][0]["is_quick_win"] is True


def test_deterministic_fallback_critica_not_quick_win():
    gaps = [
        {"id": "g1", "medida_afectada": "mp.info.3", "severidad": "critica"},
    ]
    fb = _deterministic_fallback(gaps)
    assert fb["prioritized_gaps"][0]["is_quick_win"] is False
    assert fb["prioritized_gaps"][0]["business_impact"] == "alto"


def test_deterministic_fallback_summary_counts():
    gaps = _make_gaps()
    fb = _deterministic_fallback(gaps)
    s = fb["summary"]
    assert s["total_gaps"] == 3
    # g1 critica (alto), g3 alta (alto) = 2 alto_impacto
    assert s["alto_impacto_count"] == 2
    # g2 baja 3d -> quick win
    assert s["quick_wins_count"] == 1


# =======================================================================
# 5) Output validator - rechazos
# =======================================================================


def test_validate_rejects_unknown_gap_id():
    parsed = {
        "prioritized_gaps": [
            {
                "gap_id": "ghost_id",
                "medida_afectada": "mp.info.3",
                "priority_rank": 1,
                "priority_rationale": "x",
                "estimated_effort_days": 5,
                "business_impact": "alto",
                "is_quick_win": False,
            },
        ],
        "summary": {},
    }
    errors = _validate_output(parsed, {"g1"}, {"mp.info.3"})
    assert any("gap_id 'ghost_id' no esta en input" in e for e in errors)


def test_validate_rejects_invented_medida():
    parsed = {
        "prioritized_gaps": [
            {
                "gap_id": "g1",
                "medida_afectada": "fake.medida.99",
                "priority_rank": 1,
                "priority_rationale": "x",
                "estimated_effort_days": 5,
                "business_impact": "alto",
                "is_quick_win": False,
            },
        ],
        "summary": {},
    }
    errors = _validate_output(parsed, {"g1"}, {"mp.info.3"})
    assert any("fake.medida.99" in e for e in errors)


def test_validate_rejects_duplicate_rank():
    parsed = {
        "prioritized_gaps": [
            {
                "gap_id": "g1", "medida_afectada": "mp.info.3",
                "priority_rank": 1, "priority_rationale": "x",
                "estimated_effort_days": 5, "business_impact": "alto",
                "is_quick_win": False,
            },
            {
                "gap_id": "g2", "medida_afectada": "org.1",
                "priority_rank": 1, "priority_rationale": "y",
                "estimated_effort_days": 3, "business_impact": "medio",
                "is_quick_win": True,
            },
        ],
        "summary": {},
    }
    errors = _validate_output(
        parsed, {"g1", "g2"}, {"mp.info.3", "org.1"},
    )
    assert any("priority_rank duplicado" in e for e in errors)


def test_validate_rejects_missing_gap_coverage():
    """Si el input tiene g1 y g2 pero output solo g1, rechazo."""
    parsed = {
        "prioritized_gaps": [
            {
                "gap_id": "g1", "medida_afectada": "mp.info.3",
                "priority_rank": 1, "priority_rationale": "x",
                "estimated_effort_days": 5, "business_impact": "alto",
                "is_quick_win": False,
            },
        ],
        "summary": {},
    }
    errors = _validate_output(
        parsed, {"g1", "g2"}, {"mp.info.3", "org.1"},
    )
    assert any("no cubre todos los gaps" in e for e in errors)


def test_validate_rejects_invalid_impact():
    parsed = {
        "prioritized_gaps": [
            {
                "gap_id": "g1", "medida_afectada": "mp.info.3",
                "priority_rank": 1, "priority_rationale": "x",
                "estimated_effort_days": 5, "business_impact": "fatal",
                "is_quick_win": False,
            },
        ],
        "summary": {},
    }
    errors = _validate_output(parsed, {"g1"}, {"mp.info.3"})
    assert any("business_impact invalido" in e for e in errors)


# =======================================================================
# 6) LLM real - sanidad MEDIA
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(300)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_prioritize_sanidad_media_real_llm():
    _skip_if_no_api_key()
    result = await prioritize_gaps_with_llm(
        gaps=_make_gaps(), client_context=SANIDAD_CTX,
    )
    assert result["fallback_used"] is False, (
        f"Fallback; errors={result.get('schema_errors', [])[:3]}"
    )
    pg = result["prioritized"]
    assert len(pg) == 3
    # g1 mp.info.3 critica datos salud -> rank 1 esperado (muy alta prob.)
    assert pg[0]["gap_id"] == "g1"
    # Todos con business_impact valido
    for p in pg:
        assert p["business_impact"] in {"alto", "medio", "bajo"}


# =======================================================================
# 7) LLM real - AAPP BASICA con 2 gaps
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(300)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_prioritize_aapp_basica_real_llm():
    _skip_if_no_api_key()
    gaps = [
        {
            "id": "g10", "medida_afectada": "org.2",
            "severidad": "mayor",
            "descripcion": "Sin RSEG designado formalmente",
        },
        {
            "id": "g11", "medida_afectada": "mp.s.1",
            "severidad": "menor",
            "descripcion": "Perimetral sin IDS",
        },
    ]
    result = await prioritize_gaps_with_llm(
        gaps=gaps, client_context=AAPP_CTX,
    )
    assert result["fallback_used"] is False
    pg = result["prioritized"]
    assert len(pg) == 2
    # org.2 designar RSEG es quick win tipico AAPP
    g10 = next(p for p in pg if p["gap_id"] == "g10")
    assert g10["is_quick_win"] is True or g10["priority_rank"] == 1


# =======================================================================
# 8) LLM real - coste bajo (caching opt-in, no garantizado con prompt
#    ~1261 tokens justo encima del umbral 1024 de Sonnet 4.6)
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(180)
async def test_prioritize_low_cost_per_run():
    """Verifica coste por run razonable. El caching es opt-in pero el
    prompt es pequeno (~1261 tokens) y esta justo encima del threshold
    minimo de Sonnet 4.6 (1024 tokens); puede no cachear de forma fiable.
    El test verifica funcionalidad + coste sin exigir cache_read > 0.
    """
    _skip_if_no_api_key()
    gaps = _make_gaps()
    first = await prioritize_gaps_with_llm(
        gaps=gaps, client_context=SANIDAD_CTX,
    )
    second = await prioritize_gaps_with_llm(
        gaps=gaps, client_context=SANIDAD_CTX,
    )
    assert first["fallback_used"] is False
    assert second["fallback_used"] is False
    # Coste individual bajo: 1261 tokens input + ~400 output Sonnet
    # ~0.009 EUR sin cache; con cache ~0.004 EUR. Tope 0.030 EUR holgado.
    assert first["cost_eur_estimated"] < 0.030
    assert second["cost_eur_estimated"] < 0.030
    # Determinismo semantico a T=0.2: misma prioritario primero
    p1_first = first["prioritized"][0]["gap_id"]
    p1_second = second["prioritized"][0]["gap_id"]
    assert p1_first == p1_second
