"""Tests Agente 19 — Redactor de Propuestas (Sesion 9 Paso 1).

Estructura:
- 4 @pytest.mark.asyncio (determinista, mockea LLM): context builder,
  integracion M13, fallback, whitelist.
- 3 @pytest.mark.llm (llamada real Opus 4.7): numeros exactos, AAPP branch,
  sector sanidad.

Los tests LLM se saltan si ANTHROPIC_API_KEY no esta seteado o si se
corre sin ``-m llm``. pytest-asyncio mode=auto (no necesita decorador).
"""
from __future__ import annotations

import os
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv
from sqlalchemy import text

# Carga .env antes de leer ANTHROPIC_API_KEY — permite que los tests LLM
# corran con la key del fichero sin necesidad de export manual.
load_dotenv()

from backend.app.agents.agent_19_propuestas import (
    Agent19Proposals,
    Agent19ProposalError,
    REQUIRED_SECTIONS,
)
from backend.app.core.pricing import PricingCalculator
from backend.app.database import set_tenant_context
from backend.tests.conftest import _admin_setup


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════


async def _seed_project(
    db,
    *,
    categoria: str = "MEDIA",
    sector: str | None = None,
    cif_prefix: str = "B",
    nombre: str = "Test DataForma",
    tipo_org: str | None = None,  # kept for API compat; no DB column
) -> tuple[str, str, str]:
    """Crea client + project validos para ejercitar A19.

    Retorna (client_id, project_id, lead_id). ``tipo_org`` se ignora porque
    el schema actual de ``clients`` no expone ``tipo_organizacion`` (se
    deriva del nombre via ``is_aapp``).
    """
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    lead_id = uuid.uuid4()
    cif = f"{cif_prefix}{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, sector, created_at) "
                "VALUES (:id, :nombre, :cif, :sector, now())"
            ),
            {
                "id": str(client_id),
                "nombre": nombre,
                "cif": cif,
                "sector": sector,
            },
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, categoria_objetivo, "
                "created_at) VALUES (:id, :cid, 'P-Test', :cat, now())"
            ),
            {
                "id": str(project_id),
                "cid": str(client_id),
                "cat": categoria,
            },
        )
    await db.flush()
    # Tras el seed, activar tenant context para que RLS deje pasar INSERTs
    # posteriores (llm_interaction_log + proposals con project_id).
    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    return str(client_id), str(project_id), str(lead_id)


def _skip_if_no_api_key() -> None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        pytest.skip("ANTHROPIC_API_KEY no configurado — test LLM saltado")


# ══════════════════════════════════════════════════════════════════════════
# 1) Context builder (asyncio, determinista)
# ══════════════════════════════════════════════════════════════════════════


async def test_agent_19_context_builder_from_db(db):
    """Verifica que el context builder extrae project+client+pricing coherentes."""
    _, project_id, _ = await _seed_project(
        db, categoria="MEDIA", sector="sanidad", nombre="Hospital Test"
    )

    agent = Agent19Proposals()
    ctx = await agent._build_full_context(
        db,
        project_id=uuid.UUID(project_id),
        sistemas_en_alcance=3,
        sedes=2,
        madurez_pct=20,  # <30 threshold -> madurez_l0_l1 extra aplicable
        dias_hasta_plazo=120,
        sector_override=None,
        categoria_override=None,
        retainer_tier="R_LITE",
    )

    assert ctx["project_id"] == project_id
    assert ctx["categoria"] == "MEDIA"
    assert ctx["client"]["nombre"] == "Hospital Test"
    assert ctx["sector"] == "sanidad"
    assert ctx["sistemas_en_alcance"] == 3
    assert ctx["sedes"] == 2
    # Pricing deterministico Apendice M v2.2
    pricing = ctx["pricing"]
    assert pricing.categoria == "MEDIA"
    # Base MEDIA = 9.500 EUR segun Apendice M
    assert pricing.base == Decimal("9500.00")
    # Hospital + sanidad -> sector regulado extra (MEDIA only)
    codes = {e.code for e in pricing.extras}
    assert "sector_regulado" in codes
    # Multi ubicacion porque sedes=2
    assert "multi_ubicacion" in codes
    # Madurez 35 < 50 -> madurez_l0_l1
    assert "madurez_l0_l1" in codes
    # Retainer presente
    assert ctx["retainer"] is not None
    assert ctx["retainer"].tier == "R_LITE"


