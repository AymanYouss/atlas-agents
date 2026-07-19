"""Integration tests for the Postgres repository.

Marked ``integration`` and skipped when no database is reachable, so the unit
suite stays hermetic. Point ATLAS_DATABASE_URL at a test database to run these.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from atlas.config import get_settings
from atlas.persistence.db import Base, create_engine, session_factory
from atlas.persistence.records import EventRecord, RunRecord
from atlas.persistence.sql import SqlAlchemyRunRepository
from atlas.schemas.run import RunStatus

pytestmark = pytest.mark.integration


@pytest.fixture
async def repo():
    engine = create_engine(get_settings().database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        await engine.dispose()
        pytest.skip("Postgres not reachable")
    yield SqlAlchemyRunRepository(session_factory(engine))
    await engine.dispose()


async def test_roundtrip_and_status(repo: SqlAlchemyRunRepository) -> None:
    rec = RunRecord(id="run_sql_1", goal="integration goal")
    await repo.create(rec)
    fetched = await repo.get("run_sql_1")
    assert fetched is not None and fetched.goal == "integration goal"

    fetched.status = RunStatus.COMPLETED
    fetched.report = {"summary": "done"}
    await repo.update(fetched)
    reloaded = await repo.get("run_sql_1")
    assert reloaded.status is RunStatus.COMPLETED
    assert reloaded.report == {"summary": "done"}


async def test_event_persistence(repo: SqlAlchemyRunRepository) -> None:
    await repo.create(RunRecord(id="run_sql_2", goal="g"))
    for i in range(1, 4):
        await repo.append_event(EventRecord(run_id="run_sql_2", seq=i, type="agent_token"))
    events = await repo.list_events("run_sql_2", after_seq=1)
    assert [e.seq for e in events] == [2, 3]
