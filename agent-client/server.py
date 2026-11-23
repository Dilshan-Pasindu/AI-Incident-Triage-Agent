"""
agent-client/server.py

FastAPI Web Backend for the Incident Triage & Release Readiness AI Agent.
Exposes REST and Server-Sent Events (SSE) streaming endpoints with
Last-Event-ID reconnection replay, interactive approval submission,
and health diagnostics.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Header, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from approvers import ApprovalService
from llm import GrokLlmClient, MockLlmClient, get_llm_client
from mcp_client import MCPHub
from runs import RunContext, RunManager, RunState
from tracing import TraceLogger

repo_root = Path(__file__).resolve().parent.parent
mock_data_dir = repo_root / "mock_data"
workspace_dir = mock_data_dir / "workspace"
rust_binary = repo_root / "mcp-server" / "target" / "release" / "ops-telemetry-mcp"
trace_file = repo_root / "agent_traces.jsonl"
eval_file = repo_root / "eval_results.md"

# Global components
hub: Optional[MCPHub] = None
approval_service: Optional[ApprovalService] = None
trace_logger: Optional[TraceLogger] = None
run_manager: Optional[RunManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global hub, approval_service, trace_logger, run_manager

    # Initialize TraceLogger and ApprovalService
    trace_logger = TraceLogger(str(trace_file))
    approval_service = ApprovalService(default_timeout_seconds=120.0)

    # Initialize and connect MCPHub
    hub = MCPHub(
        ops_binary_path=str(rust_binary),
        workspace_dir=str(workspace_dir),
    )
    await hub.start()

    # Initialize RunManager
    run_manager = RunManager(
        hub=hub,
        approval_service=approval_service,
        trace_logger=trace_logger,
        workspace_dir=str(workspace_dir),
    )

    yield

    # Teardown
    if hub:
        await hub.stop()


app = FastAPI(
    title="Incident Triage & Release Readiness AI Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local Vite dev server and UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------------
# Request Models
# -------------------------------------------------------------------------


class CreateRunRequest(BaseModel):
    query: str = Field(..., description="Incident investigation prompt or triage query")
    model: Optional[str] = Field(None, description="'mock' or specific Grok model name")


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., description="'approve' or 'reject'")


class CancelRunRequest(BaseModel):
    reason: Optional[str] = Field("User cancelled", description="Reason for cancellation")


# -------------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------------


@app.get("/api/health")
async def get_health():
    """Health check reporting MCP servers status and discovered tools."""
    if not hub:
        return {"status": "starting", "mcp_servers": {}}

    ops_conn = hub.connections.get("ops")
    fs_conn = hub.connections.get("fs")

    return {
        "status": "healthy",
        "mcp_servers": {
            "ops": {
                "name": "ops-telemetry-mcp",
                "health": ops_conn.health.value if ops_conn else "unknown",
            },
            "fs": {
                "name": "server-filesystem",
                "health": fs_conn.health.value if fs_conn else "unknown",
            },
        },
        "tools_count": len(hub.tool_registry),
        "tools": list(hub.tool_registry.keys()),
    }


@app.post("/api/runs", status_code=status.HTTP_201_CREATED)
async def create_run(req: CreateRunRequest):
    """Start a new incident triage investigation run."""
    if not run_manager:
        raise HTTPException(status_code=500, detail="Server not initialized")

    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    llm = None
    if req.model:
        if req.model.lower() == "mock":
            llm = MockLlmClient()
        elif req.model.lower() != "default":
            llm = GrokLlmClient(model=req.model)

    ctx = await run_manager.start_run(query=query, llm=llm, model_name=req.model)
    return ctx.to_dict()


@app.get("/api/runs")
async def list_runs(limit: int = Query(50, ge=1, le=100)):
    """List recent investigation runs."""
    if not run_manager:
        return []
    return run_manager.list_runs(limit=limit)


@app.get("/api/runs/{run_id}")
async def get_run_detail(run_id: str):
    """Get full details of a specific investigation run."""
    if not run_manager:
        raise HTTPException(status_code=500, detail="Server not initialized")

    ctx = run_manager.get_run(run_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    data = ctx.to_dict()
    data["events"] = [e.model_dump() for e in ctx.events]
    return data


@app.get("/api/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    request: Request,
    last_event_id_header: Optional[str] = Header(None, alias="Last-Event-ID"),
    last_event_id_query: Optional[int] = Query(None, alias="last_event_id"),
):
    """
    Stream live Server-Sent Events (SSE) for an investigation run.
    Supports event replay via Last-Event-ID header or query parameter.
    """
    if not run_manager:
        raise HTTPException(status_code=500, detail="Server not initialized")

    ctx = run_manager.get_run(run_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    # Determine last event ID for replay
    last_id = None
    if last_event_id_query is not None:
        last_id = last_event_id_query
    elif last_event_id_header is not None:
        try:
            last_id = int(last_event_id_header)
        except ValueError:
            pass

    async def event_generator():
        async for ev in run_manager.subscribe_events(run_id=run_id, last_event_id=last_id):
            if await request.is_disconnected():
                break

            ev_dict = ev.model_dump()
            yield {
                "event": ev.event_type.value,
                "id": str(ev.event_id),
                "data": json.dumps(ev_dict),
            }

    return EventSourceResponse(event_generator())


@app.post("/api/runs/{run_id}/approvals/{approval_id}")
async def resolve_approval(run_id: str, approval_id: str, req: ApprovalDecisionRequest):
    """Submit operator approval decision for a pending state mutation."""
    if not run_manager:
        raise HTTPException(status_code=500, detail="Server not initialized")

    ctx = run_manager.get_run(run_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    decision = req.decision.strip().lower()
    if decision not in ("approve", "approved", "reject", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'reject'")

    canonical_decision = "approved" if decision in ("approve", "approved") else "rejected"
    success = run_manager.resolve_approval(run_id, approval_id, canonical_decision)
    if not success:
        raise HTTPException(status_code=404, detail="Pending approval not found or already resolved")

    return {"status": "resolved", "decision": canonical_decision}


@app.post("/api/runs/{run_id}/cancel")
async def cancel_run(run_id: str, req: Optional[CancelRunRequest] = None):
    """Cancel an ongoing investigation run."""
    if not run_manager:
        raise HTTPException(status_code=500, detail="Server not initialized")

    reason = req.reason if req else "User cancelled"
    success = await run_manager.cancel_run(run_id, reason=reason)
    if not success:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    return {"status": "cancelled", "run_id": run_id}


@app.get("/api/traces")
async def get_traces(limit: int = Query(50, ge=1, le=200)):
    """Retrieve recent structured trace records from agent_traces.jsonl."""
    if not trace_file.exists():
        return []

    lines = []
    with open(trace_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    lines.append(json.loads(line))
                except Exception:
                    pass
    return lines[-limit:]


@app.get("/api/benchmarks")
async def get_benchmarks():
    """Return evaluation benchmarks summary from eval_results.md."""
    if not eval_file.exists():
        return {"content": "No benchmark report found. Run eval_suite.py first."}

    with open(eval_file, "r", encoding="utf-8") as f:
        content = f.read()

    return {"content": content}


def start_server(host: str = "0.0.0.0", port: int = 8000):
    """Entrypoint to launch the API server via uvicorn."""
    import uvicorn
    uvicorn.run("server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    start_server()
