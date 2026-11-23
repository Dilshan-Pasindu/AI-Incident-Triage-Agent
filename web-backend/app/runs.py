"""
web-backend/app/runs.py

Execution Run Manager for the Incident Triage Web Backend.
Manages asynchronous agent runs, Server-Sent Events (SSE) buffering,
reconnect replay via Last-Event-ID, and HTTP approval resolution.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional
import uuid

from incident_agent.agent import run_query
from incident_agent.approvers import ApprovalRecord, ApprovalService
from incident_agent.cancellation import CancellationToken
from incident_agent.events import (
    ApprovalRequiredEvent,
    ApprovalResolvedEvent,
    BaseAgentEvent,
    FinalAnswerEvent,
    RunStartedEvent,
    RunStoppedEvent,
)
from incident_agent.llm import LlmClient, get_llm_client
from incident_agent.mcp_client import MCPHub
from incident_agent.tracing import TraceLogger

from app.approver import WebApprover


class RunState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunContext:
    def __init__(
        self,
        run_id: str,
        query: str,
        approval_service: ApprovalService,
        trace_logger: TraceLogger,
        workspace_dir: str,
        model_name: Optional[str] = None,
    ):
        self.run_id = run_id
        self.query = query
        self.state = RunState.PENDING
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.ended_at: Optional[str] = None
        self.events: List[BaseAgentEvent] = []
        self.subscribers: List[asyncio.Queue[Optional[BaseAgentEvent]]] = []
        self.cancel_token = CancellationToken()
        self.approval_service = approval_service
        self.approver = WebApprover(service=approval_service)
        self.trace_logger = trace_logger
        self.workspace_dir = workspace_dir
        self.model_name = model_name
        self.task: Optional[asyncio.Task] = None
        self.result: Optional[str] = None
        self.error: Optional[str] = None
        self.pending_approval: Optional[ApprovalRecord] = None
        self._lock = asyncio.Lock()

    def add_event(self, ev: BaseAgentEvent) -> None:
        """Add event to run buffer and broadcast to active SSE subscribers."""
        self.events.append(ev)

        # Update run state based on event type
        if isinstance(ev, RunStartedEvent):
            self.state = RunState.RUNNING
        elif isinstance(ev, ApprovalRequiredEvent):
            self.state = RunState.AWAITING_APPROVAL
        elif isinstance(ev, ApprovalResolvedEvent):
            self.state = RunState.RUNNING
            self.pending_approval = None
        elif isinstance(ev, FinalAnswerEvent):
            self.result = ev.answer
            self.state = RunState.COMPLETED
            self.ended_at = datetime.now(timezone.utc).isoformat()
        elif isinstance(ev, RunStoppedEvent):
            if ev.reason == "cancelled":
                self.state = RunState.CANCELLED
            elif ev.reason == "error":
                self.state = RunState.FAILED
                self.error = ev.error
            elif not self.state == RunState.COMPLETED:
                self.state = RunState.COMPLETED
            self.ended_at = datetime.now(timezone.utc).isoformat()

        # Broadcast to all live subscriber queues
        dead_queues = []
        for q in self.subscribers:
            try:
                q.put_nowait(ev)
            except Exception:
                dead_queues.append(q)
        for dq in dead_queues:
            if dq in self.subscribers:
                self.subscribers.remove(dq)

    def close_subscribers(self) -> None:
        """Signal EOF (None) to all subscribers."""
        for q in self.subscribers:
            try:
                q.put_nowait(None)
            except Exception:
                pass
        self.subscribers.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize run summary for API endpoints."""
        tools_used = []
        for ev in self.events:
            tool_name = getattr(ev, "tool", None)
            if tool_name and tool_name not in tools_used:
                tools_used.append(tool_name)

        return {
            "run_id": self.run_id,
            "query": self.query,
            "state": self.state.value,
            "created_at": self.created_at,
            "ended_at": self.ended_at,
            "event_count": len(self.events),
            "tools_used": tools_used,
            "result_preview": (self.result[:200] + "...") if self.result and len(self.result) > 200 else self.result,
            "error": self.error,
            "model": self.model_name,
            "has_pending_approval": self.state == RunState.AWAITING_APPROVAL,
        }


