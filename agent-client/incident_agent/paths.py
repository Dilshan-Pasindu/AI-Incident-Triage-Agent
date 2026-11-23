"""
incident_agent/paths.py

Single source of truth for all filesystem paths in the repository.
Resolves everything relative to the repository root (the parent of the
`agent-client/` directory) so the CLI, eval suite, web backend, and tests
all find the same files regardless of which directory they are run from.

Override any path with an environment variable if needed (useful for CI or
Docker where the layout may differ).
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo root: two levels up from this file
#   agent-client/incident_agent/paths.py  → parent → agent-client/ → parent → repo root
# ---------------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
REPO_ROOT: Path = _THIS_FILE.parent.parent.parent

# ---------------------------------------------------------------------------
# Well-known paths — override via env vars for non-standard layouts
# ---------------------------------------------------------------------------
RUST_BINARY: Path = Path(
    os.environ.get(
        "OPS_BINARY_PATH",
        str(REPO_ROOT / "mcp-server" / "target" / "release" / "ops-telemetry-mcp"),
    )
)

MOCK_DATA_DIR: Path = Path(
    os.environ.get("OPS_DATA_DIR", str(REPO_ROOT / "mock_data"))
)

WORKSPACE_DIR: Path = Path(
    os.environ.get("WORKSPACE_DIR", str(MOCK_DATA_DIR / "workspace"))
)

TRACE_FILE: Path = Path(
    os.environ.get("TRACE_FILE", str(REPO_ROOT / "agent_traces.jsonl"))
)

EVAL_FILE: Path = Path(
    os.environ.get("EVAL_FILE", str(REPO_ROOT / "eval_results.md"))
)
