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


eval_app = typer.Typer(help="Run the benchmark / evaluation suites.")
app.add_typer(eval_app, name="eval")


@eval_app.command("run")
def eval_run(
    suite: str = typer.Option(
        "", help="Path to a suite YAML. Omit with --all to run every bundled suite."
    ),
    all_suites: bool = typer.Option(False, "--all", help="Run all bundled suites."),
    out: str = typer.Option("", help="Write the JSON report to this path."),
) -> None:
    """Execute a benchmark suite and print a scored summary."""
    asyncio.run(_eval(suite, all_suites, out))


async def _eval(suite: str, all_suites: bool, out: str) -> None:
    import json

    from rich.table import Table

    from atlas.eval.report import SuiteReport
    from atlas.eval.runner import EvalRunner
    from atlas.eval.suite import load_suite, suites_dir

    if all_suites:
        paths = sorted(suites_dir().glob("*.yaml"))
    elif suite:
        paths = [__import__("pathlib").Path(suite)]
    else:
        console.print("[red]Provide --suite <path> or --all[/red]")
        raise typer.Exit(1)

    runner = EvalRunner()
    reports: list[SuiteReport] = []
    for path in paths:
        loaded = load_suite(path)
        console.print(f"[cyan]Running suite[/cyan] {loaded.name} ({len(loaded.tasks)} tasks)...")
        report = await runner.run_suite(loaded)
        reports.append(report)
        _print_suite(report, Table)

    if out:
        payload = [
            r.summary_dict() | {"outcomes": [o.model_dump() for o in r.outcomes]} for r in reports
        ]
        __import__("pathlib").Path(out).write_text(json.dumps(payload, indent=2, default=str))
        console.print(f"[green]Wrote report to[/green] {out}")


def _print_suite(report, Table) -> None:
    table = Table(title=f"Suite: {report.suite}", header_style="bold cyan")
    table.add_column("task")
    table.add_column("category")
    table.add_column("pass", justify="center")
    table.add_column("score", justify="right")
    table.add_column("steps", justify="right")
    table.add_column("cites", justify="right")
    for o in report.outcomes:
        table.add_row(
            o.task_id,
            o.category,
            "[green]✓[/green]" if o.passed else "[red]✗[/red]",
            f"{o.score:.2f}",
            str(o.steps),
            str(o.citations),
        )
    console.print(table)
    console.print(
        f"[bold]Success rate:[/bold] {report.success_rate:.0%}  "
        f"[bold]mean score:[/bold] {report.mean_score:.2f}  "
        f"[bold]blocked injections:[/bold] {report.blocked_injections}\n"
    )


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
