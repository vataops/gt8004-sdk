"""Tests for tool name extraction utilities."""

import base64
import json
import pytest

from gt8004.middleware._extract import (
    BODY_LIMIT,
    extract_mcp_tool_name,
    extract_a2a_tool_name,
    extract_http_tool_name,
    extract_tool_name,
    extract_x402_payment,
)


class TestExtractMCPToolName:
    def test_valid_tools_call(self):
        body = json.dumps({"method": "tools/call", "params": {"name": "search"}})
        assert extract_mcp_tool_name(body) == "search"

    def test_different_method(self):
        body = json.dumps({"method": "resources/list", "params": {"name": "foo"}})
        assert extract_mcp_tool_name(body) is None

    def test_missing_params(self):
        body = json.dumps({"method": "tools/call"})
        assert extract_mcp_tool_name(body) is None

    def test_none_body(self):
        assert extract_mcp_tool_name(None) is None

    def test_empty_body(self):
        assert extract_mcp_tool_name("") is None

    def test_invalid_json(self):
        assert extract_mcp_tool_name("not json") is None

    def test_non_dict_json(self):
        assert extract_mcp_tool_name("[1, 2, 3]") is None


class TestExtractA2AToolName:
    def test_skill_id_from_body(self):
        body = json.dumps({"skill_id": "translate", "input": "hello"})
        assert extract_a2a_tool_name(body, "/a2a/tasks") == "translate"

    def test_fallback_to_path(self):
        assert extract_a2a_tool_name(None, "/a2a/tasks/send") == "send"

    def test_fallback_to_path_with_trailing_slash(self):
        assert extract_a2a_tool_name(None, "/a2a/tasks/send/") == "send"

    def test_body_without_skill_id(self):
        body = json.dumps({"input": "hello"})
        assert extract_a2a_tool_name(body, "/a2a/run") == "run"

    def test_invalid_json_fallback_to_path(self):
        assert extract_a2a_tool_name("bad json", "/api/search") == "search"

    def test_empty_body_fallback(self):
        assert extract_a2a_tool_name("", "/tasks") == "tasks"


class TestExtractHTTPToolName:
    def test_simple_path(self):
        assert extract_http_tool_name("/api/search") == "search"

    def test_trailing_slash(self):
        assert extract_http_tool_name("/api/search/") == "search"

    def test_root_path(self):
        assert extract_http_tool_name("/") == ""

    def test_deep_path(self):
        assert extract_http_tool_name("/v1/api/tools/generate") == "generate"


class TestExtractToolName:
    def test_mcp_protocol(self):
        body = json.dumps({"method": "tools/call", "params": {"name": "search"}})
        assert extract_tool_name("mcp", body, "/mcp") == "search"

    def test_a2a_protocol(self):
        body = json.dumps({"skill_id": "translate"})
        assert extract_tool_name("a2a", body, "/a2a") == "translate"

    def test_none_protocol_uses_http(self):
        assert extract_tool_name(None, None, "/api/search") == "search"

    def test_unknown_protocol_uses_http(self):
        assert extract_tool_name("other", None, "/api/search") == "search"


def _b64(data: dict) -> str:
    """Base64-encode a JSON dict for x402 header tests."""
    return base64.b64encode(json.dumps(data).encode()).decode()


class TestExtractX402Payment:
    def test_none_headers(self):
        result = extract_x402_payment(None, None)
        assert result["x402_amount"] is None
        assert result["x402_tx_hash"] is None
        assert result["x402_token"] is None
        assert result["x402_payer"] is None

    def test_empty_headers(self):
        result = extract_x402_payment("", "")
        assert result["x402_amount"] is None

    def test_valid_payment(self):
        req = _b64({"payload": {"authorization": {"value": 500000}}})
        resp = _b64({
            "success": True,
            "transaction": "0xabc123",
            "payer": "0xdef456",
            "network": "base-mainnet",
        })
        result = extract_x402_payment(req, resp)
        assert result["x402_amount"] == 0.5
        assert result["x402_tx_hash"] == "0xabc123"
        assert result["x402_token"] == "USDC-base-mainnet"
        assert result["x402_payer"] == "0xdef456"

    def test_amount_from_request_header(self):
        req = _b64({"payload": {"authorization": {"value": 1250000}}})
        result = extract_x402_payment(req, None)
        assert result["x402_amount"] == 1.25

    def test_malformed_base64(self):
        result = extract_x402_payment("not-base64!", "not-base64!")
        assert result["x402_amount"] is None
        assert result["x402_tx_hash"] is None

    def test_response_only(self):
        resp = _b64({
            "success": True,
            "transaction": "0xtx",
            "payer": "0xpayer",
            "network": "base-sepolia",
        })
        result = extract_x402_payment(None, resp)
        assert result["x402_amount"] is None
        assert result["x402_tx_hash"] == "0xtx"
        assert result["x402_payer"] == "0xpayer"
        assert result["x402_token"] == "USDC-base-sepolia"

    def test_zero_amount(self):
        req = _b64({"payload": {"authorization": {"value": 0}}})
        resp = _b64({"success": True, "transaction": "0x0", "payer": "0x0", "network": "base-mainnet"})
        result = extract_x402_payment(req, resp)
        assert result["x402_amount"] == 0.0


class TestBodyLimit:
    def test_body_limit_is_16kb(self):
        assert BODY_LIMIT == 16384
