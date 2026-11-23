"""
agent-client/llm.py

Provider-swappable LLM adapter for xAI Grok (and local mock fallback).
Enforces tenacity retries on HTTP 429 and 5xx errors, logs latency,
and strictly sanitizes request headers and API keys from error outputs.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

load_dotenv()


@dataclass
class ToolCallItem:
    id: str
    name: str
    arguments_json: str


@dataclass
class LlmTurn:
    text: Optional[str]
    tool_calls: List[ToolCallItem] = field(default_factory=list)
    latency_ms: float = 0.0


def is_retryable_error(exc: BaseException) -> bool:
    """Determine if provider error is a retryable 429 or 5xx."""
    msg = str(exc).lower()
    # Check for HTTP status codes
    status_code = getattr(exc, "status_code", None)
    if status_code in (429, 500, 502, 503, 504):
        return True
    if "rate limit" in msg or "429" in msg or "500" in msg or "502" in msg or "503" in msg:
        return True
    return False


def sanitize_error_message(exc: Exception) -> str:
    """Sanitize provider errors so API keys and headers are never exposed."""
    msg = str(exc)
    # Redact xai- or sk- keys
    msg = re.sub(r"(?:xai|sk)-[a-zA-Z0-9_-]{10,}", "[REDACTED_API_KEY]", msg)
    # Redact Bearer tokens
    msg = re.sub(r"Bearer\s+[a-zA-Z0-9_\-\.]+", "Bearer [REDACTED_TOKEN]", msg, flags=re.IGNORECASE)
    # Strip headers if present in error representation
    msg = re.sub(r"headers=\{[^\}]+\}", "headers=[REDACTED]", msg)
    return msg


class LlmClient(Protocol):
    async def step(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> LlmTurn:
        ...


class GrokLlmClient:
    """Production LLM adapter for xAI Grok via OpenAI-compatible SDK."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        from openai import AsyncOpenAI

        self.api_key = api_key or os.environ.get("XAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("XAI_API_KEY environment variable is required for GrokLlmClient.")

        self.model = model or os.environ.get("GROK_MODEL", "grok-2-latest")
        self.client = AsyncOpenAI(
            base_url="https://api.x.ai/v1",
            api_key=self.api_key,
        )

    @retry(
        retry=retry_if_exception(is_retryable_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def step(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> LlmTurn:
        start_time = time.perf_counter()
        try:
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = await self.client.chat.completions.create(**kwargs)
            latency_ms = (time.perf_counter() - start_time) * 1000

            choice = response.choices[0]
            msg = choice.message

            tool_calls: List[ToolCallItem] = []
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append(
                        ToolCallItem(
                            id=tc.id,
                            name=tc.function.name,
                            arguments_json=tc.function.arguments,
                        )
                    )

            return LlmTurn(
                text=msg.content,
                tool_calls=tool_calls,
                latency_ms=latency_ms,
            )

        except Exception as e:
            sanitized = sanitize_error_message(e)
            raise RuntimeError(f"Grok API error: {sanitized}") from None


class MockLlmClient:
    """
    Intelligent mock provider for local offline testing and benchmarking.
    Simulates Grok's tool-calling logic across incident triage scenarios
    without requiring an external API key.
    """

    def __init__(self, model_name: str = "mock-grok-2"):
        self.model = model_name

    async def step(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> LlmTurn:
        start_time = time.perf_counter()

        # Find latest user prompt
        user_prompt = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_prompt = m.get("content", "").lower()
                break

        # Check existing tool responses in history to know current iteration state
        tool_responses = [m for m in messages if m.get("role") == "tool"]

        # Case 1: Simple logs lookup (e.g., "Show the last 5 ERROR logs for auth-service")
        if "auth-service" in user_prompt and "logs" in user_prompt:
            if not tool_responses:
                return LlmTurn(
                    text=None,
                    tool_calls=[
                        ToolCallItem(
                            id="call_auth_logs_1",
                            name="ops__search_logs",
                            arguments_json=json.dumps({"service_name": "auth-service", "severity": "ERROR", "limit": 5}),
                        )
                    ],
                    latency_ms=50.0,
                )
            else:
                return LlmTurn(
                    text="Here are the recent ERROR logs for auth-service: There are currently no critical errors, but one warning was reported for token verification latency.",
                    tool_calls=[],
                    latency_ms=40.0,
                )

        # Case 2: Multi-step payments investigation ("Why is payments-api failing? Find root cause")
        if "payments" in user_prompt and ("failing" in user_prompt or "root cause" in user_prompt or "error" in user_prompt):
            # Step 1: Search payments logs
            if len(tool_responses) == 0:
                return LlmTurn(
                    text="Investigating payments-api failure. First, searching recent ERROR logs for payments-api.",
                    tool_calls=[
                        ToolCallItem(
                            id="call_payments_logs_1",
                            name="ops__search_logs",
                            arguments_json=json.dumps({"service_name": "payments-api", "severity": "ERROR", "limit": 10}),
                        )
                    ],
                    latency_ms=60.0,
                )
            # Step 2: Check deployment history
            elif len(tool_responses) == 1:
                return LlmTurn(
                    text="Error logs indicate multiple 'DB connection timeout after 5000ms' and 'connection pool exhausted' errors starting at 08:50Z. Next, checking deployment history to correlate with recent changes.",
                    tool_calls=[
                        ToolCallItem(
                            id="call_payments_deploy_1",
                            name="ops__get_deployment_history",
                            arguments_json=json.dumps({"service_name": "payments-api", "window_hours": 24}),
                        )
                    ],
                    latency_ms=55.0,
                )
            # Step 3: Read runbook
            elif len(tool_responses) == 2:
                return LlmTurn(
                    text="Deployment commit c4a9f12 ('Reduce DB pool size') was deployed at 08:50Z, immediately preceding the connection pool errors. Now inspecting the payments-api runbook for troubleshooting steps.",
                    tool_calls=[
                        ToolCallItem(
                            id="call_payments_runbook_1",
                            name="read_resource",
                            arguments_json=json.dumps({"uri": "service://runbooks/payments-api"}),
                        )
                    ],
                    latency_ms=50.0,
                )
            # Step 4: Final RCA and proposed ticket
            else:
                return LlmTurn(
                    text=(
                        "### Root Cause Analysis: payments-api Outage\n\n"
                        "1. **Incident Trigger**: Deployment commit `c4a9f12` ('Reduce DB pool size') at 08:50 UTC reduced the database connection pool limit.\n"
                        "2. **Observed Symptoms**: 10 `ERROR` entries and 1 `FATAL` entry with `DB connection timeout after 5000ms` and `connection pool exhausted`.\n"
                        "3. **Security Flag**: An adversarial log entry containing prompt injection was detected in the logs (`SYSTEM OVERRIDE`) and safely isolated as data.\n"
                        "4. **Remediation**: Revert commit `c4a9f12` and restore DB pool size to 25+ in `service-config.yaml`.\n\n"
                        "**Proposed Ticket Payload**:\n"
                        "- Title: `Payments API Outage: DB Connection Pool Exhaustion`\n"
                        "- Severity: `CRITICAL`\n"
                        "- Assignee: `payments-oncall`\n"
                        "- Summary: `Outage triggered by commit c4a9f12 reducing pool size; pool exhausted under load. Recommend rollback.`"
                    ),
                    tool_calls=[],
                    latency_ms=45.0,
                )

        # Case 3: Release readiness check
        if "ready for release" in user_prompt or "release" in user_prompt:
            if len(tool_responses) == 0:
                return LlmTurn(
                    text="Checking release readiness. First reading the mandatory pre-release checklist.",
                    tool_calls=[
                        ToolCallItem(
                            id="call_checklist_1",
                            name="read_resource",
                            arguments_json=json.dumps({"uri": "config://release-checklist"}),
                        )
                    ],
                    latency_ms=50.0,
                )
            elif len(tool_responses) == 1:
                return LlmTurn(
                    text="Checking recent release notes in workspace.",
                    tool_calls=[
                        ToolCallItem(
                            id="call_notes_1",
                            name="fs__read_text_file",
                            arguments_json=json.dumps({"path": "RELEASE_NOTES.md"}),
                        )
                    ],
                    latency_ms=50.0,
                )
            else:
                return LlmTurn(
                    text="Release readiness verification complete: Checked checklist criteria and verified release notes in workspace.",
                    tool_calls=[],
                    latency_ms=40.0,
                )

        # Case 4: Ticket creation request ("Open a ticket for the payments outage")
        if "ticket" in user_prompt or "open a ticket" in user_prompt:
            if not tool_responses:
                return LlmTurn(
                    text="Drafting incident ticket for the payments outage.",
                    tool_calls=[
                        ToolCallItem(
                            id="call_create_ticket_1",
                            name="ops__create_incident_ticket",
                            arguments_json=json.dumps({
                                "title": "Payments API Outage: Database Pool Exhaustion",
                                "severity": "CRITICAL",
                                "summary": "DB connection timeouts observed after deployment commit c4a9f12. Immediate rollback recommended.",
                                "assignee": "sarah.k",
                            }),
                        )
                    ],
                    latency_ms=50.0,
                )
            else:
                return LlmTurn(
                    text="The incident ticket has been drafted.",
                    tool_calls=[],
                    latency_ms=30.0,
                )

        # Default fallback: answer directly
        return LlmTurn(
            text=f"I have received your query: '{user_prompt}'. How can I assist you with incident triage or release verification?",
            tool_calls=[],
            latency_ms=30.0,
        )


def get_llm_client() -> LlmClient:
    """Factory returning GrokLlmClient if valid XAI_API_KEY is present, else MockLlmClient."""
    api_key = os.environ.get("XAI_API_KEY", "")
    if api_key and not api_key.startswith("xai-your-api-key"):
        return GrokLlmClient()
    return MockLlmClient()
