from __future__ import annotations

import asyncio

import pytest

from atlas.observability.events import EventBroker, EventType, RunEvent


@pytest.fixture
def broker() -> EventBroker:
    return EventBroker(replay_buffer_size=16)


async def test_publish_assigns_monotonic_seq(broker: EventBroker) -> None:
    e1 = await broker.publish(RunEvent(run_id="r1", type=EventType.RUN_CREATED))
    e2 = await broker.publish(RunEvent(run_id="r1", type=EventType.RUN_STATUS))
    assert (e1.seq, e2.seq) == (1, 2)


async def test_late_subscriber_gets_replay(broker: EventBroker) -> None:
    await broker.publish(RunEvent(run_id="r1", type=EventType.RUN_CREATED))
    await broker.publish(RunEvent(run_id="r1", type=EventType.PLAN_CREATED))

    received: list[RunEvent] = []
    agen = broker.subscribe("r1", replay=True)
    received.append(await asyncio.wait_for(agen.__anext__(), timeout=1))
    received.append(await asyncio.wait_for(agen.__anext__(), timeout=1))
    await agen.aclose()

    assert [e.type for e in received] == [EventType.RUN_CREATED, EventType.PLAN_CREATED]


async def test_live_fanout_to_multiple_subscribers(broker: EventBroker) -> None:
    a = broker.subscribe("r2", replay=False)
    b = broker.subscribe("r2", replay=False)
    # Prime both subscriptions so their queues are registered.
    await asyncio.sleep(0)
    task_a = asyncio.create_task(a.__anext__())
    task_b = asyncio.create_task(b.__anext__())
    await asyncio.sleep(0)

    await broker.publish(RunEvent(run_id="r2", type=EventType.AGENT_TOKEN))
    ea = await asyncio.wait_for(task_a, timeout=1)
    eb = await asyncio.wait_for(task_b, timeout=1)
    assert ea.type == eb.type == EventType.AGENT_TOKEN
    await a.aclose()
    await b.aclose()


async def test_replay_buffer_bounded(broker: EventBroker) -> None:
    for _ in range(40):
        await broker.publish(RunEvent(run_id="r3", type=EventType.HEARTBEAT))
    assert len(broker.replay("r3")) == 16
