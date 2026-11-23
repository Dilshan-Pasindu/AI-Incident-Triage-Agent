"""
agent-client/cli.py

Rich-powered Terminal User Interface for the Incident Triage & Release Readiness Agent.
Renders real-time telemetry, tool invocation panels, execution durations, and final diagnosis.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from incident_agent.agent import run_query
from incident_agent.cancellation import CancellationToken
from incident_agent.events import (
    BaseAgentEvent,
    FinalAnswerEvent,
    LlmTurnEvent,
    RunStartedEvent,
    RunStoppedEvent,
    ToolFinishedEvent,
    ToolStartedEvent,
    ToolStatus,
)
from incident_agent.mcp_client import MCPHub

from incident_agent.paths import RUST_BINARY, MOCK_DATA_DIR, WORKSPACE_DIR
from dotenv import load_dotenv
load_dotenv()
console = Console()


class RichCliHandler:
    def __init__(self):
        self.tool_start_times = {}

    def handle_event(self, event: BaseAgentEvent) -> None:
        if isinstance(event, RunStartedEvent):
            console.print(f"[bold cyan]▶ Starting run {event.run_id[:8]}...[/bold cyan]")

        elif isinstance(event, LlmTurnEvent):
            console.print(
                f"[dim]Turn {event.iteration}: LLM latency {event.latency_ms:.1f}ms, generated {event.tool_calls_count} tool call(s)[/dim]"
            )

        elif isinstance(event, ToolStartedEvent):
            server_style = "bold magenta" if event.server == "ops" else "bold green"
            mut_tag = " [bold red][MUTATING][/bold red]" if event.is_mutating else ""
            args_str = json.dumps(event.arguments)
            if len(args_str) > 80:
                args_str = args_str[:77] + "..."
            console.print(
                f"  [{server_style}][{event.server}][/{server_style}] [bold yellow]{event.tool}[/bold yellow]{mut_tag} ({args_str})"
            )

        elif isinstance(event, ToolFinishedEvent):
            status_style = {
                ToolStatus.OK: "bold green",
                ToolStatus.ERROR: "bold red",
                ToolStatus.TIMEOUT: "bold yellow",
                ToolStatus.REJECTED: "bold red",
                ToolStatus.BLOCKED: "bold red",
                ToolStatus.INVALID: "bold red",
            }.get(event.status, "white")

            console.print(
                f"    ↳ [{status_style}]{event.status.value.upper()}[/{status_style}] in {event.duration_ms:.1f}ms"
            )

        elif isinstance(event, FinalAnswerEvent):
            console.print("\n")
            console.print(
                Panel(
                    Markdown(event.answer),
                    title="[bold green]Incident Diagnosis & Final Answer[/bold green]",
                    border_style="green",
                )
            )

            # Summary stats table
            table = Table(title="Execution Summary", border_style="dim")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="magenta")
            table.add_row("Total Iterations", str(event.iterations))
            table.add_row("Tools Used", ", ".join(event.tools_used) or "None")
            table.add_row("Total Duration", f"{event.duration_ms:.1f}ms")
            console.print(table)

        elif isinstance(event, RunStoppedEvent):
            if event.reason != "completed":
                console.print(f"\n[bold yellow]Run stopped: {event.reason} ({event.error or ''})[/bold yellow]")


async def main():
    parser = argparse.ArgumentParser(description="AI Incident Triage & Release Readiness CLI")
    parser.add_argument("--max-iterations", type=int, default=8, help="Maximum agent reasoning steps")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve mutating actions (eval mode)")
    parser.add_argument("--trace-file", type=str, default=None, help="Path to write JSONL execution trace")
    parser.add_argument("query", nargs="*", help="Query to run non-interactively")
    args = parser.parse_args()

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ops_bin = str(RUST_BINARY)
    workspace = str(WORKSPACE_DIR)
    data_dir = str(MOCK_DATA_DIR)

    console.print(
        Panel.fit(
            "[bold white]Incident Triage & Release Readiness AI Agent[/bold white]\n"
            "[dim]Powered by Rust MCP Server + Node Filesystem + Grok Tool Calling[/dim]",
            border_style="cyan",
        )
    )

    console.print("[dim]Initializing MCPHub and connecting to servers...[/dim]")
    hub = MCPHub(ops_binary_path=ops_bin, workspace_dir=workspace, data_dir=data_dir)
    await hub.start()
    console.print(
        f"[green]✓ Connected to ops server ({hub.connections['ops'].health.value}) and fs server ({hub.connections['fs'].health.value})[/green]\n"
    )

    handler = RichCliHandler()

    try:
        if args.query:
            user_input = " ".join(args.query)
            console.print(f"[bold cyan]Query>[/bold cyan] {user_input}")
            cancel_token = CancellationToken()
            await run_query(
                hub=hub,
                query=user_input,
                emit=handler.handle_event,
                cancel_token=cancel_token,
                max_iterations=args.max_iterations,
            )
        else:
            # Interactive mode
            while True:
                try:
                    user_input = console.input("\n[bold cyan]You>[/bold cyan] ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ("exit", "quit", "q"):
                        break

                    cancel_token = CancellationToken()
                    await run_query(
                        hub=hub,
                        query=user_input,
                        emit=handler.handle_event,
                        cancel_token=cancel_token,
                        max_iterations=args.max_iterations,
                    )
                except KeyboardInterrupt:
                    console.print("\n[yellow]Query interrupted by user.[/yellow]")
                    continue

    finally:
        console.print("[dim]Closing MCPHub connections...[/dim]")
        await hub.close()
        console.print("[green]✓ Clean shutdown complete.[/green]")


def run_cli() -> None:
    """Console script entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    run_cli()
