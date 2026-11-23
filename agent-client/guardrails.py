"""
agent-client/guardrails.py

Code-enforced Security Boundaries, Validation, and Injection Detection.
Enforces:
1. Batch-level and per-call tool invocation validation (using jsonschema).
2. Canonical filesystem sandbox confinement (symlink resolution, commonpath check).
3. Regex prompt-injection detection (NFKC normalization, whitespace collapse).
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import jsonschema

# Forbidden sensitive filename patterns
FORBIDDEN_FILE_PATTERNS = [
    re.compile(r"^\.env.*", re.IGNORECASE),
    re.compile(r".*secret.*", re.IGNORECASE),
    re.compile(r".*credential.*", re.IGNORECASE),
    re.compile(r"^id_rsa.*", re.IGNORECASE),
    re.compile(r".*\.pem$", re.IGNORECASE),
]

# Configured non-path keys that should not be evaluated as filesystem paths
KNOWN_NON_PATH_KEYS = {
    "pattern",
    "excludePatterns",
    "tail",
    "head",
    "sortBy",
    "depth",
    "service_name",
    "severity",
    "limit",
    "window_hours",
    "title",
    "summary",
    "assignee",
    "uri",
}

# Prompt injection detection patterns
INJECTION_PATTERNS = [
    re.compile(r"(?:ignore|disregard)\s+(?:all\s+)?(?:previous|prior|earlier|above)\s+(?:instructions|rules)", re.IGNORECASE),
    re.compile(r"system\s+override", re.IGNORECASE),
    re.compile(r"you\s+are\s+now", re.IGNORECASE),
    re.compile(r"read\s+(?:all\s+)?(?:\.env|\.env\.local|secrets)", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?(?:rules|instructions)", re.IGNORECASE),
]


def validate_tool_batch(tool_calls: List[Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate the complete assistant tool-call batch before appending or executing.
    Fails closed if any tool_call_id is missing, empty, or duplicated.
    """
    if not tool_calls:
        return True, None

    seen_ids: Set[str] = set()
    for idx, tc in enumerate(tool_calls):
        call_id = getattr(tc, "id", None)
        if not call_id or not isinstance(call_id, str) or not call_id.strip():
            return False, f"Batch validation error: tool_call at index {idx} has missing or empty id."
        if call_id in seen_ids:
            return False, f"Batch validation error: duplicate tool_call_id '{call_id}' detected in single turn."
        seen_ids.add(call_id)

    return True, None


def validate_tool_arguments(schema: Dict[str, Any], arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate tool arguments against JSON Schema using jsonschema.
    Rejects unexpected extra arguments even if schema omits additionalProperties.
    """
    if not isinstance(arguments, dict):
        return False, f"Arguments must be a JSON object, got {type(arguments).__name__}."

    # Clone schema and enforce additionalProperties=False if properties is present
    strict_schema = dict(schema)
    if "properties" in strict_schema and "additionalProperties" not in strict_schema:
        strict_schema["additionalProperties"] = False

    try:
        jsonschema.validate(instance=arguments, schema=strict_schema)
        return True, None
    except jsonschema.ValidationError as ve:
        return False, f"Argument validation failed: {ve.message}"
    except Exception as e:
        return False, f"Schema validation error: {e}"


def check_prompt_injection(text: str) -> bool:
    """
    Inspect text for adversarial prompt-injection patterns.
    Normalizes text with Unicode NFKC and collapses whitespace first.
    Detection layer only, NOT a security boundary.
    """
    if not text:
        return False

    # 1. Normalize Unicode NFKC
    normalized = unicodedata.normalize("NFKC", text)
    # 2. Collapse whitespace
    collapsed = " ".join(normalized.split())

    for pat in INJECTION_PATTERNS:
        if pat.search(collapsed):
            return True
    return False


def validate_and_canonicalize_path(
    candidate_path: str,
    workspace_root: str,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Canonical Filesystem Security Boundary.
    Enforces that candidate path resolves strictly within the canonical workspace root.
    Returns (is_allowed, canonical_resolved_path, error_reason).
    """
    # 1. Reject NUL bytes
    if "\0" in candidate_path:
        return False, None, "BLOCKED by policy: NUL byte in path"

    try:
        resolved_root = os.path.realpath(os.path.abspath(workspace_root))
        # Handle Windows/macOS case folding
        resolved_root = os.path.normcase(resolved_root)

        # Normalize relative path candidate against root
        if os.path.isabs(candidate_path):
            abs_candidate = os.path.normpath(candidate_path)
        else:
            abs_candidate = os.path.normpath(os.path.join(resolved_root, candidate_path))

        # 4. Resolve symlinks
        resolved_candidate = os.path.realpath(abs_candidate)
        resolved_candidate = os.path.normcase(resolved_candidate)

        # 6. Verify resolved path is strictly inside workspace root using commonpath
        common = os.path.commonpath([resolved_candidate, resolved_root])
        if common != resolved_root:
            return False, None, f"BLOCKED by policy: path escape attempted outside workspace root"

        # Filename pattern security layer: block sensitive files (.env, secrets, etc.)
        base_name = os.path.basename(resolved_candidate)
        for pattern in FORBIDDEN_FILE_PATTERNS:
            if pattern.match(base_name):
                return False, None, f"BLOCKED by policy: access to sensitive file '{base_name}' is forbidden"

        return True, resolved_candidate, None

    except Exception as e:
        return False, None, f"BLOCKED by policy: path resolution failed ({e})"


def sanitize_fs_arguments(
    arguments: Dict[str, Any],
    workspace_root: str,
) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """
    Apply canonical path validation to all path arguments in a filesystem tool call.
    Unknown arguments fail closed.
    """
    sanitized = {}
    for key, value in arguments.items():
        if key in KNOWN_NON_PATH_KEYS:
            sanitized[key] = value
        elif isinstance(value, str):
            # Treat string argument as path candidate
            ok, canonical_path, err = validate_and_canonicalize_path(value, workspace_root)
            if not ok:
                return False, {}, err
            sanitized[key] = canonical_path
        elif isinstance(value, list) and all(isinstance(x, str) for x in value):
            # Treat list of strings as path candidates
            sanitized_list = []
            for item in value:
                ok, canonical_path, err = validate_and_canonicalize_path(item, workspace_root)
                if not ok:
                    return False, {}, err
                sanitized_list.append(canonical_path)
            sanitized[key] = sanitized_list
        else:
            # Unknown argument type fails closed
            return False, {}, f"BLOCKED by policy: unknown argument key '{key}' of type {type(value).__name__}"

    return True, sanitized, None
