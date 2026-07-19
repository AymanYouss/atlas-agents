"""FastAPI application factory.

On startup the app wires durable infrastructure — a Postgres-backed run
repository and a Postgres LangGraph checkpointer — and falls back to in-memory
equivalents when a database is not configured, so the same image runs both a
laptop demo and a production deployment.
"""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from atlas.api.routes import router
from atlas.config import get_settings
from atlas.graph.orchestrator import Orchestrator
from atlas.observability.logging import configure_logging, get_logger
from atlas.persistence.repository import InMemoryRunRepository, RunRepository
from atlas.service.run_manager import RunManager

log = get_logger("atlas.main")


async def _init_persistence(stack: AsyncExitStack) -> tuple[RunRepository, object | None]:
    """Return (repository, checkpointer). Falls back to in-memory on any failure."""
    settings = get_settings()
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from sqlalchemy import text

        from atlas.persistence.db import Base, create_engine, session_factory
        from atlas.persistence.sql import SqlAlchemyRunRepository

        engine = await stack.enter_async_context(_dispose(create_engine()))
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.run_sync(Base.metadata.create_all)
        repo: RunRepository = SqlAlchemyRunRepository(session_factory(engine))

        saver = await stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(settings.sync_database_url)
        )
        await saver.setup()
        log.info("persistence_ready", backend="postgres")
        return repo, saver
    except Exception as exc:  # no DB available -> ephemeral, single-process mode
        log.warning("persistence_fallback", backend="in-memory", reason=str(exc))
        return InMemoryRunRepository(), None


def _dispose(engine):
    @asynccontextmanager
    async def _cm():
        try:
            yield engine
        finally:
            await engine.dispose()

    return _cm()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level, json_output=settings.is_production)
    async with AsyncExitStack() as stack:
        repository, checkpointer = await _init_persistence(stack)
        orchestrator = Orchestrator(checkpointer=checkpointer, settings=settings)
        app.state.run_manager = RunManager(orchestrator, repository)
        app.state.ready = True
        log.info("atlas_started", env=settings.env)
        yield
        app.state.ready = False


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Atlas",
        version="0.4.0",
        description="Self-hosted, MCP-native multi-agent platform.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def readyz() -> dict:
        return {"ready": getattr(app.state, "ready", False)}

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
