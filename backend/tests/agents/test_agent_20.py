"""Tests Agente 20 — Negociador Contractual (Sesion 9 Paso 2.1).

4 asyncio (mock / determinista) + 3 @pytest.mark.llm (Sonnet 4.6 real).
Usa el mismo patron que test_agent_19.
"""
from __future__ import annotations

import json
import os
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv
from sqlalchemy import text

from backend.app.agents.agent_20_negociacion import (
    Agent20NegociadorContractual,
    REQUIRED_SECTIONS,
)
from backend.app.agents.validators import detect_unknowns_in_text
from backend.app.core.pricing import PricingCalculator
from backend.app.database import set_tenant_context
from backend.app.motors.m13_commercial.proposal_service import ProposalService
from backend.tests.conftest import _admin_setup

load_dotenv()


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════


async def _seed_proposal(
    db,
    *,
    categoria: str = "MEDIA",
    sector: str = "sanidad",
    cif_prefix: str = "B",
    nombre: str = "Hospital Test",
    sistemas_en_alcance: int = 2,
    sedes: int = 1,
    madurez_pct: int | None = None,
    dias_hasta_plazo: int | None = None,
) -> tuple[str, str, uuid.UUID, uuid.UUID]:
    """Crea client + project + lead + proposal y retorna ids."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    lead_id = uuid.uuid4()
    cif = f"{cif_prefix}{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, sector, created_at) "
                "VALUES (:id, :nm, :cif, :sector, now())"
            ),
            {"id": str(client_id), "nm": nombre, "cif": cif, "sector": sector},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, categoria_objetivo, "
                "created_at) VALUES (:id, :cid, 'P-test', :cat, now())"
            ),
            {"id": str(project_id), "cid": str(client_id), "cat": categoria},
        )
        await db.execute(
            text(
                "INSERT INTO leads (id, empresa_nombre, empresa_cif, sector, "
                "estado, created_at) VALUES (:id, :nm, :cif, :sector, 'nuevo', now())"
            ),
            {"id": str(lead_id), "nm": nombre, "cif": cif, "sector": sector},
        )
    await db.flush()
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    svc = ProposalService()
    cliente_dict = {"cif": cif, "razon_social": nombre, "sector": sector}
    proposal = await svc.generate_proposal_apendice_m(
        db,
        lead_id=lead_id,
        categoria=categoria,
        cliente=cliente_dict,
        sector=sector,
        sistemas_en_alcance=sistemas_en_alcance,
        sedes=sedes,
        madurez_pct=madurez_pct,
        dias_hasta_plazo=dias_hasta_plazo,
        project_id=project_id,
    )
    return str(client_id), str(project_id), lead_id, proposal.id


def _skip_if_no_api_key() -> None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        pytest.skip("ANTHROPIC_API_KEY no configurado — test LLM saltado")


def _total_length(draft: dict) -> int:
    return sum(len(v) for v in draft.values() if isinstance(v, str))


# ══════════════════════════════════════════════════════════════════════════
# 1) Context builder desde Proposal (asyncio)
# ══════════════════════════════════════════════════════════════════════════


async def test_agent_20_context_builder_from_proposal(db):
    """Context builder resuelve categoria + is_aapp + hitos + garantia."""
    _, project_id, lead_id, proposal_id = await _seed_proposal(
        db, categoria="MEDIA", sector="sanidad", nombre="Hospital Demo"
    )
    agent = Agent20NegociadorContractual()
    ctx = await agent._build_full_context(
        db,
        proposal_id=proposal_id,
        cliente={"cif": "B99999999", "razon_social": "Hospital Demo", "sector": "sanidad"},
        cliente_firmante_nombre="Ana Responsable",
        cliente_firmante_cargo="Directora SI",
    )
    assert ctx["categoria"] == "MEDIA"
    assert ctx["is_aapp"] is False
    assert ctx["importe_total"] > Decimal("0")
    assert len(ctx["hitos"]) == 5          # MEDIA -> 5 hitos
    assert "ENAC" in ctx["garantia_text"] or ctx["garantia_text"]  # hay garantia
    assert ctx["cliente_firmante_nombre"] == "Ana Responsable"


# ══════════════════════════════════════════════════════════════════════════
# 2) Garantía por categoría (asyncio, 3 sub-cases vía fallback)
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "categoria,expected_tokens",
    [
        ("BASICA", ("BASICA",)),
        ("MEDIA", ("1.000", "1000")),
        ("ALTA", ("ALTA", "partner")),
    ],
)
async def test_agent_20_garantia_por_categoria(db, categoria, expected_tokens):
    """Fallback deterministico cubre las 3 categorias con texto distinto."""
    _, project_id, lead_id, proposal_id = await _seed_proposal(
        db, categoria=categoria, sector="sanidad",
        nombre=f"Cliente {categoria}",
    )
    agent = Agent20NegociadorContractual()
    # Forzar fallback mockeando invoke con respuesta invalida
    bad = {
        "response": "no-json",
        "parsed": None,
        "tokens_input": 50,
        "tokens_output": 20,
        "latency_ms": 5,
        "model": "sonnet-4.6",
    }
    with patch.object(
        Agent20NegociadorContractual, "invoke", new=AsyncMock(return_value=bad)
    ):
        result = await agent.generate_contract_clauses(
            db,
            proposal_id=proposal_id,
            cliente={"razon_social": f"Cliente {categoria}", "sector": "sanidad"},
            cliente_firmante_nombre="Test",
            cliente_firmante_cargo="Dir",
        )
    assert result["fallback_used"] is True
    draft = result["clauses_draft"]
    assert all(k in draft for k in REQUIRED_SECTIONS)
    # Garantia contiene el token esperado por categoria (presencia debil)
    joined_garantia_preambulo = (
        draft["garantia"] + " " + draft["preambulo"]
    )
    assert any(
        tok in joined_garantia_preambulo for tok in expected_tokens
    ), f"Ninguno de {expected_tokens} encontrado en garantia/preambulo (caso {categoria})"


# ══════════════════════════════════════════════════════════════════════════
# 3) Incompatibilidad SIEMPRE presente — incluso en fallback determinista
# ══════════════════════════════════════════════════════════════════════════


async def test_agent_20_incompatibilidad_siempre_presente(db):
    """La clausula de incompatibilidad (ISO 17065 + CCN-CERT IC-01/19) es
    obligatoria en toda C-001, tambien cuando el LLM falla y cae a fallback."""
    _, project_id, lead_id, proposal_id = await _seed_proposal(
        db, categoria="MEDIA", sector="sanidad", nombre="Demo Compat"
    )
    agent = Agent20NegociadorContractual()
    bad = {
        "response": "no json",
        "parsed": None,
        "tokens_input": 50, "tokens_output": 20, "latency_ms": 5, "model": "sonnet-4.6",
    }
    with patch.object(
        Agent20NegociadorContractual, "invoke", new=AsyncMock(return_value=bad)
    ):
        result = await agent.generate_contract_clauses(
            db,
            proposal_id=proposal_id,
            cliente={"razon_social": "Demo Compat", "sector": "sanidad"},
            cliente_firmante_nombre="Demo",
            cliente_firmante_cargo="Dir",
        )
    incomp = result["clauses_draft"]["incompatibilidad"].lower()
    assert "17065" in incomp, "Falta cita ISO 17065 en incompatibilidad"
    assert "ccn-cert" in incomp or "ic-01" in incomp, (
        "Falta cita CCN-CERT IC-01/19 en incompatibilidad"
    )
    assert "auditoria" in incomp or "auditoría" in incomp


# ══════════════════════════════════════════════════════════════════════════
# 4) Integración M14 ContractService con narrative_mode=llm (mock A20)
# ══════════════════════════════════════════════════════════════════════════


async def test_agent_20_m14_integration_narrative_mode_llm(db):
    """``ContractService.generate_contract_apendice_m`` con narrative_mode=
    'llm' persiste el draft A20 en ``parametros_xyzpr['llm_clauses']``."""
    _, project_id, lead_id, proposal_id = await _seed_proposal(
        db, categoria="MEDIA", sector="sanidad", nombre="Demo M14"
    )
    from backend.app.motors.m14_contracts.contract_service import ContractService

    fake_result = {
        "clauses_draft": {k: f"Seccion {k} OK" for k in REQUIRED_SECTIONS},
        "is_aapp": False,
        "validation": {"numbers_ok": True, "unknown_amounts": [], "retry_count": 0},
        "tokens_input": 800, "tokens_output": 3000,
        "cost_eur_estimated": 0.04, "latency_ms": 4000,
        "model": "sonnet-4.6", "fallback_used": False,
        "context_summary": {"categoria": "MEDIA"},
    }

    svc = ContractService()
    with patch.object(
        svc,
        "_generate_clauses_via_agent_20",
        new=AsyncMock(return_value=fake_result),
    ):
        contract = await svc.generate_contract_apendice_m(
            db,
            proposal_id=proposal_id,
            project_id=uuid.UUID(project_id),
            cliente={"cif": "B12345678", "razon_social": "Demo M14", "sector": "sanidad"},
            cliente_firmante_nombre="Firmante Demo",
            cliente_firmante_cargo="Director",
            narrative_mode="llm",
        )
    params = contract.parametros_xyzpr or {}
    assert "llm_clauses" in params
    assert params["llm_clauses"]["fallback_used"] is False
    assert all(
        k in params["llm_clauses"]["clauses_draft"] for k in REQUIRED_SECTIONS
    )


# ══════════════════════════════════════════════════════════════════════════
# 4b) Smoke E2E endpoint POST /contracts/projects/{id}/contracts/generate-llm
# ══════════════════════════════════════════════════════════════════════════


async def test_agent_20_endpoint_generate_llm_e2e(async_client, db):
    """Llama al endpoint HTTP real con mock del Agente 20 y comprueba shape
    del response (contract serializado + narrative_mode + agent_20_result)."""
    from backend.app.motors.m14_contracts.contract_service import ContractService

    _, project_id, lead_id, proposal_id = await _seed_proposal(
        db, categoria="MEDIA", sector="sanidad", nombre="E2E Endpoint Demo"
    )

    fake_result = {
        "clauses_draft": {k: f"[mock] {k}" for k in REQUIRED_SECTIONS},
        "is_aapp": False,
        "validation": {"numbers_ok": True, "unknown_amounts": [], "retry_count": 0},
        "tokens_input": 900,
        "tokens_output": 3200,
        "cost_eur_estimated": 0.042,
        "latency_ms": 4200,
        "model": "sonnet-4.6",
        "fallback_used": False,
        "context_summary": {"categoria": "MEDIA"},
    }
    with patch.object(
        ContractService,
        "_generate_clauses_via_agent_20",
        new=AsyncMock(return_value=fake_result),
    ):
        resp = await async_client.post(
            f"/api/v1/contracts/projects/{project_id}/contracts/generate-llm",
            json={
                "proposal_id": str(proposal_id),
                "cliente_firmante_nombre": "Firmante E2E",
                "cliente_firmante_cargo": "Director",
                "sector": "sanidad",
                "use_llm": True,
                "vigencia_meses": 12,
            },
        )

    assert resp.status_code == 201, resp.text
    data = resp.json()
    # Shape check (adaptado al endpoint real):
    assert "contract" in data
    assert "id" in data["contract"]
    assert data["narrative_mode"] == "llm"
    assert data["agent_20_result"] is not None
    # El payload A20 tiene los campos de tokens + coste
    a20 = data["agent_20_result"]
    assert a20["tokens_input"] == 900
    assert a20["tokens_output"] == 3200
    assert a20["cost_eur_estimated"] == 0.042
    assert a20["fallback_used"] is False
    assert all(k in a20["clauses_draft"] for k in REQUIRED_SECTIONS)


# ══════════════════════════════════════════════════════════════════════════
# 5) LLM real: rama AAPP (Ayuntamiento) cita LCSP + FACe + DIR3
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.llm
@pytest.mark.timeout(600)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_20_aapp_branch_lcsp_real_llm(db):
    """Ayuntamiento (CIF P) → LCSP 198.4 + FACe + DIR3 + 60 dias."""
    _skip_if_no_api_key()
    _, project_id, lead_id, proposal_id = await _seed_proposal(
        db,
        categoria="BASICA",
        sector="administracion publica",
        cif_prefix="P",
        nombre="Ayuntamiento de Villanueva",
        sistemas_en_alcance=1,
        sedes=1,
        dias_hasta_plazo=30,          # urgencia +30%
    )
    agent = Agent20NegociadorContractual()
    result = await agent.generate_contract_clauses(
        db,
        proposal_id=proposal_id,
        cliente={
            "cif": "P99999999",
            "razon_social": "Ayuntamiento de Villanueva",
            "tipo_organizacion": "Ayuntamiento",
            "sector": "administracion publica",
        },
        cliente_firmante_nombre="Alcalde Test",
        cliente_firmante_cargo="Alcalde",
    )

    assert result["fallback_used"] is False, (
        f"Fallback activado; retry={result['validation']['retry_count']} "
        f"unknown={result['validation']['unknown_amounts'][:3]}"
    )
    assert result["is_aapp"] is True

    draft = result["clauses_draft"]
    assert _total_length(draft) >= 1800, "Contrato AAPP demasiado corto"

    cuerpo = " ".join(v for v in draft.values() if isinstance(v, str))
    cuerpo_lower = cuerpo.lower()

    # LCSP: norma marco, tiene que aparecer >=2 veces (ley aplicable +
    # art. 198.4 plazo pago). Menos de 2 indica omision estructural.
    lcsp_count = cuerpo_lower.count("lcsp") + cuerpo_lower.count("ley 9/2017")
    assert lcsp_count >= 2, (
        f"LCSP/Ley 9/2017 debe citarse >=2 veces en contrato AAPP (real: {lcsp_count})"
    )

    # Art. 198.4 (plazo 60d AAPP) en clausula plazo pago
    assert (
        "198.4" in cuerpo_lower
        or "articulo 198" in cuerpo_lower
        or "artículo 198" in cuerpo_lower
    ), "Falta referencia Art. 198.4 LCSP (plazo pago 60d AAPP)"

    # Facturacion electronica AAPP: >=2 de 3 indicadores (FACe / DIR3 /
    # Facturae). Tolera variabilidad Sonnet sin perder deteccion de
    # omision estructural completa.
    face_present = "face" in cuerpo_lower
    dir3_present = "dir3" in cuerpo_lower or "dir 3" in cuerpo_lower
    facturae_present = "facturae" in cuerpo_lower
    fact_indicators = sum([face_present, dir3_present, facturae_present])
    assert fact_indicators >= 2, (
        f"Facturacion electronica AAPP insuficiente (>=2 de 3 esperados): "
        f"face={face_present} dir3={dir3_present} facturae={facturae_present}"
    )

    # Plazo 60 dias AAPP explicito
    assert "60" in cuerpo and (
        "dias" in cuerpo_lower or "días" in cuerpo_lower
    ), "Falta plazo '60 dias' explicito AAPP"

    # Incompatibilidad siempre presente (ISO 17065)
    incomp = draft["incompatibilidad"].lower()
    assert "17065" in incomp, "Incompatibilidad sin ISO 17065 (AAPP)"


# ══════════════════════════════════════════════════════════════════════════
# 6) LLM real: sector sanidad DPA Art. 28 RGPD
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.llm
@pytest.mark.timeout(600)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_20_sector_sanidad_dpa_art28_real_llm(db):
    """Sanidad privada → Art. 28 RGPD + datos de salud (Art. 9 RGPD)."""
    _skip_if_no_api_key()
    _, project_id, lead_id, proposal_id = await _seed_proposal(
        db,
        categoria="MEDIA",
        sector="sanidad",
        nombre="Hospital Sanitas Pro",
        sistemas_en_alcance=2,
        sedes=1,
        madurez_pct=45,
    )
    agent = Agent20NegociadorContractual()
    result = await agent.generate_contract_clauses(
        db,
        proposal_id=proposal_id,
        cliente={
            "cif": "B00000001",
            "razon_social": "Hospital Sanitas Pro",
            "sector": "sanidad",
        },
        cliente_firmante_nombre="Dr. Responsable",
        cliente_firmante_cargo="Director Medico",
    )
    assert result["fallback_used"] is False, (
        f"Fallback activado; retry={result['validation']['retry_count']} "
        f"unknown={result['validation']['unknown_amounts'][:3]}"
    )
    draft = result["clauses_draft"]
    joined = " ".join(v for v in draft.values() if isinstance(v, str)).lower()
    assert "art. 28" in joined or "art 28" in joined or "articulo 28" in joined, (
        "Falta Art. 28 RGPD en clausulas sanidad"
    )
    assert "rgpd" in joined, "Falta mencion RGPD"
    # Datos de salud (Art. 9) o categoría especial
    assert "salud" in joined or "art. 9" in joined or "categoria especial" in joined


# ══════════════════════════════════════════════════════════════════════════
# 7) LLM real: urgencia +30% justificada
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.llm
@pytest.mark.timeout(600)
@pytest.mark.flaky(reruns=2, reruns_delay=5)
async def test_agent_20_urgencia_30_percent_justified_real_llm(db):
    """Plazo 28 dias (<42 threshold) -> urgencia activada -> justificacion
    explicita en clausulas."""
    _skip_if_no_api_key()
    _, project_id, lead_id, proposal_id = await _seed_proposal(
        db,
        categoria="BASICA",
        sector="privado",
        cif_prefix="B",
        nombre="DataForma Urgente",
        dias_hasta_plazo=28,
    )
    agent = Agent20NegociadorContractual()
    result = await agent.generate_contract_clauses(
        db,
        proposal_id=proposal_id,
        cliente={"cif": "B20000001", "razon_social": "DataForma Urgente", "sector": "privado"},
        cliente_firmante_nombre="Firmante",
        cliente_firmante_cargo="Director",
    )
    assert result["fallback_used"] is False, (
        f"Fallback; retry={result['validation']['retry_count']}"
    )
    # Pricing snapshot debe traer urgency > 0
    assert result["context_summary"]["urgency"] > 0, (
        "Urgencia deberia estar activa con plazo 28d"
    )
    draft = result["clauses_draft"]
    joined = " ".join(v for v in draft.values() if isinstance(v, str)).lower()
    assert "urgencia" in joined or "plazo corto" in joined or "recargo" in joined, (
        "Falta justificacion de urgencia en clausulas"
    )


# ══════════════════════════════════════════════════════════════════════════
# 5) FASE B Path A · prompt_caching activation (2026-05-23)
# ══════════════════════════════════════════════════════════════════════════


class TestA20PromptCachingActivated:
    """A20 prompt_caching activation (FASE B Path A · OPS-045 40ª)."""

    def test_a20_enable_prompt_caching_flag_true(self):
        """Class-level flag activated · replicate pattern 8 agentes."""
        assert Agent20NegociadorContractual.ENABLE_PROMPT_CACHING is True

    @pytest.mark.asyncio
    async def test_a20_call_llm_propagates_enable_prompt_caching(self, patched_settings):
        """_call_llm pasa enable_prompt_caching=True a llm_router.complete()."""
        agent = Agent20NegociadorContractual()
        with patch(
            "backend.app.core.ai.llm_router.get_default_llm_router"
        ) as mock_get_router:
            mock_router = mock_get_router.return_value
            mock_resp = type("R", (), {
                "content": "{}",
                "model": "claude-sonnet-4-6",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "latency_ms": 100,
            })()
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
                model="sonnet-4.6",
                temperature=0.15,
                max_tokens=100,
            )
            assert captured.get("enable_prompt_caching") is True, (
                "A20 _call_llm debe propagar enable_prompt_caching=True"
            )

    @pytest.mark.asyncio
    async def test_a20_response_includes_cache_tokens_fields(self):
        """invoke() returned dict incluye cache_creation + cache_read_input_tokens."""
        agent = Agent20NegociadorContractual()
        with patch.object(
            Agent20NegociadorContractual,
            "_call_llm",
            new=AsyncMock(return_value={
                "text": '{"preambulo":"x"}',
                "tokens_input": 1000,
                "tokens_output": 200,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 3500,  # cache HIT
                "model": "claude-sonnet-4-6",
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
            assert result["cache_read_input_tokens"] == 3500, (
                "Cache HIT debe propagar cache_read_input_tokens=3500 al response"
            )
