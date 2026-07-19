from __future__ import annotations

import pytest

from atlas.persistence.records import EventRecord, RunRecord
from atlas.persistence.repository import InMemoryRunRepository
from atlas.schemas.run import RunStatus


@pytest.fixture
def repo() -> InMemoryRunRepository:
    return InMemoryRunRepository()


async def test_create_get_update(repo: InMemoryRunRepository) -> None:
    rec = RunRecord(id="run_1", goal="g")
    await repo.create(rec)
    fetched = await repo.get("run_1")
    assert fetched is not None and fetched.goal == "g"

    fetched.status = RunStatus.COMPLETED
    await repo.update(fetched)
    assert (await repo.get("run_1")).status is RunStatus.COMPLETED


async def test_get_missing_returns_none(repo: InMemoryRunRepository) -> None:
    assert await repo.get("nope") is None


async def test_list_orders_newest_first(repo: InMemoryRunRepository) -> None:
    await repo.create(RunRecord(id="a", goal="a"))
    await repo.create(RunRecord(id="b", goal="b"))
    runs = await repo.list_runs()
    assert {r.id for r in runs} == {"a", "b"}


async def test_events_replay_after_seq(repo: InMemoryRunRepository) -> None:
    for i in range(1, 6):
        await repo.append_event(EventRecord(run_id="run_1", seq=i, type="agent_token"))
    assert [e.seq for e in await repo.list_events("run_1", after_seq=3)] == [4, 5]


async def test_isolation_of_returned_copies(repo: InMemoryRunRepository) -> None:
    rec = RunRecord(id="run_1", goal="g")
    await repo.create(rec)
    got = await repo.get("run_1")
    got.goal = "mutated"  # mutating the returned copy must not affect storage
    assert (await repo.get("run_1")).goal == "g"
