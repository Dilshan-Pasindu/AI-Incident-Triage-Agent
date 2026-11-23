"""
incident_agent — Core package for the AI Incident Triage & Release Readiness Agent.

Exposes:
- MCPHub, run_query, TraceLogger, ApprovalService, CancellationToken
- Approver protocol, CliApprover, ScriptedApprover
- Event types (BaseAgentEvent and all subtypes)
- Security guardrails and redaction utilities
- Path helpers (repo_root, RUST_BINARY, MOCK_DATA_DIR, WORKSPACE_DIR)
"""

from incident_agent.paths import (
    REPO_ROOT,
    RUST_BINARY,
    MOCK_DATA_DIR,
    WORKSPACE_DIR,
    TRACE_FILE,
    EVAL_FILE,
)

__all__ = [
    "REPO_ROOT",
    "RUST_BINARY",
    "MOCK_DATA_DIR",
    "WORKSPACE_DIR",
    "TRACE_FILE",
    "EVAL_FILE",
]
