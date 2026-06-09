"""Tests for the agent framework (registry, base, prompts, API).

Sesion 9 (2026-04-23): tras auditoria STEP B, 10 agentes quedaron
deprecated (IDs 1, 3, 5, 7, 8, 13, 16, 22, 23, 24, 25 — el 13 ya
estaba descartado antes de STEP B). Los tests de este modulo
distinguen entre:

- ``AGENT_REGISTRY`` total (incluye activo + scaffolding +
  deprecated + reservado).
- ``list_active_agents()`` / ``_AGENT_CLASSES`` (solo activo +
  scaffolding — los importables).
"""
import uuid

import pytest

from backend.app.agents.api import _get_agent_class
from backend.app.agents.base import AgentBase, _resolve_model
from backend.app.agents.prompts.common_header import COMMON_HEADER
from backend.app.agents.registry import (
    AGENT_REGISTRY,
    get_agent_info,
    list_active_agents,
    list_agents,
)
from backend.tests.conftest import setup_test_project


# IDs activos + scaffolding (clases Python existen y son invocables).
# Hardcoded para detectar regresiones si alguien elimina / anade sin
# actualizar registry. Ajustar si se implementa un scaffolding (p.ej.
# TODO-A21-G1 o TODO-A27-G1) o si se deprecan/crean mas agentes.
# A31 anadido Sesion 9 Paso 2.7 (Enriquecedor DdA no_aplica).
# Sesion 10 cleanup Commit 2: A15 y A26 movidos a EXTERNALIZED_IDS
# (stubs eliminados, funcionalidad real vive en m23_retainer).
# Sesion 10 cleanup Commit 3: A2 movido a SCAFFOLDING_COVERED_IDS
# (mantiene stub + endpoint /2/analyze-pliego para promocion LLM
# futura); A28/A29/A30 movidos a DEPRECATED_IDS (cubiertos por
# M27/M28/M23 deterministas).
ACTIVE_OR_SCAFFOLDING_IDS = {
    4, 6, 11, 12, 14, 17, 18, 19, 20, 21, 27, 31,
}

SCAFFOLDING_COVERED_IDS = {2}  # Sesion 10: A2 Pliegos, promocion LLM futura

