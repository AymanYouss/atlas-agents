"""The ``atlas`` command-line interface."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from atlas import __version__
from atlas.config import get_settings

app = typer.Typer(help="Atlas: self-hosted multi-agent platform.", no_args_is_help=True)
console = Console()


@app.command()
def version() -> None:
    """Print the Atlas version."""
    console.print(f"atlas {__version__}")


@app.command()
def serve(
    host: str = typer.Option(None, help="Bind host (defaults to ATLAS_API_HOST)."),
    port: int = typer.Option(None, help="Bind port (defaults to ATLAS_API_PORT)."),
    reload: bool = typer.Option(False, help="Enable autoreload for development."),
) -> None:
    """Run the HTTP API with uvicorn."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "atlas.main:app",
        host=host or settings.api_host,
        port=port or settings.api_port,
        reload=reload,
    )


@app.command("mcp-server")
def mcp_server() -> None:
    """Expose Atlas's built-in tools as an MCP server over stdio."""
    from atlas.mcp.server import main as run_server

    run_server()


@app.command()
def run(
    goal: str = typer.Argument(..., help="The goal to accomplish."),
    auto_approve: bool = typer.Option(True, help="Auto-resolve approval gates."),
) -> None:
    """Run a goal end-to-end in-process and stream progress to the terminal."""
    asyncio.run(_run_goal(goal, auto_approve))


async def _run_goal(goal: str, auto_approve: bool) -> None:
    from atlas.graph.orchestrator import Orchestrator
    from atlas.observability.events import EventType, event_broker
    from atlas.persistence.repository import InMemoryRunRepository
    from atlas.schemas.run import RunConfig, RunStatus
    from atlas.service.run_manager import RunManager

    manager = RunManager(Orchestrator(), InMemoryRunRepository())
    config = RunConfig(auto_approve=auto_approve)
    record = await manager.create_run(goal, config=config)
    console.print(Panel(goal, title=f"Atlas run {record.id}", border_style="cyan"))
    manager.launch(record.id, goal, config)

    async def _print_events() -> None:
        async for ev in event_broker.subscribe(record.id):
            _render_event(ev)
            if ev.type in {EventType.REPORT_READY, EventType.ERROR}:
                break

    await _print_events()
    final = await manager.get_run(record.id)
    if final and final.report:
        console.rule("[bold cyan]Report")
        console.print(Markdown(final.report.get("body_markdown", "")))
        console.print(f"\n[dim]confidence: {final.report.get('confidence', 0):.0%}[/dim]")
    elif final and final.status is RunStatus.FAILED:
        console.print(f"[red]Run failed:[/red] {final.error}")


def _render_event(ev) -> None:
    from atlas.observability.events import EventType

    tag = {
        EventType.PLAN_CREATED: "[cyan]plan[/cyan]",
        EventType.STEP_STATUS: "[yellow]step[/yellow]",
        EventType.TOOL_CALL: "[magenta]tool[/magenta]",
        EventType.CRITIQUE: "[green]critic[/green]",
        EventType.GUARDRAIL: "[red]guardrail[/red]",
        EventType.AGENT_MESSAGE: "[blue]think[/blue]",
    }.get(ev.type)
    if tag is None:
        return
    detail = ev.payload.get("thought") or ev.payload.get("status") or ev.payload.get("tool") or ""
    console.print(f"{tag} {ev.step_id or ''} {detail}".strip())


if __name__ == "__main__":
    app()