# ══════════════════════════════════════════════════════════════════════════
# 2) Whitelist + deteccion de numeros alucinados (asyncio, puro)
# ══════════════════════════════════════════════════════════════════════════


async def test_agent_19_whitelist_detects_hallucinations(db):
    """El validador v2 acepta citas normativas + importes del pricing y
    marca números claramente inventados."""
    agent = Agent19Proposals()
    calc = PricingCalculator()
    pricing = calc.calculate_implantacion(
        "MEDIA",
        cliente={"sector": "sanidad"},
        sector="sanidad",
        sistemas_en_alcance=2,
        sedes=2,
    )
    context = {
        "pricing": pricing,
        "retainer": None,
        "sistemas_en_alcance": 2,
        "sedes": 2,
        "madurez_pct": None,
        "dias_hasta_plazo": None,
        "m21": {},
    }
    known_amounts = agent._build_known_amounts(pricing, context)
    # Importes del pricing real que deben aparecer en known_amounts
    # (base MEDIA 9500 + sanidad 2000 + multi-sede 1500 + +1 sistema 1200 = 14200)
    assert Decimal("9500.00") in known_amounts
    assert Decimal("14200.00") in known_amounts
    # Garantia MEDIA incluye el hito de 1.000 EUR — debe parsearse del texto
    assert Decimal("1000.00") in known_amounts

    # Parsed limpio: importes conocidos + citas normativas legitimas
    parsed_clean = {
        "resumen_ejecutivo": (
            f"Total {pricing.total:.2f} EUR estructurado en 5 hitos. "
            "[RD 311/2022 Art. 40]. CCN-STIC 808. Directiva 2022/2555 NIS2."
        ),
        "alcance_proyecto": "2 sistemas, 2 sedes. Anexo II 75 medidas.",
        "metodologia_10_fases": (
            "Fase 1 a Fase 10. [CCN-STIC 803 seccion 4]. [RD 311/2022 Art. 31]."
        ),
        "cronograma_textual": "Duracion 8 semanas, 80 horas consultoria.",
        "justificacion_extras": "Sector regulado 2.000,00 EUR. Multi-ubicacion 1.500,00 EUR.",
        "pricing_desglose": f"Base {pricing.base:.2f} EUR. Hitos 26%, 21%, 21%, 21%, 11%.",
        "hitos_pago": "5 hitos segun Apendice M v2.2.",
        "garantias": "Ultimo hito 1.000 EUR si no certifica ENAC.",
        "proximos_pasos": "Firma P-001 validez 30 dias. [RGPD Art. 28].",
        "referencias_legales": (
            "[RD 311/2022]. [Ley 40/2015 Art. 156]. [CCN-STIC 808]. "
            "[Reglamento UE 2016/679 RGPD]. [Ley Organica 3/2018 LOPDGDD]."
        ),
    }
    unknowns_clean = agent._detect_unknown_numbers_v2(parsed_clean, known_amounts)
    assert unknowns_clean == [], f"Draft limpio no deberia tener unknowns: {unknowns_clean}"

    # Parsed sucio: importe inventado + numero suelto sin contexto
    parsed_dirty = dict(parsed_clean)
    parsed_dirty["resumen_ejecutivo"] = "Total 77777.77 EUR en 999 mundos."
    unknowns_dirty = agent._detect_unknown_numbers_v2(parsed_dirty, known_amounts)
    assert any("77777" in u for u in unknowns_dirty), unknowns_dirty
    assert any("999" in u for u in unknowns_dirty), unknowns_dirty

    # validate_numbers_v2 publico: firma sobre string suelto
    free_text = "Un hito fantasma de 999.123,45 EUR."
    unknowns_free = agent.validate_numbers_v2(free_text, known_amounts=known_amounts)
    assert any("999" in u for u in unknowns_free), unknowns_free


# ══════════════════════════════════════════════════════════════════════════
# 3) Fallback determinista cuando el LLM falla
# ══════════════════════════════════════════════════════════════════════════


