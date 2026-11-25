"""
web-backend/tests/test_server.py

Integration tests for the FastAPI backend and Server-Sent Events (SSE) streaming.
Verifies:
- Health check endpoint
- Run creation and SSE event streaming
- Last-Event-ID event replay
- Interactive approval resolution via HTTP
- Cooperative cancellation
"""

import asyncio
from contextlib import asynccontextmanager
import pytest
from httpx import ASGITransport, AsyncClient

from app.server import app


@asynccontextmanager
async def get_test_client():
    """Helper context manager providing an active test client with initialized lifespan."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        async with app.router.lifespan_context(app):
            yield client


@pytest.mark.asyncio
async def test_health_endpoint():
    """Verify /api/health reports healthy MCP servers and discovered tools."""
    async with get_test_client() as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "ops" in data["mcp_servers"]
        assert "fs" in data["mcp_servers"]
        assert data["tools_count"] > 0
        assert "ops__search_logs" in data["tools"]


@pytest.mark.asyncio
async def test_create_run_and_stream_events():
    """Verify run creation and SSE streaming for an auth logs query."""
    async with get_test_client() as client:
        create_resp = await client.post(
            "/api/runs",
            json={"query": "Show the last 5 ERROR logs for auth-service", "model": "mock"},
        )
        assert create_resp.status_code == 201
        run_data = create_resp.json()
        run_id = run_data["run_id"]
        assert run_id is not None

        # Wait briefly for run to execute
        await asyncio.sleep(0.2)

        # Fetch run detail
        detail_resp = await client.get(f"/api/runs/{run_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["run_id"] == run_id
        assert detail["state"] in ("completed", "running")
        assert len(detail["events"]) > 0

        # Stream SSE events
        stream_resp = await client.get(f"/api/runs/{run_id}/events")
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers["content-type"]
        text = stream_resp.text
        assert "event: run_started" in text
        assert "event: final_answer" in text


@pytest.mark.asyncio
async def test_event_replay_last_event_id():
    """Verify Last-Event-ID parameter replays only events after the specified ID."""
    async with get_test_client() as client:
        create_resp = await client.post(
            "/api/runs",
            json={"query": "Show the last 5 ERROR logs for auth-service", "model": "mock"},
        )
        run_id = create_resp.json()["run_id"]
        await asyncio.sleep(0.2)

        # Replay with last_event_id=2
        replay_resp = await client.get(f"/api/runs/{run_id}/events?last_event_id=2")
        assert replay_resp.status_code == 200
        lines = replay_resp.text.splitlines()

        event_ids = []
        for line in lines:
            if line.startswith("id: "):
                event_ids.append(int(line.split("id: ")[1]))

        # Every replayed event must have event_id > 2
        for eid in event_ids:
            assert eid > 2


@pytest.mark.asyncio
async def test_approval_resolution_via_api():
    """Verify mutating ticket creation pauses for approval and resumes when approved via HTTP."""
    async with get_test_client() as client:
        create_resp = await client.post(
            "/api/runs",
            json={"query": "Create a critical incident ticket for payments-api outage", "model": "mock"},
        )
        run_id = create_resp.json()["run_id"]

        # Poll for pending approval event
        approval_id = None
        for _ in range(20):
            await asyncio.sleep(0.05)
            detail_resp = await client.get(f"/api/runs/{run_id}")
            events = detail_resp.json().get("events", [])
            for ev in events:
                if ev.get("event_type") == "approval_required":
                    approval_id = ev.get("approval_id")
                    break
            if approval_id:
                break

        assert approval_id is not None, "Did not receive approval_required event"

        # Submit HTTP approval decision
        approve_resp = await client.post(
            f"/api/runs/{run_id}/approvals/{approval_id}",
            json={"decision": "approve"},
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["decision"] == "approved"

        # Wait for completion
        await asyncio.sleep(0.2)
        final_resp = await client.get(f"/api/runs/{run_id}")
        final_data = final_resp.json()
        assert final_data["state"] == "completed"
        assert "ticket has been successfully created" in final_data.get("result_preview", "").lower()


@pytest.mark.asyncio
async def test_cancel_run_via_api():
    """Verify ongoing run can be cancelled via /api/runs/{run_id}/cancel and emits run_stopped."""
    async with get_test_client() as client:
        create_resp = await client.post(
            "/api/runs",
            json={"query": "Create a critical incident ticket for payments-api outage", "model": "mock"},
        )
        run_id = create_resp.json()["run_id"]

        # Wait until awaiting_approval so the run is guaranteed to be mid-flight
        for _ in range(20):
            await asyncio.sleep(0.05)
            d = (await client.get(f"/api/runs/{run_id}")).json()
            if d["state"] == "awaiting_approval":
                break

        cancel_resp = await client.post(
            f"/api/runs/{run_id}/cancel",
            json={"reason": "Operator aborted"},
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

        detail_resp = await client.get(f"/api/runs/{run_id}")
        detail = detail_resp.json()
        assert detail["state"] == "cancelled"
        assert any(
            ev.get("event_type") == "run_stopped" and ev.get("reason") == "cancelled"
            for ev in detail["events"]
        )


@pytest.mark.asyncio
async def test_expired_approval_returns_410_and_unblocks_run():
    """Verify resolving an expired approval returns 410 and unblocks the run cleanly."""
    from datetime import datetime, timedelta, timezone
    import app.server as srv

    async with get_test_client() as client:
        create_resp = await client.post(
            "/api/runs",
            json={"query": "Create a critical incident ticket for payments-api outage", "model": "mock"},
        )
        run_id = create_resp.json()["run_id"]

        approval_id = None
        for _ in range(20):
            await asyncio.sleep(0.05)
            events = (await client.get(f"/api/runs/{run_id}")).json().get("events", [])
            for ev in events:
                if ev.get("event_type") == "approval_required":
                    approval_id = ev.get("approval_id")
                    break
            if approval_id:
                break

        assert approval_id is not None
        assert srv.approval_service is not None
        rec = srv.approval_service.get_record(approval_id)
        assert rec is not None
        rec.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)

        resp = await client.post(
            f"/api/runs/{run_id}/approvals/{approval_id}",
            json={"decision": "approve"},
        )
        assert resp.status_code == 410

        await asyncio.sleep(0.2)
        detail = (await client.get(f"/api/runs/{run_id}")).json()
        assert detail["state"] == "completed"
        assert any(
            ev.get("event_type") == "approval_resolved" and ev.get("decision") == "expired"
            for ev in detail["events"]
        )
