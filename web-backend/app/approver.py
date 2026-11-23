"""
web-backend/app/approver.py

Web-based Approver implementation for Human-in-the-Loop (HITL) execution.
Suspends agent execution via an asyncio.Future until an HTTP decision is submitted.
Only supplies human decisions to the core ApprovalService; never executes tools directly.
"""

from __future__ import annotations

import asyncio
from typing import Dict

from incident_agent.approvers import ApprovalRecord, ApprovalService, ApprovalSource


class WebApprover:
    """Approver for Web UI / SSE mode. Suspends execution until HTTP resolution."""

    def __init__(self, service: ApprovalService):
        self.service = service
        self._waiters: Dict[str, asyncio.Future[str]] = {}

    def register_waiter(self, approval_id: str) -> asyncio.Future[str]:
        fut = asyncio.get_running_loop().create_future()
        self._waiters[approval_id] = fut
        return fut

    def resolve_waiter(self, approval_id: str, decision: str) -> None:
        if approval_id in self._waiters and not self._waiters[approval_id].done():
            self._waiters[approval_id].set_result(decision)

    async def request_decision(self, record: ApprovalRecord) -> str:
        record.approval_source = ApprovalSource.WEB
        fut = self.register_waiter(record.approval_id)
        try:
            return await fut
        finally:
            self._waiters.pop(record.approval_id, None)
