"""
agent-client/events.py

Pydantic event models for agent run lifecycle, tool calls, and streaming telemetry.
Every event carries a run_id and a monotonically increasing event_id.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    RUN_STARTED = "run_started"
    LLM_TURN = "llm_turn"
    TOOL_STARTED = "tool_started"
    TOOL_FINISHED = "tool_finished"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESOLVED = "approval_resolved"
    FINAL_ANSWER = "final_answer"
    RUN_STOPPED = "run_stopped"


class ToolStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    INVALID = "invalid"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseAgentEvent(BaseModel):
    event_type: EventType
    run_id: str
    event_id: int
    timestamp: str = Field(default_factory=utc_now_iso)


class RunStartedEvent(BaseAgentEvent):
    event_type: EventType = EventType.RUN_STARTED
    query: str


class LlmTurnEvent(BaseAgentEvent):
    event_type: EventType = EventType.LLM_TURN
    iteration: int
    text_preview: Optional[str] = None
    tool_calls_count: int = 0
    latency_ms: float = 0.0


class ToolStartedEvent(BaseAgentEvent):
    event_type: EventType = EventType.TOOL_STARTED
    iteration: int
    server: str
    tool: str
    tool_call_id: str
    arguments: Dict[str, Any]
    is_mutating: bool = False


class ToolFinishedEvent(BaseAgentEvent):
    event_type: EventType = EventType.TOOL_FINISHED
    iteration: int
    server: str
    tool: str
    tool_call_id: str
    status: ToolStatus
    duration_ms: float
    output_preview: str
    truncated: bool = False
    injection_suspected: bool = False
    error: Optional[str] = None


class ApprovalRequiredEvent(BaseAgentEvent):
    event_type: EventType = EventType.APPROVAL_REQUIRED
    approval_id: str
    tool_call_id: str
    tool: str
    server: str
    arguments: Dict[str, Any]
    payload_hash: str
    expires_at: str


class ApprovalResolvedEvent(BaseAgentEvent):
    event_type: EventType = EventType.APPROVAL_RESOLVED
    approval_id: str
    tool_call_id: str
    decision: str  # approved, rejected, expired, cancelled
    source: str    # cli, web, scripted, auto


class FinalAnswerEvent(BaseAgentEvent):
    event_type: EventType = EventType.FINAL_ANSWER
    answer: str
    iterations: int
    tools_used: List[str]
    duration_ms: float


class RunStoppedEvent(BaseAgentEvent):
    event_type: EventType = EventType.RUN_STOPPED
    reason: str  # completed, cancelled, max_iterations, error, malformed_response
    iterations: int
    error: Optional[str] = None
