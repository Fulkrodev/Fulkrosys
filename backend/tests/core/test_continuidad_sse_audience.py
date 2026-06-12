"""Sync admin↔cliente · eventos SSE de continuidad BIA/DRP (feat/fulkro-100).

El cliente RELLENA el cuestionario / APRUEBA / COMENTA un borrador BIA/DRP →
el admin (Marcos) lo VE en realtime. Marcos prepara un borrador →
el cliente lo recibe (``continuidad.draft_ready``). Filosofía cliente-mínimo:
los eventos cliente-origin NO se eco-difunden de vuelta al cliente.
"""
from __future__ import annotations

from backend.app.core.sse_dispatcher import (
    ADMIN_EVENT_TYPES,
    CLIENTE_EVENT_TYPES,
    event_matches_audience,
)

_CLIENTE_ORIGIN = (
    "continuidad.questionnaire.submitted",
    "continuidad.draft.approved",
    "continuidad.draft.comment",
)


def test_cliente_origin_events_registered_admin_audience():
    for et in _CLIENTE_ORIGIN:
        assert et in ADMIN_EVENT_TYPES, et


def test_admin_sees_cliente_continuidad_actions_realtime():
    data = {"primary_actor": "cliente"}
    for et in _CLIENTE_ORIGIN:
        assert event_matches_audience(et, "admin", data) is True, et


def test_cliente_minimo_no_echo_back():
    # El cliente NO recibe el eco de sus propias acciones de continuidad.
    for et in _CLIENTE_ORIGIN:
        assert event_matches_audience(et, "cliente", {"primary_actor": "cliente"}) is False, et


def test_admin_origin_draft_ready_is_cliente_facing_only():
    assert "continuidad.draft_ready" in CLIENTE_EVENT_TYPES
    assert event_matches_audience("continuidad.draft_ready", "cliente", {"primary_actor": "admin"}) is True
    # Admin genera el borrador: no necesita el eco cliente-facing.
    assert event_matches_audience("continuidad.draft_ready", "admin", {}) is False


def test_audiences_remain_distinct_by_design():
    # El invariante: continuidad cliente-origin NO está en CLIENTE; draft_ready NO está en ADMIN.
    for et in _CLIENTE_ORIGIN:
        assert et not in CLIENTE_EVENT_TYPES, et
    assert "continuidad.draft_ready" not in ADMIN_EVENT_TYPES
