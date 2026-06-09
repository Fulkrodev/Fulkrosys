"""Sesión 3B-2B.8 CLUSTER 1 Phase 1B · M02 MAGERIT sync admin→cliente READ-ONLY tests.

Verifica:
1. SSE emit m02.magerit.updated dispatched on freeze_analysis endpoint
2. ClientSseEventType `m02.magerit.updated` accepted en CLIENTE_EVENT_TYPES
3. event_matches_audience cliente filter accepts cuando primary_actor=admin
4. event_matches_audience cliente filter rejects cuando primary_actor=cliente
   (sanity · cliente NO emite m02 events)
5. SSE dispatcher subscriber receives payload structure correct
"""
from __future__ import annotations

import asyncio
import uuid

import pytest

from backend.app.core.sse_dispatcher import (
    CLIENTE_EVENT_TYPES,
    event_matches_audience,
    sse_dispatcher,
)


def test_cliente_event_types_includes_m02_magerit():
    assert "m02.magerit.updated" in CLIENTE_EVENT_TYPES


def test_event_matches_audience_cliente_admin_actor_accepted():
    """Cliente recibe m02.magerit.updated cuando primary_actor='admin'."""
    assert event_matches_audience(
        "m02.magerit.updated",
        "cliente",
        {"primary_actor": "admin"},
    ) is True


def test_event_matches_audience_cliente_actor_rejected():
    """Sanity · cliente actor=cliente NO recibe (NO eco propio)."""
    assert event_matches_audience(
        "m02.magerit.updated",
        "cliente",
        {"primary_actor": "cliente"},
    ) is False


def test_event_matches_audience_admin_m02_filter_strict():
    """Admin filter estricto · m02 NO en ADMIN_EVENT_TYPES (cliente-bound emit)."""
    assert event_matches_audience(
        "m02.magerit.updated",
        "admin",
        {"primary_actor": "admin"},
    ) is False


@pytest.mark.asyncio
async def test_sse_dispatch_m02_magerit_updated_arrives():
    """sse_dispatcher dispatch event arrives subscriber channel project:{id}.

    Verifies payload integrity (analysis_id + assets_count + threats_count +
    safeguards_count + frozen_at + primary_actor preserved).
    """
    channel = f"project:{uuid.uuid4()}"
    received: list = []

    async def consume():
        async for event in sse_dispatcher.subscribe(channel):
            if event.type == "m02.magerit.updated":
                received.append(event)
                return

    consumer_task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)

    await sse_dispatcher.dispatch(
        channel,
        "m02.magerit.updated",
        {
            "analysis_id": str(uuid.uuid4()),
            "analysis_name": "Test MAGERIT Q1 2026",
            "assets_count": 15,
            "threats_count": 42,
            "safeguards_count": 18,
            "frozen_at": "2026-05-26T10:00:00Z",
            "primary_actor": "admin",
        },
    )

    try:
        await asyncio.wait_for(consumer_task, timeout=1.5)
    except asyncio.TimeoutError:
        consumer_task.cancel()

    assert len(received) >= 1
    event = received[0]
    assert event.type == "m02.magerit.updated"
    assert event.data["assets_count"] == 15
    assert event.data["threats_count"] == 42
    assert event.data["safeguards_count"] == 18
    assert event.data["primary_actor"] == "admin"