async def test_agent_19_fallback_on_llm_failure(db):
    """Si el LLM falla 3 veces consecutivas, se entrega fallback determinista."""
    _, project_id, _ = await _seed_project(
        db, categoria="BASICA", sector="educacion", nombre="Colegio Test"
    )
    agent = Agent19Proposals()

    # Mockear invoke para devolver respuestas invalidas (no JSON) 3 veces
    bad_response = {
        "response": "texto libre no-JSON",
        "parsed": None,
        "tokens_input": 100,
        "tokens_output": 50,
        "latency_ms": 10,
        "model": "claude-opus-4-7",
    }
    with patch.object(Agent19Proposals, "invoke", new=AsyncMock(return_value=bad_response)):
        result = await agent.generate_proposal(
            db,
            project_id=uuid.UUID(project_id),
            sistemas_en_alcance=1,
            sedes=1,
        )

    assert result["fallback_used"] is True
    draft = result["proposal_draft"]
    # El fallback rellena las 10 secciones
    assert all(k in draft for k in REQUIRED_SECTIONS)
    assert "BASICA" in draft["resumen_ejecutivo"]
    # El pricing_snapshot sigue siendo deterministico
    assert result["pricing_snapshot"]["categoria"] == "BASICA"
    assert result["validation"]["numbers_ok"] is False
    assert result["validation"]["retry_count"] >= 1


# ══════════════════════════════════════════════════════════════════════════
# 4) Integracion con M13 ProposalService (narrative_mode=llm con mock)
# ══════════════════════════════════════════════════════════════════════════


async def test_agent_19_m13_integration_narrative_mode_llm(db):
    """``ProposalService.generate_proposal_apendice_m`` con narrative_mode='llm'
    persiste el draft LLM en importe_desglose['llm_narrative'].
    """
    client_id, project_id, _ = await _seed_project(
        db, categoria="MEDIA", sector="tic", nombre="Empresa TIC Test"
    )
    # Seed lead con RLS bypass (M13 proposal requires FK valido a leads)
    lead_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO leads (id, empresa_nombre, empresa_cif, sector, "
                "estado, created_at) VALUES (:id, :nm, :cif, :sector, 'nuevo', now())"
            ),
            {
                "id": str(lead_id),
                "nm": "Empresa TIC Test",
                "cif": f"B{uuid.uuid4().hex[:8].upper()}",
                "sector": "tic",
            },
        )
    # Re-activar tenant context tras _admin_setup (RESET ROLE limpio)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id)
    )

    from backend.app.motors.m13_commercial.proposal_service import ProposalService

    # Mock A19 para no consumir API real en este test asyncio
    fake_result = {
        "proposal_draft": {k: f"Seccion {k} OK" for k in REQUIRED_SECTIONS},
        "pricing_snapshot": {"categoria": "MEDIA"},
        "is_aapp": False,
        "validation": {"numbers_ok": True, "unknown_amounts": [], "retry_count": 0},
        "tokens_input": 1000,
        "tokens_output": 4000,
        "cost_eur_estimated": 0.30,
        "latency_ms": 5000,
        "model": "claude-opus-4-7",
        "fallback_used": False,
        "context_summary": {"categoria": "MEDIA"},
    }

    svc = ProposalService()
    with patch.object(
        svc,
        "_generate_narrative_via_agent_19",
        new=AsyncMock(return_value=fake_result),
    ):
        prop = await svc.generate_proposal_apendice_m(
            db,
            lead_id=lead_id,
            categoria="MEDIA",
            cliente={"sector": "tic"},
            sector="tic",
            sistemas_en_alcance=2,
            sedes=1,
            project_id=uuid.UUID(project_id),
            narrative_mode="llm",
        )

    assert prop.categoria_objetivo == "MEDIA"
    llm_narr = (prop.importe_desglose or {}).get("llm_narrative")
    assert llm_narr is not None
    assert llm_narr["validation"]["numbers_ok"] is True
    assert llm_narr["fallback_used"] is False
    assert all(k in llm_narr["proposal_draft"] for k in REQUIRED_SECTIONS)


# ══════════════════════════════════════════════════════════════════════════
# 5) LLM real: numeros del pricing respetados (DataForma MEDIA sanidad)
# ══════════════════════════════════════════════════════════════════════════


def _total_length(draft: dict) -> int:
    return sum(
        len(v) for v in draft.values() if isinstance(v, str)
    )


