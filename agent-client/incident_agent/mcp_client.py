"""
agent-client/mcp_client.py

Decoupled Python MCP Client and MCPHub for Incident Triage Agent.
Connects to:
1. Custom Rust server: ops-telemetry-mcp
2. Official Node server: @modelcontextprotocol/server-filesystem

Implements:
- ServerConnection: lifecycle, AnyIO task boundary isolation, health checks, stderr capture.
- MCPHub: multi-server registry, prefix namespacing (ops__, fs__), collision prevention.
- Dynamic tool & resource discovery with Grok/OpenAI function calling schemas.
- Configurable read-only filesystem policy (filtering out mutating tools).
- Independent connection recovery (reconnects suspect/unhealthy server without touching others).
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Resource as McpResource, ResourceTemplate as McpResourceTemplate

from incident_agent.paths import MOCK_DATA_DIR

TOOL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

# Configurable Read-Only Filesystem Allowlist
# Discovered from real @modelcontextprotocol/server-filesystem tool capabilities.
# All mutating tools (write_file, edit_file, append_file, create_directory, move_file, copy_file)
# are strictly excluded.
FS_READ_ONLY_ALLOWLIST: Set[str] = {
    "read_text_file",
    "read_file",
    "read_multiple_files",
    "list_directory",
    "list_directory_with_sizes",
    "directory_tree",
    "search_files",
    "get_file_info",
    "list_allowed_directories",
}


class HealthState(str, Enum):
    HEALTHY = "healthy"
    SUSPECT = "suspect"
    UNHEALTHY = "unhealthy"


@dataclass
class ToolRegistration:
    namespaced_name: str
    server: str
    original_name: str
    description: str
    schema: dict
    annotations: dict = field(default_factory=dict)
    is_mutating: bool = False

    def to_grok_function(self) -> dict:
        """Convert discovered tool to Grok/OpenAI function format."""
        return {
            "type": "function",
            "function": {
                "name": self.namespaced_name,
                "description": self.description,
                "parameters": self.schema,
            },
        }


class ServerConnection:
    """
    Manages an independent MCP ClientSession over stdio connected to ONE server.
    
    AnyIO Safety Rule: stdio_client context manager is opened, executed,
    and closed strictly inside a single dedicated owner task. Other asyncio tasks
    interact through a command queue.
    """

    def __init__(
        self,
        name: str,
        params: StdioServerParameters,
        capture_stderr: bool = True,
    ):
        self.name = name
        self.params = params
        self.capture_stderr = capture_stderr
        self.health: HealthState = HealthState.UNHEALTHY
        self._cmd_queue: asyncio.Queue = asyncio.Queue()
        self._owner_task: Optional[asyncio.Task] = None
        self._ready_event = asyncio.Event()
        self._init_error: Optional[Exception] = None
        self._reconnect_lock = asyncio.Lock()
        self._stderr_file: Any = None
        self._process_pid: Optional[int] = None

    @property
    def pid(self) -> Optional[int]:
        return self._process_pid

    def get_recent_stderr(self, max_bytes: int = 4096) -> str:
        """Read recent stderr for diagnostic telemetry."""
        if not self._stderr_file:
            return ""
        try:
            self._stderr_file.flush()
            path = self._stderr_file.name
            size = os.path.getsize(path)
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                if size > max_bytes:
                    f.seek(size - max_bytes)
                return f.read()
        except Exception:
            return ""

    async def connect(self, timeout: float = 30.0) -> None:
        """Initialize session in dedicated owner task."""
        async with self._reconnect_lock:
            if self._owner_task and not self._owner_task.done():
                await self._close_internal()

            self._ready_event.clear()
            self._init_error = None
            if self.capture_stderr:
                self._stderr_file = tempfile.NamedTemporaryFile(
                    prefix=f"mcp_stderr_{self.name}_", delete=False, mode="w+"
                )

            self._owner_task = asyncio.create_task(self._run_owner())

            try:
                await asyncio.wait_for(self._ready_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                self.health = HealthState.UNHEALTHY
                if self._owner_task:
                    self._owner_task.cancel()
                raise TimeoutError(f"Connection to MCP server '{self.name}' timed out after {timeout}s")

            if self._init_error:
                self.health = HealthState.UNHEALTHY
                stderr_text = self.get_recent_stderr()
                err_msg = f"Failed to initialize MCP connection '{self.name}': {self._init_error}"
                if stderr_text:
                    err_msg += f"\n--- {self.name} stderr ---\n{stderr_text}"
                raise ConnectionError(err_msg) from self._init_error

            self.health = HealthState.HEALTHY

    async def _run_owner(self) -> None:
        """Dedicated task owning the stdio_client and ClientSession contexts."""
        err_stream = self._stderr_file if self._stderr_file else sys.stderr
        try:
            async with stdio_client(self.params, errlog=err_stream) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    self.health = HealthState.HEALTHY
                    self._ready_event.set()

                    while True:
                        cmd, args, fut = await self._cmd_queue.get()
                        if cmd == "STOP":
                            fut.set_result(None)
                            break

                        try:
                            if cmd == "ping":
                                # Health check ping
                                await session.send_ping()
                                fut.set_result(True)
                            elif cmd == "list_tools":
                                res = await session.list_tools()
                                fut.set_result(res)
                            elif cmd == "list_resources":
                                res = await session.list_resources()
                                fut.set_result(res)
                            elif cmd == "list_resource_templates":
                                res = await session.list_resource_templates()
                                fut.set_result(res)
                            elif cmd == "call_tool":
                                res = await session.call_tool(args["name"], args["arguments"])
                                fut.set_result(res)
                            elif cmd == "read_resource":
                                res = await session.read_resource(args["uri"])
                                fut.set_result(res)
                            else:
                                fut.set_exception(ValueError(f"Unknown command: {cmd}"))
                        except Exception as exc:
                            if not fut.done():
                                fut.set_exception(exc)
        except Exception as exc:
            self.health = HealthState.UNHEALTHY
            self._init_error = exc
            self._ready_event.set()
            # Drain and fail any pending commands in queue
            while not self._cmd_queue.empty():
                try:
                    _, _, fut = self._cmd_queue.get_nowait()
                    if not fut.done():
                        fut.set_exception(ConnectionError(f"Server '{self.name}' disconnected: {exc}"))
                except Exception:
                    pass

    async def _dispatch(self, cmd: str, args: dict, timeout: Optional[float] = None) -> Any:
        if self.health == HealthState.UNHEALTHY or not self._owner_task or self._owner_task.done():
            raise ConnectionError(f"ServerConnection '{self.name}' is not healthy (state={self.health})")

        fut = asyncio.get_running_loop().create_future()
        await self._cmd_queue.put((cmd, args, fut))

        if timeout is not None:
            return await asyncio.wait_for(fut, timeout=timeout)
        return await fut

    async def health_check(self, timeout: float = 3.0) -> bool:
        """Perform active ping health check."""
        try:
            await self._dispatch("ping", {}, timeout=timeout)
            self.health = HealthState.HEALTHY
            return True
        except Exception:
            self.health = HealthState.UNHEALTHY
            return False

    async def reconnect(self) -> None:
        """Safely reconnect only this server connection."""
        await self.connect()

    async def simulate_failure(self) -> None:
        """Simulate an abrupt server process crash or failure."""
        async with self._reconnect_lock:
            if self._owner_task and not self._owner_task.done():
                self._owner_task.cancel()
                try:
                    await self._owner_task
                except (asyncio.CancelledError, Exception):
                    pass
            self.health = HealthState.UNHEALTHY

    async def list_tools(self, timeout: float = 10.0) -> Any:
        return await self._dispatch("list_tools", {}, timeout=timeout)

    async def list_resources(self, timeout: float = 10.0) -> Any:
        return await self._dispatch("list_resources", {}, timeout=timeout)

    async def list_resource_templates(self, timeout: float = 10.0) -> Any:
        return await self._dispatch("list_resource_templates", {}, timeout=timeout)

    async def call_tool(self, name: str, arguments: dict, timeout: Optional[float] = None) -> Any:
        return await self._dispatch("call_tool", {"name": name, "arguments": arguments}, timeout=timeout)

    async def read_resource(self, uri: str, timeout: Optional[float] = None) -> Any:
        return await self._dispatch("read_resource", {"uri": uri}, timeout=timeout)

    async def _close_internal(self) -> None:
        if self._owner_task and not self._owner_task.done():
            try:
                fut = asyncio.get_running_loop().create_future()
                await self._cmd_queue.put(("STOP", {}, fut))
                await asyncio.wait_for(fut, timeout=2.0)
            except Exception:
                pass
            finally:
                self._owner_task.cancel()
                try:
                    await self._owner_task
                except (asyncio.CancelledError, Exception):
                    pass
        self._owner_task = None
        self.health = HealthState.UNHEALTHY
        if self._stderr_file:
            try:
                self._stderr_file.close()
            except Exception:
                pass

    async def close(self) -> None:
        async with self._reconnect_lock:
            await self._close_internal()


class MCPHub:
    """
    Manages connections to both ops-telemetry-mcp (Rust) and server-filesystem (Node).
    Provides unified dynamic tool and resource discovery with prefix namespacing.
    """

    def __init__(
        self,
        ops_binary_path: str,
        workspace_dir: str,
        data_dir: Optional[str] = None,
    ):
        self.ops_binary_path = os.path.abspath(ops_binary_path)
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.data_dir = os.path.abspath(data_dir) if data_dir else str(MOCK_DATA_DIR)

        # Resolve filesystem server runner
        # Check for locally installed npm package binary first, fall back to npx
        local_fs_bin = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "node_modules/.bin/mcp-server-filesystem"))
        if os.path.exists(local_fs_bin):
            fs_command = local_fs_bin
            fs_args = [self.workspace_dir]
        else:
            fs_command = "npx"
            fs_args = ["-y", "@modelcontextprotocol/server-filesystem", self.workspace_dir]

        # 1. Ops Server Parameters
        ops_params = StdioServerParameters(
            command=self.ops_binary_path,
            args=[],
            env={
                **os.environ,
                "OPS_DATA_DIR": self.data_dir,
                "RUST_BACKTRACE": "1",
            },
        )

        # 2. Filesystem Server Parameters
        fs_params = StdioServerParameters(
            command=fs_command,
            args=fs_args,
            env=os.environ.copy(),
        )

        self.connections: Dict[str, ServerConnection] = {
            "ops": ServerConnection("ops", ops_params),
            "fs": ServerConnection("fs", fs_params),
        }

        self.tool_registry: Dict[str, ToolRegistration] = {}
        self.discovered_resources: Dict[str, List[McpResource]] = {}
        self.discovered_templates: Dict[str, List[McpResourceTemplate]] = {}
        self._started = False
        self._hub_lock = asyncio.Lock()

    async def start(self) -> None:
        """Start both server connections and perform dynamic discovery."""
        async with self._hub_lock:
            if self._started:
                return

            # Connect in parallel
            await asyncio.gather(
                self.connections["ops"].connect(),
                self.connections["fs"].connect(),
            )
            self._started = True

            # Run discovery
            await self.discover_all()

    async def close(self) -> None:
        """Close complete MCPHub lifecycle."""
        async with self._hub_lock:
            await asyncio.gather(
                *(conn.close() for conn in self.connections.values()),
                return_exceptions=True,
            )
            self._started = False
            self.tool_registry.clear()

    async def stop(self) -> None:
        """Alias for close()."""
        await self.close()

    def get_connection(self, server_name: str) -> ServerConnection:
        if server_name not in self.connections:
            raise KeyError(f"Unknown server connection: '{server_name}'")
        return self.connections[server_name]

    async def ensure_connection_healthy(self, server_name: str) -> None:
        """
        Check health of target connection before call.
        If suspect or unhealthy, health-check or reconnect only that server.
        Protects connection using its lock; leaves the other server untouched.
        """
        conn = self.get_connection(server_name)
        if conn.health == HealthState.HEALTHY:
            return

        # Attempt ping
        is_healthy = await conn.health_check(timeout=2.0)
        if not is_healthy:
            # Reconnect only this server
            await conn.reconnect()
            # Refresh its discovered capabilities
            await self._discover_server(server_name)

    async def discover_all(self) -> None:
        """Discover tools and resources dynamically from all active servers."""
        self.tool_registry.clear()
        for server_name in self.connections:
            await self._discover_server(server_name)

        # Register unified read_resource tool
        self._register_resource_tool()

    async def _discover_server(self, server_name: str) -> None:
        """Discover capabilities for one server."""
        conn = self.get_connection(server_name)
        tools_res = await conn.list_tools()

        # Filter out existing registrations for this server
        for k in list(self.tool_registry.keys()):
            if self.tool_registry[k].server == server_name:
                del self.tool_registry[k]

        for tool in tools_res.tools:
            # Filesystem policy enforcement: only expose read-only allowlisted tools
            if server_name == "fs" and tool.name not in FS_READ_ONLY_ALLOWLIST:
                continue

            namespaced = f"{server_name}__{tool.name}"

            # Validate name syntax
            if not TOOL_NAME_PATTERN.match(namespaced):
                raise ValueError(f"Namespaced tool name '{namespaced}' violates pattern {TOOL_NAME_PATTERN.pattern}")

            # Collision prevention: namespaced names must never collide
            if namespaced in self.tool_registry:
                raise KeyError(f"Tool namespace collision detected: '{namespaced}' is already registered!")

            # Extract schema & annotations
            raw_schema = getattr(tool, "input_schema", getattr(tool, "inputSchema", {}))
            schema = raw_schema if isinstance(raw_schema, dict) else (raw_schema.model_dump() if hasattr(raw_schema, "model_dump") else dict(raw_schema))
            annotations = getattr(tool, "annotations", None)
            ann_dict = {}
            is_mutating = False
            if annotations:
                ann_dict = annotations if isinstance(annotations, dict) else (annotations.model_dump() if hasattr(annotations, "model_dump") else dict(annotations))
                if ann_dict.get("destructive_hint") is True or ann_dict.get("destructiveHint") is True or ann_dict.get("read_only_hint") is False or ann_dict.get("readOnlyHint") is False:
                    is_mutating = True

            # Ops ticket creation is known mutating state
            if namespaced == "ops__create_incident_ticket":
                is_mutating = True

            self.tool_registry[namespaced] = ToolRegistration(
                namespaced_name=namespaced,
                server=server_name,
                original_name=tool.name,
                description=tool.description or "",
                schema=schema,
                annotations=ann_dict,
                is_mutating=is_mutating,
            )

        # Discover resources
        try:
            res = await conn.list_resources()
            self.discovered_resources[server_name] = res.resources
        except Exception:
            self.discovered_resources[server_name] = []

        # Discover resource templates
        try:
            tpl = await conn.list_resource_templates()
            self.discovered_templates[server_name] = tpl.resource_templates
        except Exception:
            self.discovered_templates[server_name] = []

    def _register_resource_tool(self) -> None:
        """Register the generic read_resource tool with dynamic description."""
        desc_lines = [
            "Reads an MCP context resource by URI.",
            "Use this tool to inspect operational runbooks and release verification criteria.",
            "",
            "Available static resources:",
        ]

        has_resources = False
        for srv, res_list in self.discovered_resources.items():
            for r in res_list:
                has_resources = True
                desc_lines.append(f"- {r.uri}: {r.description or r.name}")

        if not has_resources:
            desc_lines.append("  (None discovered)")

        desc_lines.append("\nAvailable resource URI templates:")
        has_templates = False
        for srv, tpl_list in self.discovered_templates.items():
            for tpl in tpl_list:
                has_templates = True
                desc_lines.append(f"- {tpl.uri_template}: {tpl.description or tpl.name}")

        if not has_templates:
            desc_lines.append("  (None discovered)")

        resource_tool_schema = {
            "type": "object",
            "properties": {
                "uri": {
                    "type": "string",
                    "description": "Exact URI of the resource to read (e.g., 'config://release-checklist' or 'service://runbooks/payments-api')",
                }
            },
            "required": ["uri"],
            "additionalProperties": False,
        }

        self.tool_registry["read_resource"] = ToolRegistration(
            namespaced_name="read_resource",
            server="hub_router",
            original_name="read_resource",
            description="\n".join(desc_lines),
            schema=resource_tool_schema,
            annotations={"readOnlyHint": True},
            is_mutating=False,
        )

    def get_grok_tools(self) -> List[dict]:
        """Return all exposed tools formatted as Grok/OpenAI function definitions."""
        return [reg.to_grok_function() for reg in self.tool_registry.values()]

    def validate_resource_uri(self, uri: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate URI against discovered resources and template patterns.
        Returns (is_valid, server_name, error_message).
        """
        # Check exact static resource match
        for srv, res_list in self.discovered_resources.items():
            for r in res_list:
                if r.uri == uri:
                    return True, srv, None

        # Check template match: service://runbooks/{service_name}
        if uri.startswith("service://runbooks/"):
            service_name = uri.split("service://runbooks/", 1)[1]
            valid_services = {"auth-service", "payments-api", "notification-worker"}
            if service_name in valid_services:
                return True, "ops", None
            return (
                False,
                None,
                f"Unknown service '{service_name}' in runbook URI. Valid services: {sorted(list(valid_services))}",
            )

        return False, None, f"Resource URI '{uri}' does not match any registered resource or valid template pattern."

    async def call_tool(
        self,
        namespaced_name: str,
        arguments: dict,
        timeout: Optional[float] = None,
    ) -> Any:
        """Route tool call to appropriate connection with health check and recovery."""
        if namespaced_name == "read_resource":
            uri = arguments.get("uri", "")
            is_valid, target_server, err_msg = self.validate_resource_uri(uri)
            if not is_valid or not target_server:
                raise ValueError(err_msg or f"Invalid resource URI: '{uri}'")

            await self.ensure_connection_healthy(target_server)
            conn = self.get_connection(target_server)
            return await conn.read_resource(uri, timeout=timeout)

        if namespaced_name not in self.tool_registry:
            raise KeyError(f"Tool '{namespaced_name}' not registered in MCPHub")

        reg = self.tool_registry[namespaced_name]
        target_server = reg.server
        await self.ensure_connection_healthy(target_server)
        conn = self.get_connection(target_server)
        return await conn.call_tool(reg.original_name, arguments, timeout=timeout)
