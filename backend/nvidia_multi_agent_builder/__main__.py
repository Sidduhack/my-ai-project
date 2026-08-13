"""CLI entry point."""

from __future__ import annotations

import asyncio
import sys

import typer
from rich.console import Console
from rich.table import Table

from nvidia_multi_agent_builder.config import settings, configure_logging
from nvidia_multi_agent_builder.db import init_db, close_db
from nvidia_multi_agent_builder.agents import agent_registry, register_all_agents, AgentType
from nvidia_multi_agent_builder.models import provider_registry, health_tracker, scoring_engine
from nvidia_multi_agent_builder.orchestration import orchestrator

app = typer.Typer(
    name="nvidia-multi-agent-builder",
    help="NVIDIA Multi-Agent Builder CLI",
    add_completion=False,
)

console = Console()


@app.callback()
def main(
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Log level"),
    log_format: str = typer.Option("json", "--log-format", help="Log format (json/console)"),
):
    """NVIDIA Multi-Agent Builder - AI Multi-Agent Development Platform."""
    if debug:
        log_level = "DEBUG"
    configure_logging(log_level=log_level, log_format=log_format)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of workers"),
):
    """Start the API server."""
    import uvicorn

    console.print(f"[green]Starting server on {host}:{port}[/green]")

    uvicorn.run(
        "nvidia_multi_agent_builder.api.main:create_app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,
        factory=True,
    )


@app.command()
def init_db_command():
    """Initialize database tables."""
    async def _init():
        await init_db()
        console.print("[green]Database initialized successfully[/green]")
        await close_db()

    asyncio.run(_init())


@app.command()
def migrate(
    message: str = typer.Option("", "--message", "-m", help="Migration message"),
    autogenerate: bool = typer.Option(True, "--autogenerate/--no-autogenerate", help="Auto-generate migration"),
):
    """Create a new database migration."""
    import subprocess

    cmd = ["uv", "run", "alembic", "revision"]
    if autogenerate:
        cmd.append("--autogenerate")
    if message:
        cmd.extend(["-m", message])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        console.print("[green]Migration created successfully[/green]")
        console.print(result.stdout)
    else:
        console.print("[red]Migration failed[/red]")
        console.print(result.stderr)
        sys.exit(1)


@app.command()
def upgrade(revision: str = typer.Argument("head", help="Revision to upgrade to")):
    """Apply database migrations."""
    import subprocess

    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", revision],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        console.print("[green]Migrations applied successfully[/green]")
        console.print(result.stdout)
    else:
        console.print("[red]Migration failed[/red]")
        console.print(result.stderr)
        sys.exit(1)


