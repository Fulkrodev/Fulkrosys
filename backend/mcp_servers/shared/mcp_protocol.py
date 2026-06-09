"""MCP Server base — JSON-RPC 2.0 over stdio.

Each MCP server inherits from MCPServer and registers its tools.
Protocol: https://modelcontextprotocol.io/specification
"""
import asyncio
import hashlib
import json
import sys
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Callable, Optional


class MCPTool:
    """MCP tool definition with JSON-schema and metadata."""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict,
        requires_approval: bool = False,
        timeout_seconds: int = 600,
        risk_level: str = "low",
        ens_measures: Optional[list[str]] = None,
    ):
        self.name = name
        self.description = description
        self.input_schema = {"type": "object", **input_schema}
        self.requires_approval = requires_approval
        self.timeout_seconds = timeout_seconds
        self.risk_level = risk_level
        self.ens_measures = ens_measures or []


class MCPServer(ABC):
    """Base MCP server: reads JSON-RPC from stdin, executes tools, writes to stdout."""

    SERVER_NAME: str = "base"
    SERVER_VERSION: str = "1.0.0"

    def __init__(self):
        self.tools: dict[str, MCPTool] = {}
        self._handlers: dict[str, Callable] = {}
        self._register_tools()

    @abstractmethod
    def _register_tools(self):
        """Each server overrides this to register its tools."""

    def register_tool(self, tool: MCPTool, handler: Callable):
        self.tools[tool.name] = tool
        self._handlers[tool.name] = handler

    async def run(self):
        """Main loop: stdin -> dispatch -> stdout."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = await self._dispatch(request)
            except json.JSONDecodeError:
                response = self._error(None, -32700, "Parse error")
            except Exception as exc:
                response = self._error(None, -32603, f"Internal error: {exc}")
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

    async def _dispatch(self, request: dict) -> dict:
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            return self._ok(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": self.SERVER_NAME,
                    "version": self.SERVER_VERSION,
                },
            })
        if method == "tools/list":
            return self._ok(req_id, {
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.input_schema,
                    }
                    for t in self.tools.values()
                ]
            })
        if method == "tools/call":
            return await self._handle_tool_call(req_id, params)
        if method == "notifications/initialized":
            return self._ok(req_id, {})
        return self._error(req_id, -32601, f"Unknown method: {method}")

    async def _handle_tool_call(self, req_id, params: dict) -> dict:
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return self._error(
                req_id, -32602,
                f"Tool '{tool_name}' not found. Available: {list(self.tools.keys())}",
            )

        tool = self.tools[tool_name]
        handler = self._handlers[tool_name]
        start_time = datetime.now(timezone.utc)

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(**arguments), timeout=tool.timeout_seconds
                )
            else:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: handler(**arguments)),
                    timeout=tool.timeout_seconds,
                )
            result_json = json.dumps(result, default=str, ensure_ascii=False, sort_keys=True)
            output_hash = hashlib.sha256(result_json.encode()).hexdigest()
            elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            return self._ok(req_id, {
                "content": [{"type": "text", "text": result_json}],
                "meta": {
                    "tool": tool_name,
                    "output_hash": output_hash,
                    "timestamp": start_time.isoformat(),
                    "elapsed_ms": elapsed_ms,
                    "risk_level": tool.risk_level,
                    "requires_approval": tool.requires_approval,
                    "ens_measures": tool.ens_measures,
                },
            })
        except asyncio.TimeoutError:
            return self._error(
                req_id, -32000,
                f"Tool '{tool_name}' timed out after {tool.timeout_seconds}s",
            )
        except Exception as exc:
            return self._error(
                req_id, -32000,
                f"Tool '{tool_name}' failed: {exc}\n{traceback.format_exc()}",
            )

    def _ok(self, req_id, result) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _error(self, req_id, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