@pytest.mark.llm
@pytest.mark.timeout(600)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_19_respects_pricing_numbers_real_llm(db):
    """Opus 4.7 real: numeros del draft coinciden con PricingCalculator."""
    _skip_if_no_api_key()
    _, project_id, _ = await _seed_project(
        db, categoria="MEDIA", sector="sanidad", nombre="Hospital DataForma"
    )
    agent = Agent19Proposals()
    result = await agent.generate_proposal(
        db,
        project_id=uuid.UUID(project_id),
        sistemas_en_alcance=2,
        sedes=2,
        madurez_pct=40,
    )
    draft = result["proposal_draft"]
    snapshot = result["pricing_snapshot"]
    total_eur = snapshot["total_eur"]  # p. ej. "12700.00"

    # Nunca fallback en este test — si ocurre, falla.
    assert result["fallback_used"] is False, (
        f"Fallback determinista activado; LLM no respondio con 10 secciones validas. "
        f"retry_count={result['validation']['retry_count']} "
        f"unknown={result['validation']['unknown_amounts'][:3]}"
    )

    # Longitud total del draft >= 2000 chars (propuesta real debe ser sustancial)
    total_len = _total_length(draft)
    assert total_len >= 2000, (
        f"Longitud total del draft = {total_len} chars; Opus 4.7 deberia producir >=2000"
    )

    # El total exacto debe aparecer en el resumen ejecutivo en CUALQUIERA de
    # los formatos típicos: "14200", "14200.00", "14.200", "14.200,00".
    res_ej = draft["resumen_ejecutivo"]
    total_int = total_eur.split(".")[0]                    # "14200"
    total_int_es = f"{int(total_int):,}".replace(",", ".") # "14.200"
    total_es = total_int_es + "," + total_eur.split(".")[1] if "." in total_eur else total_int_es
    expected_any = (total_int, total_eur, total_int_es, total_es)
    assert any(tok in res_ej for tok in expected_any), (
        f"El total {total_eur} no aparece en resumen_ejecutivo (probado: {expected_any}): "
        f"{res_ej[:300]}"
    )

    # Tokens realistas de un Opus 4.7 con propuesta completa
    assert result["tokens_input"] > 300
    assert result["tokens_output"] > 1500, (
        f"tokens_output={result['tokens_output']} — Opus deberia generar >1500 "
        f"para una propuesta con 10 secciones"
    )

    # Coste estimado razonable (<2 EUR para una propuesta)
    assert result["cost_eur_estimated"] < 2.0

    # Citas normativas obligatorias en cualquier propuesta ENS real
    joined = " ".join(
        v for v in draft.values() if isinstance(v, str)
    ).lower()
    assert "311/2022" in joined, "Falta cita RD 311/2022 (norma base ENS)"
    assert "ccn-stic" in joined or "ccn stic" in joined, (
        "Falta cita CCN-STIC (guias de referencia serie 800)"
    )


@pytest.mark.llm
@pytest.mark.timeout(600)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_19_aapp_branch_lcsp_real_llm(db):
    """Un ayuntamiento (CIF P...) debe disparar AAPP -> LCSP/FACe/60d/DIR3."""
    _skip_if_no_api_key()
    _, project_id, _ = await _seed_project(
        db,
        categoria="BASICA",
        sector="administracion publica",
        cif_prefix="P",
        nombre="Ayuntamiento de Villanueva",
        tipo_org="Ayuntamiento",
    )
    agent = Agent19Proposals()
    result = await agent.generate_proposal(
        db,
        project_id=uuid.UUID(project_id),
        sistemas_en_alcance=1,
        sedes=1,
        dias_hasta_plazo=30,
    )

    assert result["fallback_used"] is False, (
        f"Fallback determinista activado en caso AAPP; "
        f"retry_count={result['validation']['retry_count']} "
        f"unknown={result['validation']['unknown_amounts'][:3]}"
    )
    assert result["is_aapp"] is True

    draft = result["proposal_draft"]
    assert _total_length(draft) >= 2000, "Propuesta AAPP demasiado corta"

    joined = " ".join(
        v for v in draft.values() if isinstance(v, str)
    ).lower()
    # LCSP explicita
    assert "lcsp" in joined or "ley 9/2017" in joined, "Falta mencion LCSP/Ley 9/2017"
    # Art. 198.4 o "60 dias" para pago AAPP
    assert ("198.4" in joined) or ("60 dias" in joined) or ("60 d" in joined), (
        "Falta plazo de pago AAPP (198.4 / 60 dias)"
    )
    # FACe (facturacion electronica AAPP) o DIR3 obligatorio
    assert "face" in joined or "dir3" in joined or "dir 3" in joined, (
        "Falta mencion FACe / DIR3 para AAPP"
    )
    # Urgencia detectada (plazo 30d < 42d threshold -> +30%)
    assert result["pricing_snapshot"]["urgency_surcharge_eur"] != "0.00", (
        "No se aplico recargo urgencia para plazo 30d"
    )


