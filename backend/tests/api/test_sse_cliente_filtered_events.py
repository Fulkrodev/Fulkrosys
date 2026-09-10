"""Tests · SSE cliente endpoint con filter per audience (1.D.G.C v3.11).

Cubre:
- event_matches_audience cliente filter integration
- Audience filter semantic: cliente only step_* events
- step_completed con primary_actor=admin pasa para cliente
- step_completed con primary_actor=cliente NO pasa para cliente (NO spam own events)
- readiness_changed bloqueado para cliente
- alert_new bloqueado para cliente
- Generator filter pattern verify
"""
from __future__ import annotations

from backend.app.core.sse_dispatcher import event_matches_audience


# ============= Smoke · cliente endpoint filter logic =============


def test_cliente_filter_blocks_readiness_changed():
    """Admin-internal event NO debe llegar al cliente."""
    assert event_matches_audience(
        "readiness_changed", "cliente", {"primary_actor": "cliente"},
    ) is False


def test_cliente_filter_allows_phase_changed():
    """Ola 3 #14 · POLÍTICA NUEVA (2026-06-04): el cliente VE su progreso de
    fase (transparencia outcome-as-a-service). Antes bloqueado; revertido."""
    assert event_matches_audience(
        "phase_changed", "cliente", {"primary_actor": "cliente"},
    ) is True


def test_cliente_filter_blocks_alert_new():
    assert event_matches_audience(
        "alert_new", "cliente", {"primary_actor": "cliente"},
    ) is False


def test_cliente_filter_allows_step_completed_when_admin():
    """Cliente quiere saber cuando Marcos terminó."""
    assert event_matches_audience(
        "step_completed", "cliente", {"primary_actor": "admin"},
    ) is True


def test_cliente_filter_blocks_step_completed_own():
    """Cliente NO necesita re-recibir su propio completion event."""
    assert event_matches_audience(
        "step_completed", "cliente", {"primary_actor": "cliente"},
    ) is False


def test_cliente_filter_allows_step_unblocked_own():
    """Cliente recibe step_unblocked si LE TOCA actuar."""
    assert event_matches_audience(
        "step_unblocked", "cliente", {"primary_actor": "cliente"},
    ) is True


def test_cliente_filter_blocks_step_unblocked_admin_turn():
    """Cliente NO debe ver eventos que LE TOCA a Marcos."""
    assert event_matches_audience(
        "step_unblocked", "cliente", {"primary_actor": "admin"},
    ) is False


def test_cliente_filter_blocks_unknown_event():
    """Eventos custom desconocidos · safe-deny."""
    assert event_matches_audience(
        "custom_event", "cliente", {"primary_actor": "cliente"},
    ) is False


# ============= FIX P2-3 · gestor documental compartido (document.uploaded) =============


def test_cliente_filter_allows_document_uploaded_shared():
    """Documento normal (NO interno) → el cliente lo ve aparecer en realtime."""
    assert event_matches_audience(
        "document.uploaded", "cliente",
        {"source": "admin", "interno": False},
    ) is True


def test_cliente_filter_blocks_document_uploaded_interno():
    """Documento ``interno`` → NO se entrega al cliente (espejo de d.interno=false)."""
    assert event_matches_audience(
        "document.uploaded", "cliente",
        {"source": "admin", "interno": True},
    ) is False


def test_cliente_filter_document_uploaded_defaults_visible():
    """Sin flag ``interno`` en el payload → visible (default False · seguro)."""
    assert event_matches_audience(
        "document.uploaded", "cliente", {"source": "cliente"},
    ) is True


def test_admin_filter_allows_document_uploaded_even_interno():
    """El admin SIEMPRE ve los documentos nuevos, incluso los internos."""
    assert event_matches_audience(
        "document.uploaded", "admin", {"interno": True},
    ) is True


def test_admin_filter_allows_all_admin_events():
    """Admin SSE recibe TODOS los eventos canónicos."""
    for ev in (
        "readiness_changed", "phase_changed", "alert_new",
        "step_completed", "step_unblocked", "step_blocked",
        "document.uploaded",
    ):
        assert event_matches_audience(ev, "admin", {}) is True


def test_admin_filter_blocks_unknown_event():
    assert event_matches_audience(
        "custom_event", "admin", {},
    ) is False


# ============= Integration · endpoint mount via main app =============


def test_sse_client_endpoint_registered_in_main_app():
    """sse_client_events_router debe estar montado en /api/v1/client-portal/projects.

    Se consulta el esquema OpenAPI, no ``app.routes``. Desde FastAPI 0.141 el
    ``include_router`` ya no aplana las rutas en ``app.routes``: deja objetos
    ``_IncludedRouter`` y la resolucion es perezosa, asi que la comprobacion
    anterior (recorrer ``app.routes`` buscando ``.path``) devolvia solo las cuatro
    rutas propias de FastAPI —/openapi.json, /docs, /docs/oauth2-redirect,
    /redoc— y fallaba aunque el endpoint estuviera perfectamente montado.
    Medido el 2026-09-10 con fastapi 0.141.1 y starlette 1.6.0: el esquema
    declara 1.099 caminos, 86 de ellos bajo client-portal, incluido este.

    El esquema es ademas la definicion correcta de "superficie de la API": es lo
    que ve quien la consume, y no depende de como FastAPI organice sus rutas por
    dentro.
    """
    from backend.app.main import app

    caminos = app.openapi()["paths"]
    esperado = "/api/v1/client-portal/projects/{project_id}/events"
    assert esperado in caminos, (
        f"{esperado} no esta en el esquema OpenAPI "
        f"({len(caminos)} caminos declarados)"
    )
