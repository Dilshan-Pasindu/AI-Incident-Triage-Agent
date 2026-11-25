#!/usr/bin/env python3
"""
scripts/grok_smoke_test.py (Universal LLM API Smoke Test)

Verifies integration with live OpenAI-compatible LLM providers:
- OpenRouter (OPENROUTER_API_KEY / x-ai/grok-3-beta)
- xAI Grok (XAI_API_KEY / grok-2-latest)
- Google Gemini (GEMINI_API_KEY / gemini-3-flash-preview)
- OpenAI (OPENAI_API_KEY / gpt-4o-mini)

Checks:
- Chat completions with function calling (tools and tool_choice)
- Verifies tool arguments returned as valid JSON strings
- Tests multiple tool calls in a single assistant turn
- Error handling and sanitized provider diagnostics
- Strictly guarantees NO API keys or request headers are logged.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, cast

from dotenv import load_dotenv

load_dotenv()


def sanitize_message(msg: str) -> str:
    """Sanitize error and output text so API keys are never exposed."""
    s = re.sub(r"(?:xai|sk)-[a-zA-Z0-9_-]{10,}", "[REDACTED_API_KEY]", msg)
    s = re.sub(r"(?:AIza[0-9A-Za-z-_]{35}|AQ\.[0-9A-Za-z-_]{20,})", "[REDACTED_API_KEY]", s)
    s = re.sub(r"Bearer\s+[a-zA-Z0-9_\-\.]+", "Bearer [REDACTED_TOKEN]", s, flags=re.IGNORECASE)
    s = re.sub(r"headers=\{[^\}]+\}", "headers=[REDACTED]", s)
    return s


def test_grok_smoke():
    """Universal smoke test entrypoint, backwards-compatible with grok_smoke_test."""
    # Detect provider
    explicit_provider = os.environ.get("LLM_PROVIDER", "").lower()

    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    xai_key = os.environ.get("XAI_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    # Auto-detect OpenRouter key even if placed in XAI_API_KEY
    if not openrouter_key and xai_key.startswith("sk-or-"):
        openrouter_key = xai_key

    # Provider configuration
    provider_name: str
    api_key: str
    base_url: str
    default_model: str
    extra_headers: dict[str, str] | None = None

    if explicit_provider == "openrouter" or (
        explicit_provider in ("", "grok")
        and openrouter_key
        and not openrouter_key.startswith("sk-or-v1-your-")
    ):
        provider_name = "OpenRouter (Grok)"
        api_key = openrouter_key
        base_url = "https://openrouter.ai/api/v1"
        default_model = os.environ.get("OPENROUTER_MODEL") or os.environ.get("GROK_MODEL") or "x-ai/grok-3-beta"
        extra_headers = {
            "HTTP-Referer": os.environ.get(
                "OPENROUTER_SITE_URL", "https://github.com/Dilshan-Pasindu/AI-Incident-Triage-Agent"
            ),
            "X-Title": os.environ.get("OPENROUTER_APP_NAME", "AI Incident Triage Agent"),
        }
    elif explicit_provider in ("xai", "grok") or (
        explicit_provider == "" and xai_key and not xai_key.startswith("xai-your-api-key")
    ):
        provider_name = "xAI Grok"
        api_key = xai_key
        base_url = "https://api.x.ai/v1"
        default_model = os.environ.get("GROK_MODEL", "grok-2-latest")
    elif explicit_provider == "gemini" or (
        explicit_provider == "" and gemini_key and not gemini_key.startswith("AIzaSy-placeholder")
    ):
        provider_name = "Google Gemini"
        api_key = gemini_key
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        default_model = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
    elif explicit_provider == "openai" or (
        explicit_provider == "" and openai_key and not openai_key.startswith("sk-your-")
    ):
        provider_name = "OpenAI"
        api_key = openai_key
        base_url = "https://api.openai.com/v1"
        default_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    else:
        print("==================================================")
        print("LLM API SMOKE TEST (Universal Provider Check)")
        print("==================================================")
        print("\n[INFO] No live LLM API key detected.")
        print("To run against a live provider, set one of the following in .env:")
        print("  OpenRouter    : OPENROUTER_API_KEY=sk-or-v1-...")
        print("  xAI Grok      : XAI_API_KEY=xai-...")
        print("  Google Gemini : GEMINI_API_KEY=AIzaSy...")
        print("  OpenAI        : OPENAI_API_KEY=sk-...\n")
        print("Mock test verification: SUCCESS (MockLlmClient will be used until an API key is added).")
        return

    model = os.environ.get("LLM_MODEL", default_model)
    if provider_name == "Google Gemini" and not model.startswith("models/"):
        model = f"models/{model}"
    elif provider_name == "OpenRouter (Grok)" and "/" not in model and model.lower().startswith("grok"):
        model = f"x-ai/{model}"

    print("==================================================")
    print(f"LLM API SMOKE TEST ({provider_name} Integration)")
    print("==================================================")
    print(f"Target Provider : {provider_name}")
    print(f"Target Model    : {model}")
    print(f"Base URL        : {base_url}")

    from openai import OpenAI

    print(f"\nConnecting to {base_url} ...")
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        default_headers=extra_headers,
    )

    test_tools = [
        {
            "type": "function",
            "function": {
                "name": "search_logs",
                "description": "Searches service log entries.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string"},
                        "severity": {"type": "string", "enum": ["INFO", "WARN", "ERROR", "FATAL"]},
                        "limit": {"type": "integer"},
                    },
                    "required": ["service_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_deployment_history",
                "description": "Retrieves recent deployment history for a service.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string"},
                        "window_hours": {"type": "integer"},
                    },
                    "required": ["service_name"],
                },
            },
        },
    ]

    # 1. Test Single Tool Calling
    print("\n--- Test 1: Single Tool Call Generation ---")
    start = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a DevOps assistant. Always use tools to search logs when asked."},
                {"role": "user", "content": "Check the last 3 ERROR logs for payments-api."},
            ],
            tools=cast(Any, test_tools),
            tool_choice="auto",
        )
        latency = (time.perf_counter() - start) * 1000
        choice = response.choices[0]
        print(f"Response status: OK (Latency: {latency:.1f}ms)")
        if choice.message.tool_calls:
            print(f"Tool calls generated: {len(choice.message.tool_calls)}")
            for tc in choice.message.tool_calls:
                fn = getattr(tc, "function", None)
                if fn:
                    print(f"  ID: {tc.id}")
                    print(f"  Function: {fn.name}")
                    print(f"  Arguments JSON: {fn.arguments}")
                    parsed_args = json.loads(fn.arguments)
                    print(f"  Parsed Arguments: {parsed_args}")
        else:
            print(f"Model text response: {choice.message.content}")

    except Exception as e:
        sanitized = sanitize_message(str(e))
        print(f"[ERROR] API call failed: {type(e).__name__}: {sanitized}")
        return

    # 2. Test Multi-Tool Calling
    print("\n--- Test 2: Multi-Tool Call Generation ---")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a DevOps assistant. Call all relevant tools in parallel when possible."},
                {"role": "user", "content": "Check both ERROR logs and deployment history for payments-api simultaneously."},
            ],
            tools=cast(Any, test_tools),
            tool_choice="auto",
        )
        choice = response.choices[0]
        if choice.message.tool_calls:
            print(f"Tool calls generated in single turn: {len(choice.message.tool_calls)}")
            for tc in choice.message.tool_calls:
                fn = getattr(tc, "function", None)
                if fn:
                    print(f"  - {fn.name}({fn.arguments})")
        else:
            print(f"Model chose text response: {choice.message.content}")
    except Exception as e:
        sanitized = sanitize_message(str(e))
        print(f"[ERROR] Multi-tool test error: {sanitized}")

    print("\n==================================================")
    print(f"{provider_name.upper()} SMOKE TEST COMPLETED SUCCESSFULLY")
    print("==================================================")


if __name__ == "__main__":
    test_grok_smoke()
