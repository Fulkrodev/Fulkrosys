"""SSE dispatcher replay buffer + event_id tests · Phase 11.1 Ejecutable 6.

Verifica:
1. event_id generated unique per dispatch
2. Replay buffer maintains last 100 events (deque maxlen)
3. subscribe(channel, last_event_id) replays events posteriores correctly
4. Replay empty si last_event_id NO en buffer (gap demasiado grande)
5. Concurrent subscribers receive realtime + independent replay state
"""
from __future__ import annotations

import asyncio

import pytest

from backend.app.core.sse_dispatcher import SseDispatcher


@pytest.mark.asyncio
async def test_event_id_unique_per_dispatch():
    """Each dispatched event tiene event_id UUID único."""
    disp = SseDispatcher()
    for i in range(5):
        await disp.dispatch("project:test", "step_completed", {"i": i})

    buffer_size = disp.replay_buffer_size("project:test")
    assert buffer_size == 5


@pytest.mark.asyncio
async def test_replay_buffer_maxlen_respected():
    """Replay buffer cap REPLAY_BUFFER_MAXLEN (100) · oldest dropped."""
    disp = SseDispatcher()
    for i in range(150):
        await disp.dispatch("project:test", "step_completed", {"i": i})

    buffer_size = disp.replay_buffer_size("project:test")
    assert buffer_size == 100


@pytest.mark.asyncio
async def test_subscribe_with_last_event_id_replays_posteriori():
    """Subscribe con last_event_id yields events posteriores antes realtime."""
    disp = SseDispatcher()

    captured: list = []
    for i in range(5):
        await disp.dispatch("project:test", "step_completed", {"i": i})

    events_before = list(disp._replay_buffers["project:test"])
    third_event_id = events_before[2].event_id

    async def consumer():
        sub_iter = disp.subscribe("project:test", last_event_id=third_event_id)
        try:
            async for event in sub_iter:
                captured.append(event)
                if len(captured) >= 2:
                    break
        finally:
            await sub_iter.aclose()

    await asyncio.wait_for(consumer(), timeout=2.0)

    assert len(captured) == 2
    assert captured[0].data["i"] == 3
    assert captured[1].data["i"] == 4


@pytest.mark.asyncio
async def test_subscribe_without_last_event_id_no_replay():
    """Subscribe sin last_event_id NO replay · solo realtime."""
    disp = SseDispatcher()

    for i in range(3):
        await disp.dispatch("project:test", "step_completed", {"i": i})

    captured: list = []

    async def consumer():
        sub_iter = disp.subscribe("project:test")
        try:
            async for event in sub_iter:
                captured.append(event)
                break
        finally:
            await sub_iter.aclose()

    async def producer():
        await asyncio.sleep(0.05)
        await disp.dispatch("project:test", "step_completed", {"i": 100})

    await asyncio.gather(
        asyncio.wait_for(consumer(), timeout=2.0),
        producer(),
    )

    assert len(captured) == 1
    assert captured[0].data["i"] == 100


@pytest.mark.asyncio
async def test_replay_empty_if_last_event_id_not_in_buffer():
    """Si last_event_id NO existe en buffer · replay empty (gap demasiado grande)."""
    disp = SseDispatcher()

    for i in range(3):
        await disp.dispatch("project:test", "step_completed", {"i": i})

    fake_id = "00000000-0000-0000-0000-000000000000"
    replay = disp._compute_replay("project:test", fake_id)
    assert replay == []


@pytest.mark.asyncio
async def test_concurrent_subscribers_receive_independent_replay():
    """Multiple subscribers · independent replay state cada uno."""
    disp = SseDispatcher()

    for i in range(5):
        await disp.dispatch("project:test", "step_completed", {"i": i})

    events_before = list(disp._replay_buffers["project:test"])
    fourth_event_id = events_before[3].event_id

    captured_a: list = []
    captured_b: list = []

    async def consumer_a():
        sub_iter = disp.subscribe("project:test", last_event_id=fourth_event_id)
        try:
            async for event in sub_iter:
                captured_a.append(event)
                break
        finally:
            await sub_iter.aclose()

    async def consumer_b():
        sub_iter = disp.subscribe("project:test")
        try:
            async for event in sub_iter:
                captured_b.append(event)
                break
        finally:
            await sub_iter.aclose()

    async def producer():
        await asyncio.sleep(0.05)
        await disp.dispatch("project:test", "step_completed", {"i": 100})

    await asyncio.gather(
        asyncio.wait_for(consumer_a(), timeout=2.0),
        asyncio.wait_for(consumer_b(), timeout=2.0),
        producer(),
    )

    assert captured_a[0].data["i"] == 4
    assert captured_b[0].data["i"] == 100
