"""
EventFlow_AI/mcp_client.py
---------------------------
Manages the persistent async connection to the Solace MCP Server
via the stdio transport. Also contains the Schema Pruner and Compact
Tool generator to prevent LLM context-window overflow.
"""

import os
import json
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from . import config


# ── Schema Pruner ─────────────────────────────────────────────────────────
# Solace OpenAPI schemas are extremely verbose. Stripping these keys prevents
# the local LLM's context window from being overwhelmed.
_PRUNE_KEYS = {
    "description", "example", "examples", "readOnly",
    "default", "pattern", "format", "deprecated",
    "x-" # catches all vendor extension keys
}

def _prune_schema(obj: Any) -> Any:
    """Recursively prune bloated metadata from a JSON schema object."""
    if isinstance(obj, dict):
        return {
            k: _prune_schema(v)
            for k, v in obj.items()
            if k not in _PRUNE_KEYS and not k.startswith("x-")
        }
    if isinstance(obj, list):
        return [_prune_schema(item) for item in obj]
    return obj


def prune_tool(tool: dict) -> dict:
    """Return a copy of an MCP tool dict with the schema stripped down."""
    pruned = dict(tool)
    if "inputSchema" in pruned and pruned["inputSchema"]:
        pruned["inputSchema"] = _prune_schema(pruned["inputSchema"])
    return pruned


def to_compact_tools(tools: list[dict]) -> list[dict]:
    """
    Generate ultra-lightweight tool descriptors for Round 0 Tool Discovery.
    Only includes 'name' and a single-sentence description to keep the
    initial prompt payload under ~5KB.
    """
    compact = []
    for t in tools:
        desc = t.get("description", "")
        # Take first sentence only
        short = desc.split(".")[0].strip() if desc else "(no description)"
        compact.append({"name": t["name"], "description": short})
    return compact


# ── MCP Server Parameters ─────────────────────────────────────────────────
def _get_server_params() -> StdioServerParameters:
    env = {
        **os.environ,
        "SOLACE_API_TOKEN": config.SOLACE_API_TOKEN,
        "SOLACE_API_BASE_URL": config.SOLACE_API_BASE_URL,
    }
    return StdioServerParameters(
        command="uvx",
        args=["--from", "solace-event-portal-designer-mcp", "solace-ep-designer-mcp"],
        env=env,
    )


# ── Context Manager ────────────────────────────────────────────────────────
@asynccontextmanager
async def managed_session():
    """
    Async context manager that yields a fully initialized MCP ClientSession.

    Usage:
        async with managed_session() as session:
            tools = await session.list_tools()
    """
    async with stdio_client(_get_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


# ── Tool Helpers ───────────────────────────────────────────────────────────
async def fetch_all_tools(session: ClientSession) -> list[dict]:
    """Fetch all tools from the MCP server and return as plain dicts."""
    result = await session.list_tools()
    return [
        {
            "name": t.name,
            "description": t.description or "",
            "inputSchema": t.inputSchema if hasattr(t, "inputSchema") else {},
        }
        for t in result.tools
    ]


async def execute_tool(session: ClientSession, name: str, args: dict) -> str:
    """
    Execute a named MCP tool with the given arguments.
    Returns the raw text content of the response as a JSON string.
    """
    result = await session.call_tool(name, args)
    parts = []
    for content in result.content:
        if content.type == "text":
            parts.append(content.text)
    return "\n".join(parts) if parts else "{}"