@app.command()
def downgrade(revision: str = typer.Argument("-1", help="Revision to downgrade to")):
    """Revert database migrations."""
    import subprocess

    result = subprocess.run(
        ["uv", "run", "alembic", "downgrade", revision],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        console.print("[green]Migrations reverted successfully[/green]")
        console.print(result.stdout)
    else:
        console.print("[red]Downgrade failed[/red]")
        console.print(result.stderr)
        sys.exit(1)


@app.command()
def config():
    """Show current configuration."""
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    for key, value in settings.model_dump().items():
        if isinstance(value, str) and "key" in key.lower():
            value = "***REDACTED***"
        table.add_row(key, str(value))

    console.print(table)


@app.command()
def version():
    """Show version information."""
    from nvidia_multi_agent_builder import __version__, __author__, __license__

    console.print(f"NVIDIA Multi-Agent Builder v{__version__}")
    console.print(f"Author: {__author__}")
    console.print(f"License: {__license__}")


# Agent commands
agent_app = typer.Typer(help="Agent management commands")
app.add_typer(agent_app, name="agent")


@agent_app.command("list")
def agent_list():
    """List all agent types."""
    register_all_agents()
    table = Table(title="Registered Agents")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Description", style="yellow")

    for at in AgentType:
        agents = agent_registry.get_agents_by_type(at)
        if agents:
            for a in agents:
                table.add_row(at.value, a.name, a.description or "")
        else:
            table.add_row(at.value, at.value.replace("_", " ").title(), "")

    console.print(table)


@agent_app.command("create")
def agent_create(
    agent_type: AgentType = typer.Argument(..., help="Agent type"),
    name: str = typer.Option(None, "--name", "-n", help="Agent name"),
    description: str = typer.Option(None, "--description", "-d", help="Description"),
):
    """Create an agent instance."""
    register_all_agents()
    agent_id = name or f"{agent_type.value}-{__import__('uuid').uuid4().hex[:8]}"
    agent = agent_registry.create_agent(agent_type, agent_id=agent_id)
    console.print(f"[green]Created agent: {agent.agent_id}[/green]")


# Model commands
model_app = typer.Typer(help="Model management commands")
app.add_typer(model_app, name="model")


@model_app.command("list")
def model_list(
    provider: str = typer.Option(None, "--provider", "-p", help="Filter by provider"),
):
    """List available models."""
    async def _list():
        models = await provider_registry.get_all_models()
        if provider:
            models = {provider: models.get(provider, [])}

        for prov, mod_list in models.items():
            if not mod_list:
                continue
            table = Table(title=f"Provider: {prov}")
            table.add_column("Model ID", style="cyan")
            table.add_column("Display Name", style="green")
            table.add_column("Capabilities", style="yellow")
            table.add_column("Context", style="magenta")
            for m in mod_list:
                table.add_row(m.id, m.display_name, ", ".join(m.capabilities), str(m.context_window))
            console.print(table)

    asyncio.run(_list())


@model_app.command("health")
def model_health():
    """Show model health status."""
    health_data = health_tracker.get_all_health()
    table = Table(title="Model Health")
    table.add_column("Model", style="cyan")
    table.add_column("Provider", style="green")
    table.add_column("State", style="yellow")
    table.add_column("Success", style="blue")
    table.add_column("Failures", style="red")
    table.add_column("Avg Latency", style="magenta")
    table.add_column("Available", style="cyan")

    for key, health in health_data.items():
        state_style = {
            "healthy": "green",
            "degraded": "yellow",
            "cooldown": "red",
        }.get(health.state.value, "white")
        table.add_row(
            health.model_id,
            health.provider,
            f"[{state_style}]{health.state.value}[/{state_style}]",
            str(health.success_count),
            str(health.failure_count),
            f"{health.get_avg_latency():.1f}ms",
            "Yes" if health.is_available() else "No",
        )

    console.print(table)


@model_app.command("scores")
def model_scores(
    agent_type: AgentType = typer.Option(None, "--agent", "-a", help="Filter by agent type"),
):
    """Show adaptive model scores."""
    if agent_type:
        scores = scoring_engine.get_all_scores(agent_type.value)
    else:
        scores = []
        for at in AgentType:
            scores.extend(scoring_engine.get_all_scores(at.value))

    table = Table(title="Model Scores")
    table.add_column("Agent", style="cyan")
    table.add_column("Model", style="green")
    table.add_column("Total", style="yellow")
    table.add_column("Reliability", style="blue")
    table.add_column("Latency", style="magenta")
    table.add_column("Confidence", style="green")
    table.add_column("Samples", style="white")

    for s in sorted(scores, key=lambda x: x.total_score, reverse=True):
        table.add_row(
            s.agent_type,
            s.model_id,
            f"{s.total_score:.3f}",
            f"{s.reliability_score:.3f}",
            f"{s.latency_score:.3f}",
            f"{s.confidence_score:.3f}",
            str(s.sample_count),
        )

    console.print(table)


# Project commands
project_app = typer.Typer(help="Project management commands")
app.add_typer(project_app, name="project")


@project_app.command("create")
def project_create(
    name: str = typer.Argument(..., help="Project name"),
    description: str = typer.Option(None, "--description", "-d", help="Project description"),
):
    """Create a new project."""
    async def _create():
        project = await orchestrator.create_project(name, description)
        console.print(f"[green]Created project: {project.id}[/green]")
        console.print(f"Name: {project.name}")
        console.print(f"Status: {project.status}")

    asyncio.run(_create())


@project_app.command("start")
def project_start(
    project_id: str = typer.Argument(..., help="Project ID"),
):
    """Start a project."""
    async def _start():
        await orchestrator.start_project(project_id)
        console.print(f"[green]Started project: {project_id}[/green]")

    asyncio.run(_start())


@project_app.command("status")
def project_status(
    project_id: str = typer.Argument(..., help="Project ID"),
):
    """Get project status."""
    async def _status():
        status = await orchestrator.get_project_status(project_id)
        if "error" in status:
            console.print(f"[red]{status['error']}[/red]")
            return

        console.print(f"[bold]Project:[/bold] {status['name']} ({status['project_id']})")
        console.print(f"[bold]Status:[/bold] {status['status']}")
        console.print(f"[bold]Tasks:[/bold] {len(status['tasks'])}")

        table = Table(title="Tasks")
        table.add_column("ID", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Description", style="yellow")
        table.add_column("Status", style="blue")
        table.add_column("Priority", style="magenta")

        for t in status['tasks']:
            status_style = {
                "pending": "yellow",
                "running": "blue",
                "completed": "green",
                "failed": "red",
                "blocked": "orange",
                "cancelled": "gray",
            }.get(t['status'], "white")
            table.add_row(
                t['id'][:8],
                t['agent_id'],
                t['description'][:50],
                f"[{status_style}]{t['status']}[/{status_style}]",
                t['priority'],
            )

        console.print(table)

    asyncio.run(_status())


if __name__ == "__main__":
    app()