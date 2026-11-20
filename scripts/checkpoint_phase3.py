#!/usr/bin/env python3
"""
scripts/checkpoint_phase3.py

Phase 3 Checkpoint Verification Script:
1. Connects to both servers (ops-telemetry-mcp and server-filesystem).
2. Prints dynamically discovered tools and resources with namespacing.
3. Calls one tool from each server.
4. Kills/fails one server connection (ops).
5. Detects its failure.
6. Reconnects only that server.
7. Demonstrates that the other connection (fs) remained untouched.
"""

import asyncio
import json
import os
import sys

# Ensure agent-client is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../agent-client")))

from mcp_client import HealthState, MCPHub


async def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ops_bin = os.path.join(root, "mcp-server/target/release/ops-telemetry-mcp")
    workspace = os.path.join(root, "mock_data/workspace")
    data_dir = os.path.join(root, "mock_data")

    print("==================================================")
    print("STEP 1: CONNECT TO BOTH SERVERS VIA MCPHUB")
    print("==================================================")
    hub = MCPHub(
        ops_binary_path=ops_bin,
        workspace_dir=workspace,
        data_dir=data_dir,
    )
    await hub.start()
    print(f"Server 'ops' status: {hub.connections['ops'].health.value.upper()}")
    print(f"Server 'fs'  status: {hub.connections['fs'].health.value.upper()}")

    print("\n==================================================")
    print("STEP 2: DISCOVERED TOOLS AND RESOURCES")
    print("==================================================")
    print(f"Total Discovered Tools: {len(hub.tool_registry)}")
    for name, reg in sorted(hub.tool_registry.items()):
        mut_flag = "[MUTATING]" if reg.is_mutating else "[READ-ONLY]"
        print(f"  - {name:32} ({reg.server:10}) {mut_flag}")

    print("\nDiscovered Static Resources:")
    for srv, res_list in hub.discovered_resources.items():
        for r in res_list:
            print(f"  - [{srv}] {r.uri}: {r.name}")

    print("\nDiscovered Resource Templates:")
    for srv, tpl_list in hub.discovered_templates.items():
        for t in tpl_list:
            print(f"  - [{srv}] {t.uri_template}: {t.name}")

    print("\n==================================================")
    print("STEP 3: CALL ONE TOOL FROM EACH SERVER")
    print("==================================================")
    print("Calling ops__search_logs (payments-api, limit=1)...")
    ops_res = await hub.call_tool("ops__search_logs", {"service_name": "payments-api", "limit": 1})
    print("ops__search_logs Result:")
    print(ops_res.content[0].text[:180] + "...\n")

    print("Calling fs__read_text_file (RELEASE_NOTES.md)...")
    fs_res = await hub.call_tool("fs__read_text_file", {"path": os.path.join(workspace, "RELEASE_NOTES.md"), "tail": 5})
    print("fs__read_text_file Result:")
    print(fs_res.content[0].text[:180] + "...")

    print("\n==================================================")
    print("STEP 4: KILL OPS SERVER PROCESS / SIMULATE FAILURE")
    print("==================================================")
    print("Simulating abrupt failure on 'ops' connection...")
    await hub.connections["ops"].simulate_failure()
    print(f"ops connection state: {hub.connections['ops'].health.value.upper()}")
    print(f"fs  connection state: {hub.connections['fs'].health.value.upper()} (untouched!)")

    print("\n==================================================")
    print("STEP 5 & 6: DETECT FAILURE & RECONNECT ONLY OPS")
    print("==================================================")
    print("Calling ops__search_logs again (triggers ensure_connection_healthy)...")
    recovered_res = await hub.call_tool("ops__search_logs", {"service_name": "payments-api", "limit": 1})
    print(f"ops connection state after recovery: {hub.connections['ops'].health.value.upper()}")
    print("Recovered Call Result:")
    print(recovered_res.content[0].text[:180] + "...\n")

    print("==================================================")
    print("STEP 7: VERIFY FS SERVER WAS UNTOUCHED")
    print("==================================================")
    print(f"fs connection state: {hub.connections['fs'].health.value.upper()}")
    fs_verify = await hub.call_tool("fs__list_directory", {"path": workspace})
    print("fs__list_directory Result:")
    print(fs_verify.content[0].text.strip())

    await hub.close()
    print("\nMCPHub shutdown cleanly. Checkpoint complete.")


if __name__ == "__main__":
    asyncio.run(main())
