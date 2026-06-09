"""Thin wrapper for the common tool handler skeleton used across servers.

Each concrete tool imports MCPTool from shared.mcp_protocol directly.
This module is kept for import compatibility with the spec tree.
"""
from shared.mcp_protocol import MCPTool  # noqa: F401
