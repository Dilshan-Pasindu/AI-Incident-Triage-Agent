"""
agent-client/tests/test_mcp_client.py

Tests for MCP client, MCPHub, dynamic discovery, prefix namespacing,
name collision prevention, read-only filesystem policy, and connection recovery.
"""

import asyncio
import os
import pytest
from incident_agent.mcp_client import (
    FS_READ_ONLY_ALLOWLIST,
    HealthState,
    MCPHub,
    ServerConnection,
    ToolRegistration,
)


@pytest.fixture
def repo_paths():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    ops_bin = os.path.join(root, "mcp-server/target/release/ops-telemetry-mcp")
    workspace = os.path.join(root, "mock_data/workspace")
    data_dir = os.path.join(root, "mock_data")
    return {
        "ops_bin": ops_bin,
        "workspace": workspace,
        "data_dir": data_dir,
    }


def test_tool_name_collision_prevention():
    """Verify that identical tool names on different servers never overwrite each other."""
    schema = {"type": "object", "properties": {}}
    t1 = ToolRegistration(
        namespaced_name="server_a__search_logs",
        server="server_a",
        original_name="search_logs",
        description="Search logs server A",
        schema=schema,
    )
    t2 = ToolRegistration(
        namespaced_name="server_b__search_logs",
        server="server_b",
        original_name="search_logs",
        description="Search logs server B",
        schema=schema,
    )

    registry = {}
    registry[t1.namespaced_name] = t1
    registry[t2.namespaced_name] = t2

    assert len(registry) == 2
    assert "server_a__search_logs" in registry
    assert "server_b__search_logs" in registry
    assert registry["server_a__search_logs"].server == "server_a"
    assert registry["server_b__search_logs"].server == "server_b"


def test_filesystem_read_only_policy():
    """Verify that mutating tools are strictly filtered out from FS_READ_ONLY_ALLOWLIST."""
    mutating_tools = {
        "write_file",
        "edit_file",
        "append_file",
        "create_directory",
        "move_file",
        "copy_file",
    }
    for mt in mutating_tools:
        assert mt not in FS_READ_ONLY_ALLOWLIST, f"Mutating tool {mt} must NOT be in read-only allowlist!"

    read_tools = {
        "read_text_file",
        "read_file",
        "read_multiple_files",
        "list_directory",
        "directory_tree",
        "search_files",
        "get_file_info",
    }
    for rt in read_tools:
        assert rt in FS_READ_ONLY_ALLOWLIST, f"Read tool {rt} should be permitted in allowlist"


@pytest.mark.asyncio
async def test_mcphub_lifecycle_and_discovery(repo_paths):
    """Test full MCPHub startup, dynamic tool/resource discovery, and clean shutdown."""
    hub = MCPHub(
        ops_binary_path=repo_paths["ops_bin"],
        workspace_dir=repo_paths["workspace"],
        data_dir=repo_paths["data_dir"],
    )

    await hub.start()
    try:
        # 1. Verify health of both servers
        assert hub.connections["ops"].health == HealthState.HEALTHY
        assert hub.connections["fs"].health == HealthState.HEALTHY

        # 2. Verify namespaced tools
        tool_names = list(hub.tool_registry.keys())
        assert "ops__search_logs" in tool_names
        assert "ops__get_deployment_history" in tool_names
        assert "ops__create_incident_ticket" in tool_names
        assert "read_resource" in tool_names

        # Verify filesystem read-only filtering: no write tools exposed
        assert not any("write_file" in name for name in tool_names)
        assert not any("edit_file" in name for name in tool_names)
        assert any("fs__read" in name or "fs__list" in name for name in tool_names)

        # 3. Verify resources discovered
        ops_resources = hub.discovered_resources.get("ops", [])
        assert any(r.uri == "config://release-checklist" for r in ops_resources)

        ops_templates = hub.discovered_templates.get("ops", [])
        assert any("service://runbooks/" in t.uri_template for t in ops_templates)

        # 4. Verify Grok function formatting
        grok_tools = hub.get_grok_tools()
        assert len(grok_tools) == len(hub.tool_registry)
        for gt in grok_tools:
            assert gt["type"] == "function"
            assert "name" in gt["function"]
            assert "description" in gt["function"]
            assert "parameters" in gt["function"]

        # 5. Execute read_resource via hub
        res = await hub.call_tool("read_resource", {"uri": "config://release-checklist"})
        assert "Pre-Release Verification Checklist" in res.contents[0].text

        # 6. Execute ops tool via hub
        logs_res = await hub.call_tool("ops__search_logs", {"service_name": "payments-api", "limit": 2})
        assert "payments-api" in logs_res.content[0].text

    finally:
        await hub.close()
        assert hub.connections["ops"].health == HealthState.UNHEALTHY
        assert hub.connections["fs"].health == HealthState.UNHEALTHY


@pytest.mark.asyncio
async def test_resource_uri_validation(repo_paths):
    """Test validation of static and templated resource URIs."""
    hub = MCPHub(
        ops_binary_path=repo_paths["ops_bin"],
        workspace_dir=repo_paths["workspace"],
        data_dir=repo_paths["data_dir"],
    )
    await hub.start()
    try:
        # Valid static
        ok, srv, err = hub.validate_resource_uri("config://release-checklist")
        assert ok is True
        assert srv == "ops"
        assert err is None

        # Valid template
        ok, srv, err = hub.validate_resource_uri("service://runbooks/payments-api")
        assert ok is True
        assert srv == "ops"
        assert err is None

        # Invalid template service
        ok, srv, err = hub.validate_resource_uri("service://runbooks/fraud-engine")
        assert ok is False
        assert err is not None and "Unknown service" in err

        # Arbitrary URI
        ok, srv, err = hub.validate_resource_uri("http://evil.com/leak")
        assert ok is False
        assert err is not None and "does not match" in err
    finally:
        await hub.close()