DEPRECATED_IDS = {1, 3, 5, 7, 8, 13, 16, 22, 23, 24, 25, 28, 29, 30}
RESERVED_IDS = {9, 10}
EXTERNALIZED_IDS = {15, 26}  # Sesion 10: funcion real en m23_retainer


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestAgentRegistry:
    def test_registry_contains_all_status_categories(self):
        assert len(AGENT_REGISTRY) == (
            len(ACTIVE_OR_SCAFFOLDING_IDS)
            + len(SCAFFOLDING_COVERED_IDS)
            + len(DEPRECATED_IDS)
            + len(RESERVED_IDS)
            + len(EXTERNALIZED_IDS)
        )

    def test_active_agents_match_expected(self):
        # list_active_agents incluye activo + scaffolding +
        # scaffolding_covered_by_engine (los 3 con clase importable).
        actual = {a["id"] for a in list_active_agents()}
        assert actual == ACTIVE_OR_SCAFFOLDING_IDS | SCAFFOLDING_COVERED_IDS

    def test_deprecated_ids_marked(self):
        for aid in DEPRECATED_IDS:
            info = AGENT_REGISTRY[aid]
            assert info["status"] == "deprecated", (
                f"Agent {aid} should be deprecated"
            )
            assert "deprecated_reason" in info, (
                f"Agent {aid} missing deprecated_reason"
            )

    def test_reserved_ids_marked(self):
        for aid in RESERVED_IDS:
            info = AGENT_REGISTRY[aid]
            assert info["status"] == "reservado"

    def test_externalized_ids_marked(self):
        for aid in EXTERNALIZED_IDS:
            info = AGENT_REGISTRY[aid]
            assert info["status"] == "externalized_to_motor", (
                f"Agent {aid} should be externalized_to_motor"
            )
            assert "external_location" in info, (
                f"Agent {aid} missing external_location"
            )
            assert "note" in info, f"Agent {aid} missing note"
            # external_location debe apuntar a modulo m23_retainer (o similar)
            assert "motors" in info["external_location"], (
                f"Agent {aid} external_location {info['external_location']!r} "
                "should reference a motor module"
            )

    def test_scaffolding_covered_ids_marked(self):
        for aid in SCAFFOLDING_COVERED_IDS:
            info = AGENT_REGISTRY[aid]
            assert info["status"] == "scaffolding_covered_by_engine", (
                f"Agent {aid} should be scaffolding_covered_by_engine"
            )
            assert "note" in info, f"Agent {aid} missing note"
            # Stub tiene valor comercial futuro — note debe explicarlo
            assert len(info["note"]) > 100, (
                f"Agent {aid} note too short — should explain future LLM promotion"
            )
            # Preserva metadata model/temperature para cuando se promueva
            assert "model" in info
            assert "temperature" in info

    def test_active_agents_have_required_fields(self):
        for aid in ACTIVE_OR_SCAFFOLDING_IDS:
            info = AGENT_REGISTRY[aid]
            assert "name" in info, f"Agent {aid} missing name"
            assert "model" in info, f"Agent {aid} missing model"
            assert "temperature" in info, f"Agent {aid} missing temperature"
            assert "description" in info, f"Agent {aid} missing description"
            assert info["model"] in (
                "sonnet-4.5",
                "sonnet-4.6",
                "opus-4",
                "opus-4.6",
                "opus-4.7",
                "haiku-4.5",
                # A21 Detector Discrepancias · semantic info preserved:
                # processor 100% deterministic R1 INVIOLABLE · NO LLM
                # (sostiene 1.D.A promoted scaffolding → activo · OPS-045 13ª).
                # Future-1.E.test-framework-a21-whitelist resolved 2026-05-24.
                "deterministic",
            ), f"Agent {aid} invalid model"
            assert 0.0 <= info["temperature"] <= 1.0, f"Agent {aid} invalid temperature"

    def test_list_agents_returns_sorted(self):
        agents = list_agents()
        assert len(agents) == len(AGENT_REGISTRY)
        ids = [a["id"] for a in agents]
        assert ids == sorted(ids)

    def test_get_agent_info_valid_active(self):
        info = get_agent_info(14)
        assert info["name"] == "Copiloto Conversacional"

    def test_get_agent_info_valid_deprecated(self):
        info = get_agent_info(16)
        assert info["status"] == "deprecated"

    def test_get_agent_info_unknown_id(self):
        assert get_agent_info(99) is None


# ---------------------------------------------------------------------------
# Common header
# ---------------------------------------------------------------------------

class TestCommonHeader:
    def test_common_header_exists(self):
        assert len(COMMON_HEADER) > 100

    def test_common_header_has_rules(self):
        assert "REGLAS NO NEGOCIABLES" in COMMON_HEADER
        assert "1." in COMMON_HEADER
        assert "5." in COMMON_HEADER

    def test_common_header_mentions_ens(self):
        assert "RD 311/2022" in COMMON_HEADER
        assert "Esquema Nacional de Seguridad" in COMMON_HEADER

    def test_common_header_anti_hallucination(self):
        assert "JAMAS inventes" in COMMON_HEADER
        assert "No encontrado en el corpus oficial" in COMMON_HEADER


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

