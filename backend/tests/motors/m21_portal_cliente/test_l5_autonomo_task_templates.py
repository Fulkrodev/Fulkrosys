"""L-5 (FRENTE L) · task templates del perfil autónomo (archetype
autonomo_individual) · incl. gate ALTA bloqueante + Art.11 acumulación roles.
Filtrado determinista por applicable_archetypes + size micro (sin DB)."""
from __future__ import annotations

from backend.app.motors.m21_portal_cliente.task_templates_loader import (
    get_enriched_steps_for_project,
    load_task_templates,
)


def test_l5_autonomo_templates_loaded():
    ids = [t.id for t in load_task_templates().templates]
    for tid in (
        "ENR_AUT_01_ROLES_ART11",
        "ENR_AUT_02_DECLARACION_PROPIA_BASICA",
        "ENR_AUT_03_GATE_ALTA_BLOQUEANTE",
    ):
        assert tid in ids


def test_l5_autonomo_alta_gets_alta_gate_and_roles():
    steps = get_enriched_steps_for_project({
        "categoria_objetivo": "ALTA",
        "archetype": "autonomo_individual",
        "tamano_empleados": "micro",
    })
    ids = {s.id for s in steps}
    assert "ENR_AUT_03_GATE_ALTA_BLOQUEANTE" in ids  # gate ALTA bloqueante
    assert "ENR_AUT_01_ROLES_ART11" in ids           # acumulación roles (ALL)


def test_l5_autonomo_basica_gets_self_declaration_not_alta_gate():
    steps = get_enriched_steps_for_project({
        "categoria_objetivo": "BASICA",
        "archetype": "autonomo_individual",
        "tamano_empleados": "micro",
    })
    ids = {s.id for s in steps}
    assert "ENR_AUT_02_DECLARACION_PROPIA_BASICA" in ids
    assert "ENR_AUT_03_GATE_ALTA_BLOQUEANTE" not in ids  # gate ALTA solo en ALTA


def test_l5_non_autonomo_excluded():
    steps = get_enriched_steps_for_project({
        "categoria_objetivo": "ALTA",
        "archetype": "saas_only",
        "tamano_empleados": "grande",
    })
    ids = {s.id for s in steps}
    assert not any(i.startswith("ENR_AUT_") for i in ids)
