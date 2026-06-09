"""Tests SseDispatcher in-memory pub-sub (MB-13.3 · ADR-035).

Cobertura:
- Subscriber recibe events del channel
- Multiple subscribers reciben el mismo event
- Dispatch sin subscribers no error (no-op)
- Subscriber cleanup al cancelar (no leak channel entry)
- subscriber_count refleja realidad
"""
import asyncio

import pytest

from backend.app.core.sse_dispatcher import SseDispatcher, SseEvent, sse_dispatcher


@pytest.mark.asyncio
async def test_dispatch_to_subscriber():
    dispatcher = SseDispatcher()

    received: list[SseEvent] = []

    async def consumer():
        async for event in dispatcher.subscribe("test:single"):
            received.append(event)
            return  # consume one and exit

    consumer_task = asyncio.create_task(consumer())
    await asyncio.sleep(0.05)

    await dispatcher.dispatch("test:single", "test_event", {"key": "value"})
    await asyncio.wait_for(consumer_task, timeout=2.0)

    assert len(received) == 1
    assert received[0].type == "test_event"
    assert received[0].data == {"key": "value"}
    assert received[0].timestamp  # ISO timestamp set


@pytest.mark.asyncio
async def test_multiple_subscribers_receive_event():
    dispatcher = SseDispatcher()

    received_a: list[SseEvent] = []
    received_b: list[SseEvent] = []

    async def consume(target: list[SseEvent]):
        async for event in dispatcher.subscribe("test:multi"):
            target.append(event)
            return

    task_a = asyncio.create_task(consume(received_a))
    task_b = asyncio.create_task(consume(received_b))
    await asyncio.sleep(0.05)

    await dispatcher.dispatch("test:multi", "event", {"data": 1})
    await asyncio.gather(task_a, task_b)

    assert len(received_a) == 1
    assert len(received_b) == 1
    assert received_a[0].data == received_b[0].data == {"data": 1}


@pytest.mark.asyncio
async def test_dispatch_no_subscribers_noop():
    """Dispatch sin subscribers · no error y no leak."""
    dispatcher = SseDispatcher()
    # No raise expected
    await dispatcher.dispatch("test:empty", "ev", {})
    assert dispatcher.subscriber_count("test:empty") == 0


@pytest.mark.asyncio
async def test_subscriber_count_reflects_reality():
    """``subscriber_count(channel)`` track activos · sin leak post-cancel."""
    dispatcher = SseDispatcher()

    async def long_consumer():
        async for _event in dispatcher.subscribe("test:count"):
            return

    task = asyncio.create_task(long_consumer())
    await asyncio.sleep(0.05)
    assert dispatcher.subscriber_count("test:count") == 1

    task.cancel()
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass

    # After cancel + cleanup finally clause, channel cleared
    await asyncio.sleep(0.05)
    assert dispatcher.subscriber_count("test:count") == 0


def test_global_singleton_is_sse_dispatcher_instance():
    """``sse_dispatcher`` exportado es la instancia singleton."""
    assert isinstance(sse_dispatcher, SseDispatcher)