class RunManager:
    """Central registry and lifecycle coordinator for active agent runs."""

    def __init__(
        self,
        hub: MCPHub,
        approval_service: ApprovalService,
        trace_logger: TraceLogger,
        workspace_dir: str,
        default_llm: Optional[LlmClient] = None,
    ):
        self.hub = hub
        self.approval_service = approval_service
        self.trace_logger = trace_logger
        self.workspace_dir = workspace_dir
        self.default_llm = default_llm or get_llm_client()
        self.runs: Dict[str, RunContext] = {}
        self._lock = asyncio.Lock()

    async def start_run(
        self,
        query: str,
        run_id: Optional[str] = None,
        llm: Optional[LlmClient] = None,
        model_name: Optional[str] = None,
    ) -> RunContext:
        """Create, register, and launch a new agent run task."""
        run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
        llm_client = llm or self.default_llm

        ctx = RunContext(
            run_id=run_id,
            query=query,
            approval_service=self.approval_service,
            trace_logger=self.trace_logger,
            workspace_dir=self.workspace_dir,
            model_name=model_name or getattr(llm_client, "model", "default"),
        )

        async with self._lock:
            self.runs[run_id] = ctx

        # Define background execution task
        async def _execute():
            try:
                await run_query(
                    hub=self.hub,
                    query=query,
                    emit=ctx.add_event,
                    approver=ctx.approver,
                    approval_service=ctx.approval_service,
                    trace_logger=ctx.trace_logger,
                    run_id=run_id,
                    cancel_token=ctx.cancel_token,
                    max_iterations=8,
                    llm_client=llm_client,
                    workspace_root=self.workspace_dir,
                )
            except asyncio.CancelledError:
                ctx.state = RunState.CANCELLED
                ctx.ended_at = datetime.now(timezone.utc).isoformat()
            except Exception as e:
                ctx.state = RunState.FAILED
                ctx.error = str(e)
                ctx.ended_at = datetime.now(timezone.utc).isoformat()
            finally:
                ctx.close_subscribers()

        ctx.task = asyncio.create_task(_execute())
        return ctx

    def get_run(self, run_id: str) -> Optional[RunContext]:
        return self.runs.get(run_id)

    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        sorted_runs = sorted(self.runs.values(), key=lambda r: r.created_at, reverse=True)
        return [r.to_dict() for r in sorted_runs[:limit]]

    async def cancel_run(self, run_id: str, reason: str = "User cancelled") -> bool:
        ctx = self.runs.get(run_id)
        if not ctx:
            return False

        ctx.cancel_token.cancel(reason)

        # If waiting for web approval, abort any open approval future
        for app_id in list(ctx.approver._waiters.keys()):
            ctx.approver.resolve_waiter(app_id, "reject")

        if ctx.task and not ctx.task.done():
            # Allow cooperative cancellation
            await asyncio.sleep(0.05)
            if not ctx.task.done():
                ctx.task.cancel()

        ctx.state = RunState.CANCELLED
        ctx.ended_at = datetime.now(timezone.utc).isoformat()
        ctx.close_subscribers()
        return True

    def resolve_approval(self, run_id: str, approval_id: str, decision: str) -> bool:
        """Resolve a pending Web approval."""
        ctx = self.runs.get(run_id)
        if not ctx:
            return False

        if approval_id in ctx.approver._waiters:
            ctx.approver.resolve_waiter(approval_id, decision)
            return True
        return False

    async def subscribe_events(
        self,
        run_id: str,
        last_event_id: Optional[int] = None,
    ) -> AsyncGenerator[BaseAgentEvent, None]:
        """
        Yield SSE events for a run.
        If last_event_id is provided, replays all previous events with event_id > last_event_id.
        """
        ctx = self.runs.get(run_id)
        if not ctx:
            return

        # 1. Replay missed buffered events
        if last_event_id is not None:
            for ev in ctx.events:
                if ev.event_id > last_event_id:
                    yield ev
        else:
            for ev in ctx.events:
                yield ev

        # If run is already completed and no task is active, finish
        if ctx.state in (RunState.COMPLETED, RunState.FAILED, RunState.CANCELLED) and (not ctx.task or ctx.task.done()):
            return

        # 2. Subscribe to live stream
        q: asyncio.Queue[Optional[BaseAgentEvent]] = asyncio.Queue()
        ctx.subscribers.append(q)

        try:
            while True:
                ev = await q.get()
                if ev is None:
                    break
                # Only yield if beyond last_event_id to prevent duplicates
                if last_event_id is None or ev.event_id > last_event_id:
                    yield ev
                if ctx.state in (RunState.COMPLETED, RunState.FAILED, RunState.CANCELLED) and q.empty():
                    break
        finally:
            if q in ctx.subscribers:
                ctx.subscribers.remove(q)
