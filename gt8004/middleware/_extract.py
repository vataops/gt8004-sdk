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


def extract_x402_payment(header_value: str | None) -> dict:
    """Extract x402 payment fields from the X-Payment header JSON.

    Returns a dict with keys x402_amount, x402_tx_hash, x402_token, x402_payer.
    All values default to None if the header is missing or malformed.
    """
    result: dict = {
        "x402_amount": None,
        "x402_tx_hash": None,
        "x402_token": None,
        "x402_payer": None,
    }
    if not header_value:
        return result
    try:
        payment = json.loads(header_value)
        amount = payment.get("amount")
        if amount is not None:
            result["x402_amount"] = float(amount)
        if payment.get("tx_hash"):
            result["x402_tx_hash"] = str(payment["tx_hash"])
        if payment.get("token"):
            result["x402_token"] = str(payment["token"])
        if payment.get("payer"):
            result["x402_payer"] = str(payment["payer"])
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
        pass
    return result