class TestAgentInstantiation:
    @pytest.mark.parametrize("agent_id", sorted(ACTIVE_OR_SCAFFOLDING_IDS))
    def test_agent_instantiates(self, agent_id):
        agent_class = _get_agent_class(agent_id)
        assert agent_class is not None, f"Agent {agent_id} class not found"
        agent = agent_class()
        assert agent.AGENT_ID == agent_id
        assert len(agent.AGENT_NAME) > 0
        assert len(agent.system_prompt) > len(COMMON_HEADER)

    @pytest.mark.parametrize("agent_id", sorted(DEPRECATED_IDS))
    def test_deprecated_agent_has_no_class(self, agent_id):
        assert _get_agent_class(agent_id) is None

    @pytest.mark.parametrize("agent_id", sorted(EXTERNALIZED_IDS))
    def test_externalized_agent_has_no_class(self, agent_id):
        # Los agentes externalized_to_motor no tienen clase en
        # _AGENT_CLASSES: la funcion real vive en un motor distinto.
        assert _get_agent_class(agent_id) is None

    @pytest.mark.parametrize("agent_id", sorted(SCAFFOLDING_COVERED_IDS))
    def test_scaffolding_covered_agent_has_class(self, agent_id):
        # Los scaffolding_covered_by_engine SI tienen clase importable
        # (stub funcional con endpoint + prompt). Diferencia con
        # externalized_to_motor: aqui el stub mantiene valor como
        # base para promocion LLM futura.
        agent_class = _get_agent_class(agent_id)
        assert agent_class is not None, (
            f"Agent {agent_id} scaffolding_covered should have importable class"
        )
        agent = agent_class()
        assert agent.AGENT_ID == agent_id
        assert len(agent.SPECIFIC_PROMPT) > 50


# ---------------------------------------------------------------------------
# Specific prompts
# ---------------------------------------------------------------------------

class TestAgentPrompts:
    @pytest.mark.parametrize("agent_id", sorted(ACTIVE_OR_SCAFFOLDING_IDS))
    def test_agent_has_specific_prompt(self, agent_id):
        agent = _get_agent_class(agent_id)()
        assert len(agent.SPECIFIC_PROMPT) > 50, f"Agent {agent_id} prompt too short"
        assert agent.SPECIFIC_PROMPT != COMMON_HEADER

    def test_agent_14_mentions_rag_or_corpus(self):
        from backend.app.agents.agent_14_copiloto import CopilotoAgent

        agent = CopilotoAgent()
        text = agent.SPECIFIC_PROMPT.lower()
        assert "rag" in text or "corpus" in text

    def test_agent_27_mentions_idms_or_clasificar(self):
        from backend.app.agents.agent_27_clasificador import ClasificadorIDMSAgent

        agent = ClasificadorIDMSAgent()
        text = agent.SPECIFIC_PROMPT.lower()
        assert "idms" in text or "clasificar" in text or "clasifica" in text


# ---------------------------------------------------------------------------
# Model alias resolution
# ---------------------------------------------------------------------------

class TestModelAliases:
    def test_sonnet_alias(self):
        assert _resolve_model("sonnet-4.5") == "claude-sonnet-4-5"

    def test_opus_alias(self):
        assert _resolve_model("opus-4") == "claude-opus-4-6"

    def test_haiku_alias(self):
        assert _resolve_model("haiku-4.5") == "claude-haiku-4-5"

    def test_unknown_alias_passthrough(self):
        assert _resolve_model("custom-model") == "custom-model"


# ---------------------------------------------------------------------------
# Invocation (mock LLM path)
# ---------------------------------------------------------------------------

class _DummyAgent(AgentBase):
    AGENT_ID = 99
    AGENT_NAME = "Dummy Agent"
    MODEL = "sonnet-4.5"
    SPECIFIC_PROMPT = "Rol: agente dummy para pruebas unitarias del framework base."


