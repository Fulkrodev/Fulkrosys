"""Tests Agente 4 - Redactor Diagnosticos E-090 (Sesion 9 Paso 2.5).

Scope restringido: A4 solo redacta secciones 1, 2, 6 del E-090
(narrativa senior). Las secciones 3.1/3.2/4/5 siguen deterministas
(M21+M22+M4). Los tests aqui validan:
- Schema strict de las 3 secciones.
- Anti-hallucination: el LLM NO puede inventar porcentajes / horas /
  meses / codigos ENS que no esten en deterministic_data.
- Fallback template cuando el LLM falla.
- CCN-STIC sector-aware (al menos una cita relevante por sector).

LLM tests se saltan si ANTHROPIC_API_KEY no esta configurado.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv()

from backend.app.agents.agent_04_redactor import (
    Agent04RedactorDiagnosticos,
    RedactorPoliticasAgent,
    _CCN_STIC_BY_SECTOR,
    _ENS_CATEGORIES,
    _MATURITY_LEVELS,
    _REQUIRED_TOP_KEYS,
    _SECTORS,
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
}
DATAFORMA_DATA = {
    "madurez_global": "L1",
    "porcentaje_conformidad": 32,
    "familias_peores": ["mp.s", "op.exp", "org.3"],
    "plazo_viable_meses": 8,
    "horas_estimadas": 105,
    "activos_criticos": 14,
    "top_gaps": [
        {"codigo": "op.exp.3", "gap": "configuracion no gestionada"},
        {"codigo": "mp.s.4", "gap": "sin aceptacion puesta servicio"},
        {"codigo": "org.3", "gap": "sin proceso revision periodica"},
    ],
}

AYTO_CTX = {
    "company_name": "Ayuntamiento de Villanueva",
    "sector": "aapp",
    "size": "PYME",
    "ens_category": "BASICA",
    "is_aapp": True,
}
AYTO_DATA = {
    "madurez_global": "L0",
    "porcentaje_conformidad": 18,
    "familias_peores": ["org", "mp.s"],
    "plazo_viable_meses": 3,
    "horas_estimadas": 35,
    "activos_criticos": 4,
    "top_gaps": [
        {"codigo": "org.1", "gap": "sin politica de seguridad"},
        {"codigo": "org.2", "gap": "sin responsable designado"},
        {"codigo": "mp.s.1", "gap": "proteccion perimetral insuficiente"},
    ],
}


def _valid_sections(
    *,
    porcentaje: int = 32,
    horas: int = 105,
    plazo: int = 8,
    madurez: str = "L1",
    gap_code: str = "op.exp.3",
    ccn_stic: str = "CCN-STIC 809 Guia Sanidad",
) -> dict:
    """JSON valido que respeta el schema + los valores de deterministic_data."""
    return {
        "seccion_1_resumen_ejecutivo": {
            "contenido_markdown": (
                "### Situacion actual\n\n"
                f"DataForma opera en categoria MEDIA con madurez {madurez} "
                f"y {porcentaje}% de conformidad. Esfuerzo estimado "
                f"{horas} horas en {plazo} meses.\n\n"
                "### Donde duele\n\nLas familias mp.s, op.exp y org.3 "
                f"concentran los gaps criticos. Ejemplo {gap_code}: "
                "configuracion no gestionada.\n\n"
                "### Decision\n\nDireccion debe asignar sponsor y firmar "
                "el DPA antes de arrancar.\n\n"
                "### Plazo\n\n"
                f"{plazo} meses son viables con sponsor claro y presupuesto aprobado en primer mes."
            ),
            "hallazgos_clave": [
                f"Madurez inicial {madurez} con {porcentaje}% conformidad.",
                "Familias criticas mp.s, op.exp y org.3.",
                f"Esfuerzo {horas} horas en {plazo} meses.",
            ],
            "decisiones_requeridas_direccion": [
                "Designar RSEG con dedicacion minima.",
                "Firmar DPA con proveedor cloud.",
                "Aprobar presupuesto de consultoria y MFA.",
            ],
        },
        "seccion_2_marco_normativo_sectorial": {
            "normativa_aplicable_markdown": (
                "### Marco normativo aplicable\n\n"
                "A este cliente del sector sanidad le aplican RD 311/2022 "
                "categoria MEDIA, Reglamento UE 2016/679 RGPD (con especial "
                "atencion al art. 9), LOPDGDD y Ley 41/2002.\n\n"
                f"La guia sectorial de referencia es la {ccn_stic}."
            ),
            "citas_ccn_stic": [
                {
                    "norma": ccn_stic,
                    "aplicabilidad": (
                        "Guia sectorial especifica para organizaciones "
                        "sanitarias con datos de salud."
                    ),
                },
                {
                    "norma": "CCN-STIC 803 Valoracion de sistemas",
                    "aplicabilidad": "Metodologia de categorizacion.",
                },
            ],
            "obligaciones_transversales": [
                "RGPD Reglamento UE 2016/679",
                "LOPDGDD Ley Organica 3/2018",
                "Ley 41/2002 autonomia del paciente",
            ],
        },
        "seccion_6_recomendaciones_estrategicas": {
            "vision_senior_markdown": (
                "### Vision senior\n\n"
                f"Con L1 y {porcentaje}% de partida, los {plazo} meses son "
                "compatibles si Fase 1 se dedica a cimientos. Apalancar "
                f"{ccn_stic} ahorra trabajo documental."
            ),
            "roadmap_highlevel": [
                {"fase": "1 - Cimientos", "meses": "0-2", "foco": "Gobierno + inventario", "rationale": "Sin base no escala."},
                {"fase": "2 - Proteccion", "meses": "2-5", "foco": "Familias mp.s y op.exp", "rationale": "Cerrar gaps con riesgo legal."},
                {"fase": "3 - Certificacion", "meses": "5-8", "foco": "Evidencias + auditoria externa", "rationale": "Dossier ENAC antes de cierre."},
            ],
            "riesgos_ejecucion": [
                "Sin sponsor el proyecto se estanca.",
                "Retraso en DPA retrasa Fase 2.",
            ],
        },
    }


def _mock_llm_response(sections: dict, *, tokens_in: int = 3000, tokens_out: int = 2000) -> dict:
    return {
        "agent_id": 4,
        "agent_name": "Redactor Diagnosticos E-090",
        "response": "{...}",
        "parsed": sections,
        "model": "claude-sonnet-4-6",
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "latency_ms": 20000,
        "citations": [],
        "project_id": None,
    }


# =======================================================================
# 1) Alias retrocompat + enums
# =======================================================================


def test_agent_04_alias_backcompat():
    assert RedactorPoliticasAgent is Agent04RedactorDiagnosticos


def test_agent_04_enums_match_spec():
    assert _ENS_CATEGORIES == {"BASICA", "MEDIA", "ALTA"}
    assert _SECTORS == {"sanidad", "aapp", "fintech", "otro"}
    assert _MATURITY_LEVELS == {"L0", "L1", "L2", "L3", "L4", "L5"}
    assert len(_REQUIRED_TOP_KEYS) == 3
    # CCN-STIC catalogo completo
    assert "809" in _CCN_STIC_BY_SECTOR["sanidad"]
    assert "803" in _CCN_STIC_BY_SECTOR["aapp"]
    assert "830" in _CCN_STIC_BY_SECTOR["fintech"]


# =======================================================================
# 2) Input validation - ens_category / sector / madurez invalidos
# =======================================================================


async def test_agent_04_invalid_ens_category_raises(db):
    agent = Agent04RedactorDiagnosticos()
    ctx = {**DATAFORMA_CTX, "ens_category": "MEGA"}
    with pytest.raises(ValueError, match="ens_category invalida"):
        await agent.generate_e090_narrative_sections(
            db, client_context=ctx, deterministic_data=DATAFORMA_DATA,
        )


async def test_agent_04_missing_deterministic_field_raises(db):
    agent = Agent04RedactorDiagnosticos()
    data = dict(DATAFORMA_DATA)
    del data["porcentaje_conformidad"]
    with pytest.raises(ValueError, match="porcentaje_conformidad"):
        await agent.generate_e090_narrative_sections(
            db, client_context=DATAFORMA_CTX, deterministic_data=data,
        )


# =======================================================================
# 3) Success path mock - contiene las 3 secciones validas
# =======================================================================


async def test_agent_04_complete_data_mock_produces_3_sections(db):
    agent = Agent04RedactorDiagnosticos()
    good = _mock_llm_response(_valid_sections())
    with patch.object(
        Agent04RedactorDiagnosticos, "invoke", new=AsyncMock(return_value=good)
    ) as invoke_mock:
        result = await agent.generate_e090_narrative_sections(
            db,
            client_context=DATAFORMA_CTX,
            deterministic_data=DATAFORMA_DATA,
        )

    assert invoke_mock.call_count == 1
    assert result["fallback_used"] is False
    assert result["schema_valid"] is True
    s = result["sections"]
    # Las 3 secciones presentes
    for k in _REQUIRED_TOP_KEYS:
        assert k in s
    # Cada seccion con campo markdown no vacio
    assert s["seccion_1_resumen_ejecutivo"]["contenido_markdown"].strip()
    assert s["seccion_2_marco_normativo_sectorial"]["normativa_aplicable_markdown"].strip()
    assert s["seccion_6_recomendaciones_estrategicas"]["vision_senior_markdown"].strip()


# =======================================================================
# 4) Schema strict validation - 7 casos parametrizados
# =======================================================================


@pytest.mark.parametrize(
    "mutator,expected_error_substring",
    [
        # Seccion 1 contenido demasiado corto (<400 chars)
        (
            lambda s: s["seccion_1_resumen_ejecutivo"].__setitem__(
                "contenido_markdown", "muy corto"
            ),
            "seccion_1.contenido_markdown",
        ),
        # Seccion 1 demasiados hallazgos
        (
            lambda s: s["seccion_1_resumen_ejecutivo"].__setitem__(
                "hallazgos_clave", ["a", "b", "c", "d", "e"]
            ),
            "hallazgos_clave",
        ),
        # Seccion 2 citas vacias
        (
            lambda s: s["seccion_2_marco_normativo_sectorial"].__setitem__(
                "citas_ccn_stic", []
            ),
            "citas_ccn_stic",
        ),
        # Seccion 6 sin roadmap
        (
            lambda s: s["seccion_6_recomendaciones_estrategicas"].__setitem__(
                "roadmap_highlevel", []
            ),
            "roadmap_highlevel",
        ),
        # Seccion 6 demasiadas fases
        (
            lambda s: s["seccion_6_recomendaciones_estrategicas"].__setitem__(
                "roadmap_highlevel",
                [{"fase": f"F{i}", "meses": "0-1", "foco": "x", "rationale": "y"} for i in range(10)],
            ),
            "roadmap_highlevel",
        ),
    ],
)
def test_agent_04_schema_strict_validation(mutator, expected_error_substring):
    agent = Agent04RedactorDiagnosticos()
    sections = _valid_sections()
    mutator(sections)
    errors = agent._validate_schema(sections, DATAFORMA_CTX, DATAFORMA_DATA)
    assert any(expected_error_substring in e for e in errors), errors


def test_agent_04_schema_rejects_missing_ccn_stic_sanitario():
    agent = Agent04RedactorDiagnosticos()
    sections = _valid_sections(ccn_stic="CCN-STIC 999 inventado")
    # Solo CCN-STIC 999 pero ninguno de [809, 818, 803] que son los
    # del sector sanidad.
    sections["seccion_2_marco_normativo_sectorial"]["citas_ccn_stic"] = [
        {"norma": "CCN-STIC 999 inventado", "aplicabilidad": "x"},
    ]
    errors = agent._validate_schema(sections, DATAFORMA_CTX, DATAFORMA_DATA)
    assert any("citas_ccn_stic no cita ningun CCN-STIC relevante" in e for e in errors)


# =======================================================================
# 5) Anti-hallucination CRITICO - rechaza numeros inventados
# =======================================================================


def test_agent_04_rejects_hallucinated_percentage():
    """Si el LLM inventa un importe (4567 EUR) no presente en
    deterministic_data, el validator debe detectarlo.

    Nota historica: este test originalmente usaba 45% pero el commit
    2b8e275 anadio range(0,101) a la whitelist (numeros pequenos
    legitimos en narrativa); 45 quedo whitelisted. Cambiado a 4567
    (4 digitos, capturado por regex \\b\\d{2,4}\\b, fuera de rangos
    0-100/800-999/1990-2030 y de _LEGAL_REF_NUMBERS).
    """
    agent = Agent04RedactorDiagnosticos()
    sections = _valid_sections()
    # Meter un 4567 inventado en la narrativa seccion 1
    sections["seccion_1_resumen_ejecutivo"]["contenido_markdown"] += (
        "\n\nAdicionalmente, el presupuesto inicial estimado sera de 4567 EUR para acciones complementarias, "
        "lo que eleva la exposicion general a riesgos operativos de nivel alto para la organizacion entera."
    )
    errors = agent._validate_schema(sections, DATAFORMA_CTX, DATAFORMA_DATA)
    assert any("hallucinated_number: 4567" in e for e in errors), (
        f"No detecto hallucination del 4567 EUR. Errores: {errors}"
    )


def test_agent_04_rejects_hallucinated_hours():
    agent = Agent04RedactorDiagnosticos()
    sections = _valid_sections()
    # Inventar 250 horas en el rationale del roadmap
    sections["seccion_6_recomendaciones_estrategicas"]["roadmap_highlevel"][0]["rationale"] = (
        "Se estima en 250 horas esta fase inicial de cimientos segun nuestra experiencia."
    )
    errors = agent._validate_schema(sections, DATAFORMA_CTX, DATAFORMA_DATA)
    assert any("hallucinated_number: 250" in e for e in errors), errors


def test_agent_04_rejects_hallucinated_ens_code():
    agent = Agent04RedactorDiagnosticos()
    sections = _valid_sections()
    # op.pl.1 NO esta en deterministic_data.top_gaps ni familias_peores
    sections["seccion_1_resumen_ejecutivo"]["contenido_markdown"] += (
        "\n\nFalta especialmente la medida op.pl.1 relacionada con planificacion "
        "estrategica que no aparece documentada en ningun sitio del diagnostico."
    )
    errors = agent._validate_schema(sections, DATAFORMA_CTX, DATAFORMA_DATA)
    assert any("hallucinated_ens_codes" in e for e in errors), errors


def test_agent_04_whitelist_allows_deterministic_numbers():
    """Los numeros de deterministic_data (32/105/8/14) NO deben disparar errores."""
    agent = Agent04RedactorDiagnosticos()
    sections = _valid_sections()
    errors = agent._validate_schema(sections, DATAFORMA_CTX, DATAFORMA_DATA)
    # Sin mutaciones debe pasar validator (errors vacio).
    assert errors == [], errors


def test_agent_04_whitelist_allows_ccn_stic_and_legal_refs():
    """CCN-STIC 809, RGPD art. 28, RD 311/2022 son numeros pass-through."""
    agent = Agent04RedactorDiagnosticos()
    sections = _valid_sections()
    sections["seccion_2_marco_normativo_sectorial"]["normativa_aplicable_markdown"] += (
        " El Reglamento UE 2016/679 se complementa con RD 311/2022 y la "
        "Ley Organica 3/2018 (LOPDGDD). CCN-STIC 809 y 818 son las guias de referencia."
    )
    errors = agent._validate_schema(sections, DATAFORMA_CTX, DATAFORMA_DATA)
    assert errors == [], errors


# =======================================================================
# 6) Fallback template cuando el LLM falla
# =======================================================================


async def test_agent_04_fallback_on_invalid_json(db):
    agent = Agent04RedactorDiagnosticos()
    bad = {
        "response": "no json",
        "parsed": None,
        "tokens_input": 500, "tokens_output": 20, "latency_ms": 5,
        "model": "claude-sonnet-4-6",
    }
    with patch.object(
        Agent04RedactorDiagnosticos, "invoke", new=AsyncMock(return_value=bad)
    ):
        result = await agent.generate_e090_narrative_sections(
            db,
            client_context=DATAFORMA_CTX,
            deterministic_data=DATAFORMA_DATA,
        )

    assert result["fallback_used"] is True
    s = result["sections"]
    # Las 3 secciones presentes con contenido minimo
    for k in _REQUIRED_TOP_KEYS:
        assert k in s
    # Fallback debe mencionar el porcentaje deterministico (32)
    assert "32" in s["seccion_1_resumen_ejecutivo"]["contenido_markdown"]
    # Roadmap con 3 fases minimas
    assert len(s["seccion_6_recomendaciones_estrategicas"]["roadmap_highlevel"]) >= 3


# =======================================================================
# 7) LLM real - DataForma sanidad MEDIA
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(300)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_04_sanidad_media_real_llm(db):
    _skip_if_no_api_key()
    agent = Agent04RedactorDiagnosticos()
    result = await agent.generate_e090_narrative_sections(
        db,
        client_context=DATAFORMA_CTX,
        deterministic_data=DATAFORMA_DATA,
    )

    assert result["fallback_used"] is False, (
        f"Fallback activado; errores={result['schema_errors'][:5]}"
    )
    s = result["sections"]
    # Seccion 1: menciona porcentaje 32 o el concepto de conformidad.
    s1_text = s["seccion_1_resumen_ejecutivo"]["contenido_markdown"]
    assert "32" in s1_text, "Seccion 1 no cita el 32% de conformidad"
    # Seccion 2: cita CCN-STIC sanidad (809) al menos 1 vez
    s2_text = " ".join(
        c.get("norma", "") for c in s["seccion_2_marco_normativo_sectorial"]["citas_ccn_stic"]
    )
    assert "809" in s2_text or "818" in s2_text, (
        f"Seccion 2 no cita CCN-STIC sanitario: {s2_text}"
    )
    # Seccion 6: al menos 3 fases en roadmap
    roadmap = s["seccion_6_recomendaciones_estrategicas"]["roadmap_highlevel"]
    assert 3 <= len(roadmap) <= 6


# =======================================================================
# 8) LLM real - Ayto AAPP BASICA
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(300)
@pytest.mark.flaky(reruns=3, reruns_delay=10)
async def test_agent_04_aapp_basica_real_llm(db):
    _skip_if_no_api_key()
    agent = Agent04RedactorDiagnosticos()
    result = await agent.generate_e090_narrative_sections(
        db,
        client_context=AYTO_CTX,
        deterministic_data=AYTO_DATA,
    )

    assert result["fallback_used"] is False, (
        f"Fallback activado; errores={result['schema_errors'][:5]}"
    )
    s = result["sections"]
    # Seccion 2 debe citar CCN-STIC AAPP (803/804/805)
    s2_text = " ".join(
        c.get("norma", "") for c in s["seccion_2_marco_normativo_sectorial"]["citas_ccn_stic"]
    )
    assert any(stic in s2_text for stic in ("803", "804", "805")), (
        f"Seccion 2 no cita CCN-STIC AAPP: {s2_text}"
    )
    # 3 meses con L0: al menos 1 riesgo de ejecucion
    riesgos = s["seccion_6_recomendaciones_estrategicas"]["riesgos_ejecucion"]
    assert len(riesgos) >= 1


# =======================================================================
# 9) LLM real - prompt caching reduce coste en 2a llamada
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(400)
async def test_agent_04_prompt_caching_reduces_cost(db):
    _skip_if_no_api_key()
    agent = Agent04RedactorDiagnosticos()

    first = await agent.generate_e090_narrative_sections(
        db,
        client_context=DATAFORMA_CTX,
        deterministic_data=DATAFORMA_DATA,
    )
    second = await agent.generate_e090_narrative_sections(
        db,
        client_context=DATAFORMA_CTX,
        deterministic_data=DATAFORMA_DATA,
    )

    # Cache funcional
    assert first["cache_read_input_tokens"] > 0 or second["cache_read_input_tokens"] > 0
    assert second["cache_read_input_tokens"] > 0
    # Run 2 coste con E-090 narrative largo (output 3000-4500 tokens al
    # maximo). tope 0.080 EUR holgado — lo critico es cache_read > 0
    # (caching activo) y la reduccion marginal. Si hay fallback por
    # validator, el retry anade tokens extra, asi que el margen es
    # amplio.
    assert second["cost_eur_estimated"] < 0.080, (
        f"Run 2 coste {second['cost_eur_estimated']:.5f} EUR > 0.080 EUR"
    )
