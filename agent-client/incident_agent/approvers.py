"""
agent-client/approvers.py

Human-in-the-Loop (HITL) Approval Service and Approver Abstractions.
Enforces that ALL state-mutating tool calls pass through ONE central ApprovalService.
Approvers only supply human decisions; they cannot execute tools or bypass the service.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, Optional, Protocol


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalSource(str, Enum):
    CLI = "cli"
    WEB = "web"
    SCRIPTED = "scripted"
    AUTO = "auto"


def compute_canonical_payload_hash(payload: Dict[str, Any]) -> str:
    """
    Compute deterministic SHA-256 hash over canonical JSON representation
    (keys sorted, compact separators without extra whitespace).
    """
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class ApprovalRecord:
    def __init__(
        self,
        approval_id: str,
        run_id: str,
        tool_call_id: str,
        tool_name: str,
        payload: Dict[str, Any],
        payload_hash: str,
        expires_at: datetime,
        approval_source: ApprovalSource = ApprovalSource.CLI,
    ):
        self.approval_id = approval_id
        self.run_id = run_id
        self.tool_call_id = tool_call_id
        self.tool_name = tool_name
        self.payload = payload
        self.payload_hash = payload_hash
        self.status = ApprovalStatus.PENDING
        self.expires_at = expires_at
        self.approval_source = approval_source
        self.resolved_at: Optional[datetime] = None
        self.used: bool = False

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "run_id": self.run_id,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "payload": self.payload,
            "payload_hash": self.payload_hash,
            "status": self.status.value,
            "expires_at": self.expires_at.isoformat(),
            "approval_source": self.approval_source.value,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "used": self.used,
        }


class Approver(Protocol):
    async def request_decision(self, record: ApprovalRecord) -> str:
        """Return 'approve' or 'reject'."""
        ...


class CliApprover:
    """Interactive CLI approver requesting human input via rich terminal."""

    def __init__(self, auto_approve: bool = False):
        self.auto_approve = auto_approve

    async def request_decision(self, record: ApprovalRecord) -> str:
        if self.auto_approve:
            return "approve"

        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        payload_pretty = json.dumps(record.payload, indent=2)

        console.print("\n")
        console.print(
            Panel(
                f"[bold yellow]Tool:[/bold yellow] {record.tool_name}\n"
                f"[bold yellow]Proposed Payload:[/bold yellow]\n{payload_pretty}\n\n"
                f"[bold yellow]Expires In:[/bold yellow] 120 seconds",
                title="[bold red]⚠️ HUMAN APPROVAL REQUIRED FOR STATE MUTATION[/bold red]",
                border_style="red",
            )
        )

        loop = asyncio.get_running_loop()
        # Default action is Reject for safety
        choice = await loop.run_in_executor(
            None,
            lambda: input("Approve state mutation? [y/N]: ").strip().lower(),
        )
        if choice in ("y", "yes"):
            return "approve"
        return "reject"


class ScriptedApprover:
    """Scripted approver for testing and automated benchmarks."""

    def __init__(self, decision: str = "approve", source: ApprovalSource = ApprovalSource.SCRIPTED):
        self.decision = decision
        self.source = source

    async def request_decision(self, record: ApprovalRecord) -> str:
        record.approval_source = self.source
        return self.decision


class ApprovalService:
    """
    Central Approval Authority.
    Every state-mutating tool call must create and verify an approval record here.
    """

    def __init__(self, default_timeout_seconds: float = 120.0):
        self.default_timeout_seconds = default_timeout_seconds
        self._records: Dict[str, ApprovalRecord] = {}
        self._lock = asyncio.Lock()

    def get_records_for_run(self, run_id: str) -> List[ApprovalRecord]:
        """Return all approval records matching the run_id."""
        return [r for r in self._records.values() if r.run_id == run_id]

    async def create_request(
        self,
        run_id: str,
        tool_call_id: str,
        tool_name: str,
        payload: Dict[str, Any],
        source: ApprovalSource = ApprovalSource.CLI,
        timeout_seconds: Optional[float] = None,
    ) -> ApprovalRecord:
        """Create a pending approval record with canonical payload hash."""
        async with self._lock:
            approval_id = str(uuid.uuid4())
            payload_hash = compute_canonical_payload_hash(payload)
            timeout = timeout_seconds or self.default_timeout_seconds
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=timeout)

            record = ApprovalRecord(
                approval_id=approval_id,
                run_id=run_id,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                payload=payload,
                payload_hash=payload_hash,
                expires_at=expires_at,
                approval_source=source,
            )
            self._records[approval_id] = record
            return record

    async def resolve(
        self,
        approval_id: str,
        run_id: str,
        tool_call_id: str,
        decision: str,
        source: Optional[ApprovalSource] = None,
    ) -> ApprovalRecord:
        """
        Resolve pending approval.
        Enforces run_id, tool_call_id, single-use, and expiration checks.
        """
        async with self._lock:
            if approval_id not in self._records:
                raise KeyError(f"Approval ID '{approval_id}' not found.")

            record = self._records[approval_id]

            # Cross-run check
            if record.run_id != run_id:
                raise ValueError(f"Approval belongs to run '{record.run_id}', not '{run_id}'.")

            # Tool call binding check
            if record.tool_call_id != tool_call_id:
                raise ValueError(f"Approval belongs to tool_call '{record.tool_call_id}', not '{tool_call_id}'.")

            # Check if already resolved
            if record.status != ApprovalStatus.PENDING:
                raise RuntimeError(f"Approval '{approval_id}' has already been resolved as {record.status.value}.")

            # Check expiration
            if record.is_expired():
                record.status = ApprovalStatus.EXPIRED
                record.resolved_at = datetime.now(timezone.utc)
                raise TimeoutError(f"Approval '{approval_id}' has expired.")

            if source:
                record.approval_source = source

            record.resolved_at = datetime.now(timezone.utc)
            if decision.lower() in ("approve", "approved"):
                record.status = ApprovalStatus.APPROVED
            else:
                record.status = ApprovalStatus.REJECTED

            return record

    async def verify_before_execution(
        self,
        approval_id: str,
        run_id: str,
        tool_call_id: str,
        current_payload: Dict[str, Any],
    ) -> bool:
        """
        Verification backstop immediately before MCP call.
        Recomputes payload hash and validates single use.
        """
        async with self._lock:
            if approval_id not in self._records:
                return False

            record = self._records[approval_id]

            # Validate state
            if record.status != ApprovalStatus.APPROVED:
                return False
            if record.run_id != run_id or record.tool_call_id != tool_call_id:
                return False
            if record.used:
                return False  # Single use only

            # Recompute canonical hash immediately before execution
            current_hash = compute_canonical_payload_hash(current_payload)
            if current_hash != record.payload_hash:
                return False  # Payload tampering detected

            record.used = True
            return True

    async def cancel_run_approvals(self, run_id: str) -> None:
        """Reject all pending approvals for a cancelled run."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            for record in self._records.values():
                if record.run_id == run_id and record.status == ApprovalStatus.PENDING:
                    record.status = ApprovalStatus.CANCELLED
                    record.resolved_at = now

    def get_record(self, approval_id: str) -> Optional[ApprovalRecord]:
        return self._records.get(approval_id)
