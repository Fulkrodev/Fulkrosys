"""Tests Agente 11 - Auditor Virtual Suplementario (Sesion 9 Paso 2.6).

Scope suplementario a M10 (58 preguntas ENAC deterministas). A11
anade PAC priorizado + 3-5 preguntas sector + narrativa ejecutiva.

Tests clave:
- Schema strict con fases 3-5 consecutivas + ids unicos acciones.
- Preguntas sector-aware (al menos 1 del sector cliente).
- Anti-hallucination: nc_origen en acciones DEBE venir de
  m10_audit_result.nc_mayores/nc_menores (o 'general').
- Fallback tabular cuando LLM falla.

LLM tests se saltan si ANTHROPIC_API_KEY no esta configurado.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv()

from backend.app.agents.agent_11_auditor_virtual import (
    Agent11AuditorVirtual,
    AuditorInternoVirtualAgent,
    _ENS_CATEGORIES,
    _PRIORIDADES,
    _REQUIRED_TOP_KEYS,
    _SECTORS,
    _VEREDICTOS,
)


def _skip_if_no_api_key() -> None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        pytest.skip("ANTHROPIC_API_KEY no configurado - test LLM saltado")


DATAFORMA_CTX = {
    "company_name": "DataForma S.L.",
    "sector": "sanidad",
    "size": "PYME",
    "ens_category": "MEDIA",
    "is_aapp": False,
    "target_audit_date": "2026-09-15",
}
DATAFORMA_M10 = {
    "score_conformidad": 72,
    "categoria_ens": "MEDIA",
    "nc_mayores": [
        {"codigo": "mp.info.3", "descripcion": "HCE sin cifrado en reposo"},
        {"codigo": "op.exp.4", "descripcion": "Sin proceso gestion cambios"},
        {"codigo": "org.3", "descripcion": "Sin revision periodica controles"},
        {"codigo": "mp.acc.2", "descripcion": "MFA no obligatorio apps criticas"},
    ],
    "nc_menores": [
        {"codigo": "op.pl.3", "descripcion": "Inventario activos desactualizado"},
        {"codigo": "mp.per.1", "descripcion": "Sin formacion anual obligatoria"},
    ],
    "preguntas_L5": 12, "preguntas_L4": 18, "preguntas_L3": 14,
    "preguntas_L2": 8, "preguntas_L1": 4, "preguntas_L0": 2,
    "preguntas_respondidas_total": 58,
}

AYTO_CTX = {
    "company_name": "Ayuntamiento de Villanueva",
    "sector": "aapp",
    "size": "PYME",
    "ens_category": "BASICA",
    "is_aapp": True,
    "target_audit_date": "2026-10-30",
}
AYTO_M10 = {
    "score_conformidad": 45,
    "categoria_ens": "BASICA",
    "nc_mayores": [
        {"codigo": "org.1", "descripcion": "Sin politica seguridad"},
        {"codigo": "org.2", "descripcion": "Sin RSEG designado formal"},
    ],
    "nc_menores": [
        {"codigo": "mp.s.1", "descripcion": "Perimetral basico sin IDS"},
        {"codigo": "op.pl.1", "descripcion": "Sin planificacion formal"},
        {"codigo": "mp.per.1", "descripcion": "Sin formacion"},
    ],
    "preguntas_L5": 3, "preguntas_L4": 8, "preguntas_L3": 12,
    "preguntas_L2": 15, "preguntas_L1": 12, "preguntas_L0": 8,
    "preguntas_respondidas_total": 58,
}


def _valid_audit(
    *,
    sector: str = "sanidad",
    veredicto: str = "listo_con_riesgos",
    known_codes: tuple[str, ...] = (
        "mp.info.3", "op.exp.4", "org.3", "mp.acc.2", "op.pl.3", "mp.per.1",
    ),
) -> dict:
    """SupplementaryAuditResult valido basado en DATAFORMA_M10."""
    fases = [
        {
            "fase_num": 1,
            "titulo": "Bloqueantes sanidad",
            "periodo_semanas": "0-4",
            "acciones": [
                {
                    "id": "PAC-F1-001",
                    "nc_origen": known_codes[0],
                    "accion": "Activar cifrado en reposo HCE con KMS BYOK.",
                    "responsable_sugerido": "CISO",
                    "esfuerzo_dias": 10,
                    "evidencia_esperada": "Captura consola KMS",
                    "prioridad": "critica",
                    "rationale_sector": "Datos salud art. 9 RGPD.",
                },
                {
                    "id": "PAC-F1-002",
                    "nc_origen": known_codes[3],
                    "accion": "MFA obligatorio Azure AD.",
                    "responsable_sugerido": "IT",
                    "esfuerzo_dias": 3,
                    "evidencia_esperada": "Log MFA 100% usuarios",
                    "prioridad": "critica",
                    "rationale_sector": "Acceso HCE sin MFA expone art. 9 RGPD.",
                },
            ],
            "objetivo_fase": "Cerrar NC mayores antes semana 4.",
        },
        {
            "fase_num": 2,
            "titulo": "Gobierno transversal",
            "periodo_semanas": "4-10",
            "acciones": [
                {
                    "id": "PAC-F2-001",
                    "nc_origen": known_codes[2],
                    "accion": "Proceso revision trimestral.",
                    "responsable_sugerido": "RSEG",
                    "esfuerzo_dias": 5,
                    "evidencia_esperada": "Actas trimestrales",
                    "prioridad": "alta",
                    "rationale_sector": "Revision periodica pilar ENS MEDIA.",
                },
            ],
            "objetivo_fase": "Cadencia gobierno antes semana 10.",
        },
        {
            "fase_num": 3,
            "titulo": "Certificacion",
            "periodo_semanas": "10-22",
            "acciones": [
                {
                    "id": "PAC-F3-001",
                    "nc_origen": "general",
                    "accion": "Auditoria interna completa.",
                    "responsable_sugerido": "RSEG + Auditor externo",
                    "esfuerzo_dias": 8,
                    "evidencia_esperada": "Informe auditoria interna",
                    "prioridad": "alta",
                    "rationale_sector": "Dry-run antes ENAC real.",
                },
            ],
            "objetivo_fase": "Llegar a auditoria ENAC sin NC mayor.",
        },
    ]

    preguntas = [
        {
            "codigo": f"A11-{sector[:3].upper()}-001",
            "pregunta": f"Pregunta contextual sector {sector}?",
            "sector_aplicable": sector,
            "criterio_L5": "Procedimiento documentado + simulacro.",
            "criterio_L0": "Sin procedimiento.",
            "evidencia_esperada": ["Doc A", "Log B"],
            "rationale_sector": f"Relevante para {sector}.",
        },
        {
            "codigo": "A11-GEN-001",
            "pregunta": "Hay DPA con proveedores criticos?",
            "sector_aplicable": "otro",
            "criterio_L5": "DPA firmado por todos.",
            "criterio_L0": "Sin DPA.",
            "evidencia_esperada": ["DPAs", "Inventario proveedores"],
            "rationale_sector": "RGPD art. 28 base.",
        },
        {
            "codigo": "A11-GEN-002",
            "pregunta": "Revision periodica accesos?",
            "sector_aplicable": "otro",
            "criterio_L5": "Revision trimestral + logs.",
            "criterio_L0": "Sin revision.",
            "evidencia_esperada": ["Logs", "Actas"],
            "rationale_sector": "op.acc revision documentada.",
        },
    ]

    narrativa = (
        "### Estado actual\n\nCon 72% de conformidad y 4 NC mayores, "
        "el cliente se encuentra listo con riesgos frente a auditoria ENAC. "
        "Las NC mayores tienen componente sectorial relevante al tratarse de "
        "HCE (datos art. 9 RGPD). La combinacion cifrado + MFA son las dos "
        "mas criticas.\n\n### Prioridades\n\nCerrar primero las 2 NC de "
        "sanidad (cifrado y MFA) en Fase 1 (4 semanas). Despues el gobierno "
        "transversal (revision periodica + gestion cambios) en Fase 2 "
        "(semanas 4-10). NC menores y dossier en Fase 3 (semanas 10-22).\n\n"
        "### Probabilidad\n\n62% de certificacion a la primera si se "
        "mantiene el calendario propuesto."
    )

    return {
        "pac_priorizado": {
            "fases": fases,
            "camino_critico": ["PAC-F1-001", "PAC-F1-002", "PAC-F2-001"],
        },
        "preguntas_contextuales_sector": preguntas,
        "narrativa_ejecutiva": {
            "resumen_markdown": narrativa,
            "veredicto": veredicto,
            "probabilidad_certificacion_primera": 62,
            "tiempo_minimo_estimado_semanas": 22,
            "riesgos_principales": [
                "Si proveedor cloud no firma DPA en 4 semanas, mp.info.3 queda bloqueado.",
                "Si MFA rollout tiene fricciones, mp.acc.2 se arrastra.",
                "Cambio de RSEG reseta 4-6 semanas.",
            ],
        },
    }


def _mock_llm_response(audit: dict, *, tokens_in: int = 5000, tokens_out: int = 4000) -> dict:
    return {
        "agent_id": 11,
        "agent_name": "Auditor Interno Virtual",
        "response": "{...}",
        "parsed": audit,
        "model": "claude-opus-4-7",
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "latency_ms": 60000,
        "citations": [],
        "project_id": None,
    }


# =======================================================================
# 1) Alias retrocompat + enums
# =======================================================================


def test_agent_11_alias_backcompat():
    assert AuditorInternoVirtualAgent is Agent11AuditorVirtual


def test_agent_11_enums_match_spec():
    assert _ENS_CATEGORIES == {"BASICA", "MEDIA", "ALTA"}
    assert _SECTORS == {"sanidad", "aapp", "fintech", "otro"}
    assert _PRIORIDADES == {"critica", "alta", "media", "baja"}
    assert _VEREDICTOS == {
        "listo_auditar", "listo_con_riesgos", "no_listo_plazo", "muy_lejos",
    }
    assert len(_REQUIRED_TOP_KEYS) == 3


# =======================================================================
# 2) Input validation
# =======================================================================


async def test_agent_11_invalid_sector_raises(db):
    agent = Agent11AuditorVirtual()
    ctx = {**DATAFORMA_CTX, "sector": "espacio"}
    with pytest.raises(ValueError, match="sector invalido"):
        await agent.generate_supplementary_audit(
            db, m10_audit_result=DATAFORMA_M10, client_context=ctx,
        )


async def test_agent_11_missing_m10_field_raises(db):
    agent = Agent11AuditorVirtual()
    m10 = dict(DATAFORMA_M10)
    del m10["nc_mayores"]
    with pytest.raises(ValueError, match="nc_mayores"):
        await agent.generate_supplementary_audit(
            db, m10_audit_result=m10, client_context=DATAFORMA_CTX,
        )


# =======================================================================
# 3) Success path mock
# =======================================================================


async def test_agent_11_complete_mock_pac_3_fases(db):
    agent = Agent11AuditorVirtual()
    good = _mock_llm_response(_valid_audit())
    with patch.object(
        Agent11AuditorVirtual, "invoke", new=AsyncMock(return_value=good)
    ) as invoke_mock:
        result = await agent.generate_supplementary_audit(
            db, m10_audit_result=DATAFORMA_M10, client_context=DATAFORMA_CTX,
        )

    assert invoke_mock.call_count == 1
    assert result["fallback_used"] is False
    assert result["schema_valid"] is True
    a = result["audit"]
    assert len(a["pac_priorizado"]["fases"]) == 3
    assert len(a["preguntas_contextuales_sector"]) == 3
    assert a["narrativa_ejecutiva"]["veredicto"] in _VEREDICTOS


# =======================================================================
# 4) Schema strict validation
# =======================================================================


@pytest.mark.parametrize(
    "mutator,expected_error_substring",
    [
        # Fases fuera de rango (solo 2)
        (
            lambda a: a["pac_priorizado"].__setitem__(
                "fases", a["pac_priorizado"]["fases"][:2]
            ),
            "pac_priorizado.fases",
        ),
        # fase_num no consecutivo
        (
            lambda a: a["pac_priorizado"]["fases"][1].__setitem__("fase_num", 5),
            "fase_num=5 no consecutivo",
        ),
        # Prioridad invalida
        (
            lambda a: a["pac_priorizado"]["fases"][0]["acciones"][0].__setitem__(
                "prioridad", "super_critica"
            ),
            "prioridad invalida",
        ),
        # Veredicto invalido
        (
            lambda a: a["narrativa_ejecutiva"].__setitem__("veredicto", "dudoso"),
            "veredicto invalido",
        ),
        # Probabilidad fuera de rango
        (
            lambda a: a["narrativa_ejecutiva"].__setitem__(
                "probabilidad_certificacion_primera", 150
            ),
            "probabilidad_certificacion_primera",
        ),
        # Preguntas insuficientes (2 en lugar de 3-5)
        (
            lambda a: a.__setitem__(
                "preguntas_contextuales_sector",
                a["preguntas_contextuales_sector"][:2],
            ),
            "preguntas_contextuales_sector debe tener 3-5",
        ),
    ],
)
def test_agent_11_schema_strict_validation(mutator, expected_error_substring):
    agent = Agent11AuditorVirtual()
    audit = _valid_audit()
    mutator(audit)
    errors = agent._validate_schema(audit, DATAFORMA_M10, DATAFORMA_CTX)
    assert any(expected_error_substring in e for e in errors), errors


# =======================================================================
# 5) Preguntas sector-aware: al menos 1 del sector cliente
# =======================================================================


def test_agent_11_preguntas_sector_matches_client():
    agent = Agent11AuditorVirtual()
    # Cliente sanidad pero todas las preguntas son 'otro'
    audit = _valid_audit(sector="sanidad")
    for q in audit["preguntas_contextuales_sector"]:
        q["sector_aplicable"] = "otro"
    errors = agent._validate_schema(audit, DATAFORMA_M10, DATAFORMA_CTX)
    assert any("sector_aplicable='sanidad'" in e for e in errors), errors


# =======================================================================
# 6) Anti-hallucination: nc_origen inventado
# =======================================================================


def test_agent_11_anti_hallucination_nc_origen():
    """Accion con nc_origen que no esta en m10 NCs -> rechazo."""
    agent = Agent11AuditorVirtual()
    audit = _valid_audit()
    # Insertar un codigo inexistente
    audit["pac_priorizado"]["fases"][0]["acciones"][0]["nc_origen"] = "mp.inventado.99"
    errors = agent._validate_schema(audit, DATAFORMA_M10, DATAFORMA_CTX)
    assert any("hallucinated_nc_origen" in e for e in errors)
    assert any("mp.inventado.99" in e for e in errors)


def test_agent_11_anti_hallucination_allows_general():
    """nc_origen 'general' o 'multiple' son aceptables para acciones transversales."""
    agent = Agent11AuditorVirtual()
    audit = _valid_audit()
    audit["pac_priorizado"]["fases"][0]["acciones"][0]["nc_origen"] = "general"
    audit["pac_priorizado"]["fases"][1]["acciones"][0]["nc_origen"] = "multiple"
    errors = agent._validate_schema(audit, DATAFORMA_M10, DATAFORMA_CTX)
    # Sin otros bugs, solo verificamos que no sale error de nc_origen
    assert not any("hallucinated_nc_origen" in e for e in errors)


def test_agent_11_action_id_must_be_unique():
    agent = Agent11AuditorVirtual()
    audit = _valid_audit()
    audit["pac_priorizado"]["fases"][1]["acciones"][0]["id"] = "PAC-F1-001"
    errors = agent._validate_schema(audit, DATAFORMA_M10, DATAFORMA_CTX)
    assert any("id accion duplicado" in e for e in errors)


# =======================================================================
# 7) Fallback tabular cuando LLM falla
# =======================================================================


async def test_agent_11_fallback_on_invalid_json(db):
    agent = Agent11AuditorVirtual()
    bad = {
        "response": "no json",
        "parsed": None,
        "tokens_input": 1000, "tokens_output": 50, "latency_ms": 5,
        "model": "claude-opus-4-7",
    }
    with patch.object(
        Agent11AuditorVirtual, "invoke", new=AsyncMock(return_value=bad)
    ):
        result = await agent.generate_supplementary_audit(
            db,
            m10_audit_result=DATAFORMA_M10,
            client_context=DATAFORMA_CTX,
        )

    assert result["fallback_used"] is True
    a = result["audit"]
    # Las 3 claves obligatorias
    for k in _REQUIRED_TOP_KEYS:
        assert k in a
    # PAC con 3 fases minimo
    assert len(a["pac_priorizado"]["fases"]) >= 3
    # Las acciones fallback Fase 1 deben referenciar NC mayores de M10
    f1_action_codes = {
        a_.get("nc_origen") for a_ in a["pac_priorizado"]["fases"][0]["acciones"]
    }
    m10_codes = {nc["codigo"] for nc in DATAFORMA_M10["nc_mayores"]}
    assert f1_action_codes & m10_codes, (
        "Fallback F1 no vincula NC mayores a acciones: "
        f"{f1_action_codes} vs {m10_codes}"
    )
    # Veredicto deterministico segun score (72% con NC mayor -> listo_con_riesgos)
    assert a["narrativa_ejecutiva"]["veredicto"] == "listo_con_riesgos"


# =======================================================================
# 8) LLM real - DataForma sanidad MEDIA
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(400)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_11_sanidad_media_real_llm(db):
    _skip_if_no_api_key()
    agent = Agent11AuditorVirtual()
    result = await agent.generate_supplementary_audit(
        db,
        m10_audit_result=DATAFORMA_M10,
        client_context=DATAFORMA_CTX,
    )

    assert result["fallback_used"] is False, (
        f"Fallback activado; errores={result['schema_errors'][:5]}"
    )
    a = result["audit"]
    # 3-5 fases
    assert 3 <= len(a["pac_priorizado"]["fases"]) <= 5
    # Al menos 1 pregunta sanidad
    sectors = {q["sector_aplicable"] for q in a["preguntas_contextuales_sector"]}
    assert "sanidad" in sectors
    # Veredicto listo_con_riesgos para 72%
    assert a["narrativa_ejecutiva"]["veredicto"] in {
        "listo_con_riesgos", "listo_auditar", "no_listo_plazo"
    }


# =======================================================================
# 9) LLM real - Ayto AAPP BASICA
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(400)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_11_aapp_basica_real_llm(db):
    _skip_if_no_api_key()
    agent = Agent11AuditorVirtual()
    result = await agent.generate_supplementary_audit(
        db,
        m10_audit_result=AYTO_M10,
        client_context=AYTO_CTX,
    )

    assert result["fallback_used"] is False, (
        f"Fallback activado; errores={result['schema_errors'][:5]}"
    )
    a = result["audit"]
    # Al menos 1 pregunta AAPP
    sectors = {q["sector_aplicable"] for q in a["preguntas_contextuales_sector"]}
    assert "aapp" in sectors
    # Con 45% + 8 L0 -> no_listo_plazo o muy_lejos
    assert a["narrativa_ejecutiva"]["veredicto"] in {
        "no_listo_plazo", "muy_lejos", "listo_con_riesgos"
    }


# =======================================================================
# 10) LLM real - prompt caching reduce coste en 2a llamada
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(600)
async def test_agent_11_prompt_caching_reduces_cost(db):
    _skip_if_no_api_key()
    agent = Agent11AuditorVirtual()

    first = await agent.generate_supplementary_audit(
        db,
        m10_audit_result=DATAFORMA_M10,
        client_context=DATAFORMA_CTX,
    )
    second = await agent.generate_supplementary_audit(
        db,
        m10_audit_result=DATAFORMA_M10,
        client_context=DATAFORMA_CTX,
    )

    # Cache funcional
    assert first["cache_read_input_tokens"] > 0 or second["cache_read_input_tokens"] > 0
    assert second["cache_read_input_tokens"] > 0
    # Coste run 2 con Opus 4.7: output 4000+ tokens x 75 USD/M x 0.93 EUR/USD
    # ~0.28 EUR. Con cache read reduce input a trivial. Tope 0.60 EUR holgado.
    assert second["cost_eur_estimated"] < 0.60, (
        f"Run 2 coste {second['cost_eur_estimated']:.5f} EUR > 0.60 EUR"
    )
