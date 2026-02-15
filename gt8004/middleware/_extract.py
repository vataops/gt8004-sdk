"""Common tool name extraction utilities shared across middleware adapters."""

from __future__ import annotations

import json


BODY_LIMIT = 16384  # 16 KB


def extract_mcp_tool_name(body: str | None) -> str | None:
    """Extract tool name from MCP JSON-RPC request body."""
    if not body:
        return None
    try:
        data = json.loads(body)
        if data.get("method") == "tools/call":
            return data.get("params", {}).get("name")
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass
    return None


def extract_a2a_tool_name(body: str | None, path: str) -> str | None:
    """Extract skill/tool name from A2A request body or path."""
    if body:
        try:
            data = json.loads(body)
            skill = data.get("skill_id")
            if skill:
                return skill
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass
    # Fallback: last path segment
    segments = path.rstrip("/").split("/")
    return segments[-1] if segments else None


def extract_http_tool_name(path: str) -> str | None:
    """Extract tool name from HTTP path (last meaningful segment)."""
    segments = path.rstrip("/").split("/")
    return segments[-1] if segments else None


def extract_tool_name(protocol: str | None, body: str | None, path: str) -> str | None:
    """Extract tool name based on protocol type."""
    if protocol == "mcp":
        return extract_mcp_tool_name(body)
    elif protocol == "a2a":
        return extract_a2a_tool_name(body, path)
    else:
        return extract_http_tool_name(path)
