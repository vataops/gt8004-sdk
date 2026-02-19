"""Common tool name extraction utilities shared across middleware adapters."""

from __future__ import annotations

import base64
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


def extract_x402_payment(
    payment_request: str | None,
    payment_response: str | None,
) -> dict:
    """Extract x402 payment fields from X-Payment and X-Payment-Response headers.

    The X-Payment request header is base64-encoded JSON containing the signed
    payment proof with the authorization (amount, payer).

    The X-Payment-Response response header is base64-encoded JSON containing
    the settlement result (success, transaction hash, payer).

    Returns a dict with keys x402_amount, x402_tx_hash, x402_token, x402_payer.
    All values default to None if the headers are missing or malformed.
    """
    result: dict = {
        "x402_amount": None,
        "x402_tx_hash": None,
        "x402_token": None,
        "x402_payer": None,
    }

    # Parse X-Payment-Response (base64 JSON) for settlement info
    if payment_response:
        try:
            resp = json.loads(base64.b64decode(payment_response))
            if resp.get("success"):
                if resp.get("transaction"):
                    result["x402_tx_hash"] = str(resp["transaction"])
                if resp.get("payer"):
                    result["x402_payer"] = str(resp["payer"])
                if resp.get("network"):
                    result["x402_token"] = f"USDC-{resp['network']}"
        except (json.JSONDecodeError, TypeError, ValueError, Exception):
            pass

    # Parse X-Payment request header (base64 JSON) for amount
    if payment_request:
        try:
            req = json.loads(base64.b64decode(payment_request))
            payload = req.get("payload", {})
            auth = payload.get("authorization", {})
            value = auth.get("value")
            if value is not None:
                # USDC has 6 decimals; value is in smallest unit
                result["x402_amount"] = int(value) / 1_000_000
        except (json.JSONDecodeError, TypeError, ValueError, Exception):
            pass

    return result
