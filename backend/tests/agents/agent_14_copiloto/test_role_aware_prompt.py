"""Role-aware system prompt + screen/project-state injection (2026-06-09).

Verifica que agent_14 (el pipeline RAG compartido por el panel flotante admin y
el chat cliente) selecciona el conocimiento de plataforma correcto por rol, que
el prompt cliente sigue byte-idéntico (no rompe el corpus de coherencia) y que
el catálogo de pantallas + el estado de proyecto se inyectan cuando procede.
"""
import uuid

import pytest

from backend.app.agents.agent_14_copiloto.prompts import (
    SYSTEM_PROMPT,
    build_base_system_prompt,
)
from backend.app.agents.agent_14_copiloto.service import _build_system_prompt
from backend.app.agents.agent_14_copiloto.types import PageContext
from backend.app.agents.copilot_project_state import build_project_state_block


def test_cliente_base_prompt_is_byte_identical_to_legacy_constant():
    # Invariante: la variante cliente == SYSTEM_PROMPT histórico (no divergir el
    # prompt cliente · protege test_system_knowledge_coherence).
    assert build_base_system_prompt("cliente") == SYSTEM_PROMPT


def test_admin_and_cliente_prompts_carry_the_right_platform_knowledge():
    admin = build_base_system_prompt("admin")
    cliente = build_base_system_prompt("cliente")

    # Admin: encuadre interno Marcos + bloque de conocimiento ADMIN.
    assert "Copiloto interno de FULKRO para Marcos" in admin
    assert "CÓMO GUIAR A MARCOS" in admin
    # Admin NO debe llevar el encuadre cliente.
    assert "Copiloto ENS de la plataforma FULKRO, un asistente experto" not in admin

    # Cliente: encuadre cliente + menú del portal cliente.
    assert "Copiloto ENS de la plataforma FULKRO, un asistente experto" in cliente
    assert "Tu portal (menú real)" in cliente
    # Cliente NO debe llevar el encuadre admin.
    assert "Copiloto interno de FULKRO para Marcos" not in cliente


def test_admin_prompt_knows_the_whole_portal_map():
    # El copiloto admin debe conocer TODO el panel, no solo 42 pantallas:
    # las ~45 pestañas de proyecto + el selector de proyectos + el portal
    # compliance + el resto de rutas (auto-generado · drift-gated).
    admin = build_base_system_prompt("admin")
    assert "MENÚ DEL PROYECTO" in admin
    assert "/admin/projects/[id]/dda" in admin  # una pestaña de proyecto
    assert "MAPA COMPLETO DE PÁGINAS DEL PANEL ADMIN" in admin
    assert "/admin/projects" in admin           # selector de proyectos
    assert "/admin/compliance" in admin          # portal compliance


def test_unknown_role_falls_back_to_cliente():
    assert build_base_system_prompt("anything-else") == build_base_system_prompt(
        "cliente",
    )


def test_admin_screen_catalog_injected_from_url():
    # URL project-scoped admin → normaliza a /admin/projects/[id]/dda → inyecta
    # los botones de pantalla del screen_references_catalog admin.
    pc = PageContext(url=f"/admin/projects/{uuid.uuid4()}/dda")
    prompt = _build_system_prompt(pc, corpus_gap=False, role="admin")
    assert "Pantalla activa" in prompt
    assert "Botones/acciones disponibles en esta pantalla" in prompt


def test_cliente_screen_catalog_injected_from_url():
    # El copiloto cliente ahora conoce los botones de cada página de su portal.
    pc = PageContext(url="/client-portal/firmas-pendientes")
    prompt = _build_system_prompt(pc, corpus_gap=False, role="cliente")
    assert "Pantalla activa" in prompt
    assert "Firmar" in prompt  # etiqueta de botón friendly del catálogo cliente


def test_unknown_screen_does_not_inject_button_block():
    pc = PageContext(url="/admin/this-screen-does-not-exist")
    prompt = _build_system_prompt(pc, corpus_gap=False, role="admin")
    assert "Pantalla activa" not in prompt


def test_project_state_block_injected_verbatim_into_prompt():
    block = "## Estado actual del proyecto (datos EN VIVO de la plataforma)\n- Fase actual: adecuacion"
    pc = PageContext(project_state=block)
    prompt = _build_system_prompt(pc, corpus_gap=False, role="cliente")
    assert block in prompt


@pytest.mark.asyncio
async def test_project_state_block_empty_without_project_id():
    # Sin project_id → "" (degradación grácil · no toca DB).
    assert await build_project_state_block(None, None, "cliente") == ""
    assert await build_project_state_block(None, "not-a-uuid", "admin") == ""
