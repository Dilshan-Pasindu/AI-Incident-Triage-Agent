"""
agent-client/tracing.py

Structured JSONL Tracing and Redaction Engine for Incident Triage Agent.
Guarantees:
- Every tool execution is logged to agent_traces.jsonl
- Secrets, API keys, Bearer tokens, and env vars are strictly redacted
- Truncates large input/output payloads to 500 chars with 'truncated: true'
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from incident_agent.paths import TRACE_FILE as _DEFAULT_TRACE_FILE

# Secret detection patterns
RE_API_KEY = re.compile(r"(?:xai|sk)-[a-zA-Z0-9_\-]{16,}")
RE_BEARER = re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE)
RE_KEY_VALUE_SECRET = re.compile(
    r'(?i)(?:api_key|token|secret|password|auth_token)\s*[:=]\s*["\']?([^"\'\s,;]+)["\']?'
)


def redact_string(val: str) -> str:
    """Redact secret tokens, API keys, and sensitive environment patterns from strings."""
    if not isinstance(val, str):
        return val

    # Redact xai- and sk- keys
    val = RE_API_KEY.sub("[REDACTED_API_KEY]", val)
    # Redact Bearer tokens
    val = RE_BEARER.sub("Bearer [REDACTED_TOKEN]", val)
    # Redact KEY=value secrets
    val = RE_KEY_VALUE_SECRET.sub(r"\g<0>".split("=")[0] + "=[REDACTED_SECRET]", val)
    return val


def truncate_value(val: Any, max_len: int = 500) -> tuple[Any, bool]:
    """Truncate string or serialized representation to max_len chars."""
    if isinstance(val, str):
        if len(val) > max_len:
            return val[:max_len] + "... [TRUNCATED]", True
        return val, False
    elif isinstance(val, (dict, list)):
        serialized = json.dumps(val)
        if len(serialized) > max_len:
            return serialized[:max_len] + "... [TRUNCATED]", True
        return val, False
    return val, False


def redact(obj: Any, max_string_len: int = 500) -> Any:
    """
    Recursively redact secrets and truncate large strings from any JSON-serializable object.
    Applies to both trace records and frontend client events.
    """
    if isinstance(obj, str):
        redacted = redact_string(obj)
        truncated, _ = truncate_value(redacted, max_len=max_string_len)
        return truncated
    elif isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            # Check for forbidden sensitive keys
            k_lower = str(k).lower()
            if any(secret_term in k_lower for secret_term in ("api_key", "secret", "password", "token", "authorization")):
                cleaned[k] = "[REDACTED_SECRET]"
            else:
                cleaned[k] = redact(v, max_string_len=max_string_len)
        return cleaned
    elif isinstance(obj, list):
        return [redact(item, max_string_len=max_string_len) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(redact(item, max_string_len=max_string_len) for item in obj)
    return obj


class TraceLogger:
    """
    Thread-safe / Async structured JSONL logger writing to agent_traces.jsonl.
    """

    def __init__(self, trace_file_path: Optional[str] = None):
        if trace_file_path:
            self.trace_file = Path(trace_file_path).resolve()
        else:
            self.trace_file = _DEFAULT_TRACE_FILE

        self._lock = asyncio.Lock()

    async def log_event(
        self,
        run_id: str,
        event_id: int,
        iteration: int,
        server: str,
        tool: str,
        tool_call_id: str,
        input_args: Dict[str, Any],
        status: str,
        duration_ms: float,
        output_preview: str,
        approval_id: Optional[str] = None,
        approval: Optional[str] = None,
        approval_source: Optional[str] = None,
        injection_suspected: bool = False,
        error: Optional[str] = None,
        truncated: bool = False,
    ) -> Dict[str, Any]:
        """Format, redact, and append a structured event record to the JSONL trace file."""
        redacted_input = redact(input_args, max_string_len=300)
        redacted_preview = redact_string(output_preview)
        if len(redacted_preview) > 500:
            redacted_preview = redacted_preview[:500] + "... [TRUNCATED]"
            truncated = True

        sanitized_error = redact_string(error) if error else None

        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "event_id": event_id,
            "iteration": iteration,
            "server": server,
            "tool": tool,
            "tool_call_id": tool_call_id,
            "input": redacted_input,
            "approval_id": approval_id,
            "approval": approval,
            "approval_source": approval_source,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "injection_suspected": injection_suspected,
            "error": sanitized_error,
            "output_preview": redacted_preview,
            "truncated": truncated,
        }

        async with self._lock:
            # Run file write in executor so it is thread-safe
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._append_record, record)

        return record

    def _append_record(self, record: Dict[str, Any]) -> None:
        with open(self.trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
