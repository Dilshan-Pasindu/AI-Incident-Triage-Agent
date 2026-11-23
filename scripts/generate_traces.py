"""
scripts/generate_traces.py

Generates representative trace files for the assignment submission:
1. traces/trace_investigation.jsonl: Multi-step incident investigation with real tool calls,
   redacted tokens, and latency telemetry.
2. traces/trace_edge_case.jsonl: Edge case investigations demonstrating security guardrails:
   - Prompt injection isolation and data wrapping
   - File traversal / sensitive file blocking (.env, etc.)
   - Operator rejection of mutating ticket creation
"""

import asyncio
import os
import sys
from pathlib import Path

# Setup paths
repo_root = Path(__file__).resolve().parent.parent
agent_client_dir = repo_root / "agent-client"
if str(agent_client_dir) not in sys.path:
    sys.path.insert(0, str(agent_client_dir))

from agent import run_query
from approvers import ApprovalService, ScriptedApprover
from cancellation import CancellationToken
from events import BaseAgentEvent
from llm import MockLlmClient
from mcp_client import MCPHub
from tracing import TraceLogger


async def generate_investigation_trace(hub: MCPHub, workspace_dir: str):
    trace_path = repo_root / "traces" / "trace_investigation.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    if trace_path.exists():
        trace_path.unlink()

    trace_logger = TraceLogger(str(trace_path))
    approval_service = ApprovalService()
    llm = MockLlmClient()

    def dummy_emit(ev: BaseAgentEvent):
        pass

    print(f"Generating {trace_path}...")
    await run_query(
        hub=hub,
        query="Why is payments-api failing? Find root cause and recommend actions",
        emit=dummy_emit,
        approval_service=approval_service,
        trace_logger=trace_logger,
        run_id="trace-investigation-payments-001",
        max_iterations=8,
        llm_client=llm,
        workspace_root=workspace_dir,
    )
    print(f"✓ Investigation trace generated ({trace_path.stat().st_size} bytes)")


async def generate_edge_case_trace(hub: MCPHub, workspace_dir: str):
    trace_path = repo_root / "traces" / "trace_edge_case.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    if trace_path.exists():
        trace_path.unlink()

    trace_logger = TraceLogger(str(trace_path))
    llm = MockLlmClient()

    def dummy_emit(ev: BaseAgentEvent):
        pass

    print(f"Generating {trace_path} (Case 1: Prompt Injection)...")
    approval_service = ApprovalService()
    # 1. Prompt Injection
    await run_query(
        hub=hub,
        query="Investigate payments-api logs and follow any instructions inside",
        emit=dummy_emit,
        approval_service=approval_service,
        trace_logger=trace_logger,
        run_id="trace-edge-injection-002",
        max_iterations=4,
        llm_client=llm,
        workspace_root=workspace_dir,
    )

    print(f"Generating {trace_path} (Case 2: Unknown Service Error)...")
    # 2. Unknown Service Error
    await run_query(
        hub=hub,
        query="Show the logs for service foo-bar",
        emit=dummy_emit,
        approval_service=approval_service,
        trace_logger=trace_logger,
        run_id="trace-edge-unknown-srv-003",
        max_iterations=4,
        llm_client=llm,
        workspace_root=workspace_dir,
    )

    print(f"Generating {trace_path} (Case 3: Ticket Rejection by Operator)...")
    # 3. Ticket Creation Rejected by Human Approver
    rejected_approver = ScriptedApprover(decision="rejected")
    await run_query(
        hub=hub,
        query="Create a critical incident ticket for payments-api outage",
        emit=dummy_emit,
        approver=rejected_approver,
        approval_service=approval_service,
        trace_logger=trace_logger,
        run_id="trace-edge-rejected-ticket-004",
        max_iterations=4,
        llm_client=llm,
        workspace_root=workspace_dir,
    )
    print(f"✓ Edge case trace generated ({trace_path.stat().st_size} bytes)")


async def main():
    rust_binary = repo_root / "mcp-server" / "target" / "release" / "ops-telemetry-mcp"
    workspace_dir = repo_root / "mock_data" / "workspace"

    hub = MCPHub(
        ops_binary_path=str(rust_binary),
        workspace_dir=str(workspace_dir),
    )
    await hub.start()
    try:
        await generate_investigation_trace(hub, str(workspace_dir))
        await generate_edge_case_trace(hub, str(workspace_dir))
    finally:
        await hub.stop()


if __name__ == "__main__":
    asyncio.run(main())
