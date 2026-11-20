#!/usr/bin/env python3
"""
regenerate_timestamps.py

Utility script that shifts all timestamps in mock_data/logs.json and mock_data/deployments.json
so that the newest log event is always approximately 'now minus 5 minutes' (UTC).

This guarantees that:
1. 'window_hours' filters in telemetry queries test realistic recent vs historical windows.
2. The 24-hour release-checklist and deployment queries always evaluate relative to the present.
3. Tests and evaluation benchmarks produce deterministic, reproducible results regardless of when run.

Usage:
    python mock_data/regenerate_timestamps.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


def parse_iso8601(ts_str: str) -> datetime:
    """Parse ISO8601 string to timezone-aware UTC datetime."""
    # Replace trailing 'Z' if present for fromisoformat compatibility
    cleaned = ts_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def format_iso8601(dt: datetime) -> str:
    """Format datetime as UTC ISO8601 with trailing Z."""
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def shift_timestamps(data_dir: Path | None = None) -> tuple[int, int]:
    if data_dir is None:
        data_dir = Path(__file__).resolve().parent

    logs_file = data_dir / "logs.json"
    deployments_file = data_dir / "deployments.json"

    if not logs_file.exists():
        raise FileNotFoundError(f"Missing {logs_file}")
    if not deployments_file.exists():
        raise FileNotFoundError(f"Missing {deployments_file}")

    with open(logs_file, "r", encoding="utf-8") as f:
        logs = json.load(f)

    with open(deployments_file, "r", encoding="utf-8") as f:
        deployments = json.load(f)

    if not logs:
        raise ValueError("logs.json is empty")

    # Find the maximum timestamp in logs
    log_dates = [parse_iso8601(entry["timestamp"]) for entry in logs]
    max_log_time = max(log_dates)

    # Target: newest log event should be 5 minutes ago from now (UTC)
    now_utc = datetime.now(timezone.utc)
    target_time = now_utc - timedelta(minutes=5)
    delta = target_time - max_log_time

    # Shift all logs
    for entry in logs:
        old_dt = parse_iso8601(entry["timestamp"])
        entry["timestamp"] = format_iso8601(old_dt + delta)

    # Shift all deployments
    for entry in deployments:
        old_dt = parse_iso8601(entry["timestamp"])
        entry["timestamp"] = format_iso8601(old_dt + delta)

    # Write back
    with open(logs_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
        f.write("\n")

    with open(deployments_file, "w", encoding="utf-8") as f:
        json.dump(deployments, f, indent=2)
        f.write("\n")

    return len(logs), len(deployments)


if __name__ == "__main__":
    logs_count, dep_count = shift_timestamps()
    print(f"Successfully shifted timestamps: {logs_count} logs, {dep_count} deployments.")
