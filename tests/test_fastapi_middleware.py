"""Tests for FastAPI/ASGI middleware."""

import base64
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from gt8004.middleware.fastapi import GT8004Middleware
from gt8004.types import RequestLogEntry


def _make_logger(protocol=None):
    """Create a mock GT8004Logger with async log method."""
    logger = MagicMock()
    logger.protocol = protocol
    logger.log = AsyncMock()
    return logger


def _make_app(logger):
    """Create a FastAPI app with GT8004 middleware."""
    app = FastAPI()
    app.add_middleware(GT8004Middleware, logger=logger)

    @app.get("/api/search")
    async def search():
        return {"results": []}

    @app.post("/a2a/tasks")
    async def tasks(body: dict = None):
        return {"status": "ok"}

    @app.get("/health")
    async def health():
        return {"ok": True}

    return app


class TestFastAPIMiddlewareBasic:
    def test_passes_through_request(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_excludes_health_from_logging(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        client.get("/health")
        logger.log.assert_not_called()

    def test_logs_get_request(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        client.get("/api/search")

        logger.log.assert_called_once()
        entry = logger.log.call_args[0][0]
        assert isinstance(entry, RequestLogEntry)
        assert entry.method == "GET"
        assert entry.path == "/api/search"
        assert entry.status_code == 200
        assert entry.response_ms > 0

    def test_logs_post_request(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        client.post("/a2a/tasks", json={"skill_id": "translate"})

        logger.log.assert_called_once()
        entry = logger.log.call_args[0][0]
        assert entry.method == "POST"
        assert entry.path == "/a2a/tasks"
        assert entry.request_body is not None


class TestFastAPIMiddlewareProtocol:
    def test_a2a_extracts_skill_id(self):
        logger = _make_logger(protocol="a2a")
        app = _make_app(logger)
        client = TestClient(app)

        client.post("/a2a/tasks", json={"skill_id": "translate"})

        entry = logger.log.call_args[0][0]
        assert entry.tool_name == "translate"

    def test_http_extracts_path_segment(self):
        logger = _make_logger(protocol=None)
        app = _make_app(logger)
        client = TestClient(app)

        client.get("/api/search")

        entry = logger.log.call_args[0][0]
        assert entry.tool_name == "search"

    def test_mcp_extracts_tool_name(self):
        logger = _make_logger(protocol="mcp")
        app = FastAPI()
        app.add_middleware(GT8004Middleware, logger=logger)

        @app.post("/mcp")
        async def mcp_endpoint():
            return {"result": "ok"}

        client = TestClient(app)
        mcp_body = {"method": "tools/call", "params": {"name": "search"}}
        client.post("/mcp", json=mcp_body)

        entry = logger.log.call_args[0][0]
        assert entry.tool_name == "search"


class TestFastAPIMiddlewareMetadata:
    def test_captures_request_id(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        client.get("/api/search")

        entry = logger.log.call_args[0][0]
        assert entry.request_id is not None
        assert len(entry.request_id) == 36  # UUID format

    def test_captures_timestamp(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        client.get("/api/search")

        entry = logger.log.call_args[0][0]
        assert entry.timestamp.endswith("Z")

    def test_captures_response_body(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        client.get("/api/search")

        entry = logger.log.call_args[0][0]
        assert entry.response_body is not None
        assert "results" in entry.response_body


def _b64(data: dict) -> str:
    """Base64-encode a JSON dict for x402 header tests."""
    return base64.b64encode(json.dumps(data).encode()).decode()


def _make_x402_app(logger, payment_response_header=None):
    """Create a FastAPI app that returns x-payment-response header."""
    app = FastAPI()
    app.add_middleware(GT8004Middleware, logger=logger)

    @app.get("/api/search")
    async def search():
        headers = {}
        if payment_response_header:
            headers["x-payment-response"] = payment_response_header
        return JSONResponse(content={"results": []}, headers=headers)

    return app


class TestFastAPIMiddlewareX402:
    def test_extracts_x402_payment(self):
        logger = _make_logger()
        req_header = _b64({"payload": {"authorization": {"value": 750000}}})
        resp_header = _b64({
            "success": True,
            "transaction": "0xabc123def456",
            "payer": "0x1234567890abcdef",
            "network": "base-mainnet",
        })
        app = _make_x402_app(logger, payment_response_header=resp_header)
        client = TestClient(app)

        client.get("/api/search", headers={"X-Payment": req_header})

        entry = logger.log.call_args[0][0]
        assert entry.x402_amount == 0.75
        assert entry.x402_tx_hash == "0xabc123def456"
        assert entry.x402_token == "USDC-base-mainnet"
        assert entry.x402_payer == "0x1234567890abcdef"

    def test_no_x402_header_leaves_fields_none(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        client.get("/api/search")

        entry = logger.log.call_args[0][0]
        assert entry.x402_amount is None
        assert entry.x402_tx_hash is None

    def test_malformed_x402_header_is_ignored(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        client.get("/api/search", headers={"X-Payment": "not-valid-base64"})

        entry = logger.log.call_args[0][0]
        assert entry.x402_amount is None
        assert entry.x402_tx_hash is None

    def test_x402_serializes_as_camel_case(self):
        logger = _make_logger()
        req_header = _b64({"payload": {"authorization": {"value": 1500000}}})
        resp_header = _b64({
            "success": True,
            "transaction": "0xaaa",
            "payer": "0xbbb",
            "network": "base-mainnet",
        })
        app = _make_x402_app(logger, payment_response_header=resp_header)
        client = TestClient(app)

        client.get("/api/search", headers={"X-Payment": req_header})

        entry = logger.log.call_args[0][0]
        data = entry.model_dump(by_alias=True, exclude_none=True)
        assert data["x402Amount"] == 1.5
        assert data["x402TxHash"] == "0xaaa"
        assert data["x402Token"] == "USDC-base-mainnet"
        assert data["x402Payer"] == "0xbbb"