@pytest.mark.asyncio
class TestAgentInvocation:
    async def test_invoke_returns_expected_structure(self, db):
        # Agente 17 (Cualificador Comercial) activo — reemplaza al A16
        # eliminado en STEP B.
        from backend.app.agents.agent_17_cualificador import CualificadorComercialAgent

        agent = CualificadorComercialAgent()
        result = await agent.invoke(db, user_message="test")
        for key in (
            "agent_id", "agent_name", "response", "model",
            "tokens_input", "tokens_output", "latency_ms", "citations", "project_id",
        ):
            assert key in result
        assert result["agent_id"] == 17

    async def test_invoke_with_project_id(self, db):
        # Agente 11 (Auditor Virtual) activo — reemplaza al A7 eliminado
        # en STEP B.
        from backend.app.agents.agent_11_auditor_virtual import AuditorInternoVirtualAgent

        _, project_id = await setup_test_project(db)
        agent = AuditorInternoVirtualAgent()
        result = await agent.invoke(
            db, project_id=uuid.UUID(project_id), user_message="test"
        )
        assert result["project_id"] == project_id

    async def test_citation_extraction(self, db):
        agent = _DummyAgent()
        citations = agent._extract_citations(
            "La medida [Anexo II op.acc.6] exige MFA segun [CCN-STIC 804 seccion 3.2]"
        )
        assert any("Anexo II op.acc.6" in c for c in citations)
        assert any("CCN-STIC 804" in c for c in citations)

    async def test_json_parse_with_fences(self, db):
        agent = _DummyAgent()
        assert agent._parse_json_response('```json\n{"key": "value"}\n```') == {"key": "value"}
        assert agent._parse_json_response('{"key": "value"}') == {"key": "value"}
        assert agent._parse_json_response("not json") is None

    async def test_mock_fallback_when_no_api_key(self, db, patched_settings):
        patched_settings(anthropic_api_key="")
        agent = _DummyAgent()
        result = await agent.invoke(db, user_message="ping")
        assert result["response"].startswith("[MOCK]")
        assert result["agent_id"] == 99


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAgentAPI:
    async def test_list_agents_returns_all_statuses(self, async_client):
        resp = await async_client.get("/api/v1/agents/")
        assert resp.status_code == 200
        data = resp.json()
        # Registry completo (activo + scaffolding + deprecated + reservado).
        assert data["total"] == len(AGENT_REGISTRY)
        assert len(data["agents"]) == len(AGENT_REGISTRY)

    async def test_get_agent_info_ok(self, async_client):
        resp = await async_client.get("/api/v1/agents/14")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Copiloto Conversacional"
        assert body["agent_id"] == 14

    async def test_get_agent_info_deprecated_still_returned(self, async_client):
        # Un id deprecated se devuelve (para que consumidores vean status)
        # pero el invoke rechaza con 410.
        resp = await async_client.get("/api/v1/agents/16")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "deprecated"

    async def test_get_agent_not_found(self, async_client):
        resp = await async_client.get("/api/v1/agents/99")
        assert resp.status_code == 404

    async def test_invoke_agent(self, async_client, db, patched_settings):
        patched_settings(anthropic_api_key="")
        _, project_id = await setup_test_project(db)
        # A17 Cualificador activo — reemplaza A16 eliminado.
        resp = await async_client.post(
            "/api/v1/agents/17/invoke",
            json={"project_id": project_id, "message": "Cualifica este lead"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_id"] == 17
        assert body["project_id"] == project_id

    async def test_invoke_deprecated_agent_returns_410(self, async_client):
        resp = await async_client.post(
            "/api/v1/agents/16/invoke", json={"message": "hi"}
        )
        assert resp.status_code == 410

    @pytest.mark.parametrize("agent_id", sorted(EXTERNALIZED_IDS))
    async def test_invoke_externalized_agent_returns_410(
        self, async_client, agent_id
    ):
        # Sesion 10 cleanup: A15/A26 devuelven 410 con puntero al
        # motor real (m23_retainer) en el campo detail.
        resp = await async_client.post(
            f"/api/v1/agents/{agent_id}/invoke", json={"message": "hi"}
        )
        assert resp.status_code == 410
        detail = resp.json().get("detail", "")
        assert "m23_retainer" in detail, (
            f"Agent {agent_id} detail {detail!r} should mention m23_retainer"
        )

    async def test_invoke_reserved_agent_returns_404(self, async_client):
        resp = await async_client.post(
            "/api/v1/agents/9/invoke", json={"message": "hi"}
        )
        assert resp.status_code == 404

    async def test_invoke_unknown_agent(self, async_client):
        resp = await async_client.post(
            "/api/v1/agents/999/invoke", json={"message": "hi"}
        )
        assert resp.status_code == 404
