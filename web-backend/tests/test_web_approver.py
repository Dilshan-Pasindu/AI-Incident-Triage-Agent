"""
web-backend/tests/test_web_approver.py

Tests for WebApprover HITL decision resolution in web-backend.
Verifies asynchronous resolution, decision binding, and source attribution.
"""

import asyncio
import pytest
from incident_agent.approvers import ApprovalService, ApprovalSource
from app.approver import WebApprover


@pytest.mark.asyncio
async def test_web_approver_resolution():
    """Verify WebApprover registers waiter future and resolves with web source."""
    service = ApprovalService()
    web = WebApprover(service)
    record = await service.create_request("run_w", "tc_w", "tool", {"b": 2})

    async def async_resolve():
        await asyncio.sleep(0.01)
        web.resolve_waiter(record.approval_id, "reject")

    asyncio.create_task(async_resolve())
    decision = await web.request_decision(record)
    assert decision == "reject"
    assert record.approval_source == ApprovalSource.WEB
