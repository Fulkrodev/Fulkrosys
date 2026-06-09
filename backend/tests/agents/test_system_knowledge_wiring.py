"""Pasada 18 · SYSTEM_KNOWLEDGE_BASE wired en los copilotos.

Opción 1 (decisión Marcos): constante compacta derivada de
docs/SYSTEM_KNOWLEDGE_BASE.md inyectada en los system-prompts de A14 RAG
(runtime + spec) + cliente stub + admin stub. SIN ingestión en el corpus RAG
(el corpus normativo ENS se queda limpio). R2 intacto: las reglas de citas ENS
siguen vigentes; el conocimiento de plataforma se cita como [Fulkro Plataforma].

Tests deterministas de wiring (NO llamada LLM). La nav cliente se valida contra
los labels reales de frontend/components/layout/ClientSidebar.tsx.

Fuente: docs/SYSTEM_KNOWLEDGE_BASE.md + decisión Marcos Pasada 18.
"""
from __future__ import annotations

from backend.app.agents.system_knowledge import (
    PLATFORM_CITATION,
    SYSTEM_KNOWLEDGE_ADMIN,
    SYSTEM_KNOWLEDGE_CLIENTE,
)


# ── Constante ────────────────────────────────────────────────────────


def test_platform_citation_marker():
    assert PLATFORM_CITATION == "[Fulkro Plataforma]"


def test_cliente_block_uses_real_nav_labels():
    blk = SYSTEM_KNOWLEDGE_CLIENTE
    # Labels reales de ClientSidebar.tsx (NO inventados de memoria)
    for label in (
        "Mis tareas", "Firmas pendientes", "Subir documentos",
        "Mejoras propuestas", "Mi plan ENS", "Conexiones cloud",
    ):
        assert label in blk, f"falta label real {label!r}"
    assert "[Fulkro Plataforma]" in blk


def test_cliente_block_is_cliente_minimo():
    blk = SYSTEM_KNOWLEDGE_CLIENTE
    assert "cliente-mínimo" in blk.lower()
    # R30-inverso: nada de jerga/internals al cliente
    assert "RLS" not in blk
    assert "motor m" not in blk.lower()


def test_admin_block_fuller_with_citation_and_r2_note():
    blk = SYSTEM_KNOWLEDGE_ADMIN
    assert "[Fulkro Plataforma]" in blk
    assert "cliente-mínimo" in blk.lower()
    # Recordatorio R2: lo normativo se cita con fuente ENS
    assert "RD 311/2022" in blk


# ── A14 RAG prompt (runtime · lo que usa el FE) ──────────────────────


def test_a14_runtime_prompt_has_platform_knowledge_and_keeps_r2():
    from backend.app.agents.agent_14_copiloto.prompts import SYSTEM_PROMPT

    # Plataforma wired
    assert "CONOCIMIENTO DE PLATAFORMA" in SYSTEM_PROMPT
    assert "[Fulkro Plataforma]" in SYSTEM_PROMPT
    # R2: citas ENS obligatorias + fallback normativo intactos
    assert "RD 311/2022" in SYSTEM_PROMPT
    assert "CCN-STIC" in SYSTEM_PROMPT
    assert "No encontrado en el corpus oficial" in SYSTEM_PROMPT
    # Identidad Fulkro preservada (Ejecutable 7.6)
    assert "fulkro" in SYSTEM_PROMPT.lower()


def test_a14_spec_prompt_has_platform_knowledge():
    from backend.app.agents.prompts.agent_14_copiloto import PROMPT

    assert "CONOCIMIENTO DE PLATAFORMA" in PROMPT
    assert "[Fulkro Plataforma]" in PROMPT


# ── Stub services: el wiring existe en el código fuente ──────────────
# (El append ocurre en generate_response · runtime con LLM. La no-regresión
#  del comportamiento la cubre la suite de stubs existente.)


def test_stub_services_wire_platform_knowledge_in_source():
    import inspect

    from backend.app.agents import copilot_admin_service, copilot_cliente_service

    cli_src = inspect.getsource(copilot_cliente_service)
    adm_src = inspect.getsource(copilot_admin_service)
    assert "SYSTEM_KNOWLEDGE_CLIENTE" in cli_src
    assert "SYSTEM_KNOWLEDGE_ADMIN" in adm_src