@pytest.mark.llm
@pytest.mark.timeout(600)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_19_sector_sanidad_real_llm(db):
    """Sector sanidad debe citar normativa sanitaria + CCN-CERT IS-47 o NIS2."""
    _skip_if_no_api_key()
    _, project_id, _ = await _seed_project(
        db, categoria="MEDIA", sector="sanidad", nombre="Hospital Sanitas Pro"
    )
    agent = Agent19Proposals()
    result = await agent.generate_proposal(
        db,
        project_id=uuid.UUID(project_id),
        sistemas_en_alcance=3,
        sedes=1,
        madurez_pct=55,
    )
    assert result["fallback_used"] is False, (
        f"Fallback determinista activado en caso sanidad; "
        f"retry_count={result['validation']['retry_count']} "
        f"unknown={result['validation']['unknown_amounts'][:3]}"
    )

    draft = result["proposal_draft"]
    assert _total_length(draft) >= 2000, "Propuesta sanidad demasiado corta"

    joined = " ".join(
        v for v in draft.values() if isinstance(v, str)
    ).lower()
    # Al menos UNA de: NIS2, CCN-CERT IS-47, sanidad (adjetivo/sustantivo)
    keywords_any = ("nis2", "ccn-cert", "is-47", "is47", "sanid", "sanit")
    assert any(k in joined for k in keywords_any), (
        f"Ninguna referencia sanitaria encontrada: {joined[:500]}"
    )


# ══════════════════════════════════════════════════════════════════════════
# 5) FASE B Path A · prompt_caching activation (2026-05-23)
# ══════════════════════════════════════════════════════════════════════════


class TestA19PromptCachingActivated:
    """A19 prompt_caching activation (FASE B Path A · OPS-045 40ª)."""

    def test_a19_enable_prompt_caching_flag_true(self):
        """Class-level flag activated · replicate pattern 8 agentes."""
        assert Agent19Proposals.ENABLE_PROMPT_CACHING is True

    @pytest.mark.asyncio
    async def test_a19_call_llm_propagates_enable_prompt_caching(self, patched_settings):
        """_call_llm pasa enable_prompt_caching=True a llm_router.complete()."""
        agent = Agent19Proposals()
        with patch(
            "backend.app.core.ai.llm_router.get_default_llm_router"
        ) as mock_get_router:
            mock_router = mock_get_router.return_value
            mock_resp = type("R", (), {
                "content": "{}",
                "model": "claude-opus-4-7",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "latency_ms": 100,
            })()
            mock_router.complete = lambda **kw: mock_resp
            captured: dict = {}

            def _capture(**kw):
                captured.update(kw)
                return mock_resp

            mock_router.complete = _capture
            # Suite mock-by-default vacía ANTHROPIC_API_KEY (ver conftest); este
            # test mockea el router pero necesita que _call_llm pase del gate
            # `if not api_key` para llegar a él → key dummy vía patched_settings
            # (setea env + cache_clear settings + reset router singleton).
            patched_settings(anthropic_api_key="sk-test-dummy")
            await agent._call_llm(
                system_prompt="SYS",
                user_message="USER",
                model="opus-4.7",
                temperature=0.15,
                max_tokens=100,
            )
            assert captured.get("enable_prompt_caching") is True, (
                "A19 _call_llm debe propagar enable_prompt_caching=True"
            )

    @pytest.mark.asyncio
    async def test_a19_response_includes_cache_tokens_fields(self):
        """invoke() returned dict incluye cache_creation + cache_read_input_tokens."""
        agent = Agent19Proposals()
        # Mock _call_llm directly to simulate cached response
        with patch.object(
            Agent19Proposals,
            "_call_llm",
            new=AsyncMock(return_value={
                "text": '{"resumen_ejecutivo":"x"}',
                "tokens_input": 1000,
                "tokens_output": 200,
                "cache_creation_input_tokens": 3500,
                "cache_read_input_tokens": 0,
                "model": "claude-opus-4-7",
            }),
        ):
            from unittest.mock import MagicMock
            db_mock = MagicMock()
            db_mock.execute = AsyncMock(return_value=MagicMock(
                fetchone=MagicMock(return_value=None)
            ))
            db_mock.begin_nested = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(),
                    __aexit__=AsyncMock(),
                )
            )
            db_mock.add = MagicMock()
            db_mock.flush = AsyncMock()
            result = await agent.invoke(
                db=db_mock,
                project_id=None,
                user_message="Test",
            )
            assert "cache_creation_input_tokens" in result
            assert "cache_read_input_tokens" in result
            assert result["cache_creation_input_tokens"] == 3500
