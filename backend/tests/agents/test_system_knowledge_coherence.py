"""E-3 · Gate anti-drift del conocimiento de plataforma de los copilotos.

El conocimiento (system_knowledge.py) debe reflejar SIEMPRE el sistema real.
Estos tests fallan en CI si:
- el módulo auto-generado (hechos vivos) no está al día con el código, o
- el conocimiento no menciona una fase / sección de portal / agente real.

Así, cuando alguien añade una pantalla, una fase o un agente, está OBLIGADO a
regenerar (`python backend/scripts/generate_system_knowledge.py`) y el copiloto
queda al día automáticamente.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
GEN_PATH = ROOT / "backend/scripts/generate_system_knowledge.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("_gen_sysk", GEN_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_generated_module_is_up_to_date():
    """Drift gate: regenerar en memoria == módulo committeado."""
    gen = _load_generator()
    assert gen.OUT.exists(), "falta system_knowledge_generated.py · ejecuta el generador"
    committed = gen.OUT.read_text(encoding="utf-8").strip()
    fresh = gen.render_module().strip()
    assert committed == fresh, (
        "system_knowledge_generated.py desactualizado · ejecuta "
        "python backend/scripts/generate_system_knowledge.py"
    )


def test_all_phases_present_in_admin_knowledge():
    from backend.app.agents.system_knowledge import SYSTEM_KNOWLEDGE_ADMIN
    from backend.app.core.workflow_phase import WorkflowPhase

    for phase in WorkflowPhase.ordered():
        assert phase.value in SYSTEM_KNOWLEDGE_ADMIN, (
            f"fase '{phase.value}' ausente del conocimiento admin"
        )


def test_client_nav_present_in_cliente_knowledge():
    from backend.app.agents.system_knowledge import SYSTEM_KNOWLEDGE_CLIENTE

    gen = _load_generator()
    nav = gen._parse_nav_labels(gen.CLIENT_SIDEBAR, href_prefix="/client-portal")
    assert nav, "el parser no encontró nav del portal cliente"
    for label, _href in nav:
        assert label in SYSTEM_KNOWLEDGE_CLIENTE, (
            f"la sección de portal '{label}' no está en el conocimiento cliente "
            "· regenera el conocimiento"
        )


def test_admin_knowledge_lists_active_motors():
    from backend.app.agents.system_knowledge import SYSTEM_KNOWLEDGE_ADMIN

    # los hechos vivos listan los agentes activos con su motor
    assert SYSTEM_KNOWLEDGE_ADMIN.count("(motor m") >= 5


def test_check_mode_passes_on_committed_module():
    """El modo --check del generador no detecta drift sobre lo committeado."""
    gen = _load_generator()
    assert gen.main(["--check"]) == 0
