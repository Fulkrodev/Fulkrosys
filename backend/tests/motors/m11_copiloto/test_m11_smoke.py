"""Smoke tests for Motor 11 — Copiloto LLM (m11_copiloto).

Production logic of Agent 14 lives in backend/app/agents/agent_14_copiloto/
(service.answer_question, citation validators, hybrid search). This module
keeps a minimal smoke check that the M11 router is importable and exposes
the expected endpoints, so the motor stays covered by the standard
backend/tests/motors/m11_copiloto/ layout.
"""

from backend.app.motors.m11_copiloto import api as m11_api


def test_m11_router_exists():
    assert hasattr(m11_api, "router")


def test_m11_router_has_routes():
    routes = m11_api.router.routes
    assert len(routes) > 0


def test_m11_router_prefix_is_copilot():
    # The router must be mounted under /copilot or /copiloto for the spec.
    prefix = getattr(m11_api.router, "prefix", "")
    assert "copil" in prefix.lower() or any(
        "copil" in getattr(r, "path", "").lower() for r in m11_api.router.routes
    )
