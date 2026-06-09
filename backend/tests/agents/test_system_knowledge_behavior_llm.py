"""Ejecutable 8 · Pasada 19 · comportamiento prod-fiel del SYSTEM_KNOWLEDGE_BASE.

La Pasada 18 cableó el KB en los system-prompts y lo probó de forma DETERMINISTA
(el string está en el prompt). Eso NO prueba que el copiloto, ante una pregunta
real, RESPONDA citándolo y SIN inventar. Estos tests hacen llamadas LLM reales
(@pytest.mark.llm · NO corren en el gate normal) y verifican el comportamiento:

1. admin · pregunta de uso de plataforma → cita [Fulkro Plataforma] + sección real.
2. cliente · pregunta de portal → cita [Fulkro Plataforma] + cliente-mínimo (sin
   jerga: ni "RLS" ni "motor m…").
3. fuera del KB → NO inventa (deriva a Marcos por Chat/Mensajes).
4. normativa ENS → mantiene cita ENS (RD 311/2022 / CCN-STIC) · no confunde los
   planos (no respalda lo normativo con [Fulkro Plataforma]).

Imprime la respuesta completa de cada pregunta (Marcos quiere VER qué respondió).
Llama a los services directamente (bypass del rate-limit del endpoint · patrón de
test_corpus_gap_real_llm_does_not_hallucinate).
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.agents.copilot_admin_service import get_admin_llm_service
from backend.app.agents.copilot_cliente_service import (
    get_cliente_llm_service,
    llm_enabled,
)
from backend.tests.conftest import setup_test_project

pytestmark = pytest.mark.llm


def _require_llm():
    if not llm_enabled():
        pytest.skip("anthropic_api_key no configurada · test real-LLM se omite")


def _show(titulo: str, pregunta: str, resp: str, is_stub: bool) -> None:
    print(f"\n──────── {titulo} ────────")
    print(f"PREGUNTA: {pregunta}")
    print(f"STUB_FALLBACK: {is_stub}")
    print(f"RESPUESTA:\n{resp}\n")


async def _ask_admin(db, project_id, project_nombre, pregunta):
    svc = get_admin_llm_service()
    return await svc.generate_response(
        db, "chat_send",
        project_id=project_id, project_nombre=project_nombre,
        question=pregunta, step_template_id=None, step_title=None,
        fase_actual=None,
    )


async def _ask_cliente(db, project_id, pregunta):
    svc = get_cliente_llm_service()
    return await svc.generate_response(
        db, "chat_send",
        project_id=project_id, question=pregunta,
        step_template_id=None, step_title=None, fase_actual=None, concepto=None,
    )


# ── Caso 1 · admin cita [Fulkro Plataforma] con la sección correcta ──
@pytest.mark.asyncio
async def test_admin_cites_platform_with_correct_section(db):
    _require_llm()
    _, pid = await setup_test_project(db)
    pregunta = "¿Desde qué sección del portal sube el cliente una evidencia o documento?"
    resp, _hint, is_stub = await _ask_admin(db, uuid.UUID(pid), "Proyecto Demo", pregunta)
    _show("CASO 1 · admin · uso de plataforma", pregunta, resp, is_stub)

    assert not is_stub, "esperaba respuesta LLM real, no stub fallback"
    assert "[Fulkro Plataforma]" in resp, "no cita la fuente de plataforma"
    low = resp.lower()
    assert "subir" in low and "document" in low, "no señala la sección real 'Subir documentos'"


# ── Caso 2 · cliente cita + cliente-mínimo (sin jerga) ──
@pytest.mark.asyncio
async def test_cliente_cites_platform_and_stays_minimo(db):
    _require_llm()
    _, pid = await setup_test_project(db)
    pregunta = "¿Dónde puedo ver mi plan de adecuación del ENS?"
    resp, _hint, is_stub = await _ask_cliente(db, uuid.UUID(pid), pregunta)
    _show("CASO 2 · cliente · navegación portal", pregunta, resp, is_stub)

    assert not is_stub, "esperaba respuesta LLM real, no stub fallback"
    assert "[Fulkro Plataforma]" in resp, "no cita la fuente de plataforma"
    assert "plan" in resp.lower(), "no menciona el plan (sección 'Mi plan ENS')"
    # cliente-mínimo · R30-inverso: sin jerga ni internals.
    low = resp.lower()
    assert "rls" not in low, "filtró jerga técnica (RLS) al cliente"
    assert "motor m" not in low, "filtró internals (motor m…) al cliente"


# ── Caso 3 · fuera del KB → NO inventa (deriva a Marcos) ──
@pytest.mark.asyncio
async def test_cliente_out_of_kb_does_not_invent(db):
    _require_llm()
    _, pid = await setup_test_project(db)
    # Pregunta ADYACENTE a la plataforma pero NO cubierta por el KB (no es una
    # sección del portal): el KB cliente instruye "no inventes · sugiere escribir
    # a Marcos por Chat o Mensajes".
    pregunta = (
        "¿Puedo cambiar los colores y el logotipo de mi portal para que sean "
        "los de mi empresa?"
    )
    resp, _hint, is_stub = await _ask_cliente(db, uuid.UUID(pid), pregunta)
    _show("CASO 3 · cliente · fuera del KB (adyacente)", pregunta, resp, is_stub)

    assert not is_stub, "esperaba respuesta LLM real, no stub fallback"
    # NO inventa una capacidad inexistente · deriva al consultor (canal real).
    assert any(k in resp for k in ("Marcos", "Chat", "Mensajes")), \
        f"no deriva al consultor ante algo fuera del KB · resp={resp!r}"


# ── Caso 4 · normativa ENS → mantiene cita ENS, no confunde planos ──
@pytest.mark.asyncio
async def test_admin_normative_keeps_ens_citation(db):
    _require_llm()
    _, pid = await setup_test_project(db)
    pregunta = (
        "¿La categoría MEDIA del ENS exige auditoría por una entidad externa "
        "acreditada? Cítame la base normativa."
    )
    resp, _hint, is_stub = await _ask_admin(db, uuid.UUID(pid), "Proyecto Demo", pregunta)
    _show("CASO 4 · admin · normativa ENS", pregunta, resp, is_stub)

    assert not is_stub, "esperaba respuesta LLM real, no stub fallback"
    # Mantiene el plano normativo con cita ENS (R2) · no lo respalda con plataforma.
    assert ("RD 311/2022" in resp) or ("CCN-STIC" in resp), \
        "no mantiene la cita normativa ENS para una afirmación normativa"
