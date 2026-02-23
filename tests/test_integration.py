"""Integration tests for GT8004 SDK.

These tests make REAL HTTP calls to the GT8004 ingest endpoint.
They are skipped automatically when credentials are not set.

To run locally:
    GT8004_AGENT_ID=your-id GT8004_API_KEY=your-key pytest tests/test_integration.py -v -s
"""

import os
import pytest
from gt8004 import GT8004Logger
from gt8004.types import RequestLogEntry

_AGENT_ID = os.getenv("GT8004_AGENT_ID")
_API_KEY = os.getenv("GT8004_API_KEY")

pytestmark = pytest.mark.skipif(
    not _AGENT_ID or not _API_KEY,
    reason="Integration tests require GT8004_AGENT_ID and GT8004_API_KEY env vars",
)


async def _make_logger(**kwargs) -> GT8004Logger:
    logger = GT8004Logger(
        agent_id=_AGENT_ID,
        api_key=_API_KEY,
        **kwargs,
    )
    return logger


@pytest.mark.asyncio
async def test_verify_connection():
    """verify_connection() sends a startup ping and returns True."""
    logger = await _make_logger()
    result = await logger.verify_connection()
    assert result is True
    await logger.close()


@pytest.mark.asyncio
async def test_log_basic_entry():
    """A basic RequestLogEntry can be flushed without error."""
    logger = await _make_logger()
    entry = RequestLogEntry(
        request_id="integ-basic-001",
        method="GET",
        path="/api/test",
        status_code=200,
        response_ms=42.0,
    )
    await logger.log(entry)
    await logger.flush()
    await logger.close()


@pytest.mark.asyncio
async def test_log_mcp_protocol():
    """MCP protocol entries with tool_name are flushed successfully."""
    logger = await _make_logger(protocol="mcp")
    entry = RequestLogEntry(
        request_id="integ-mcp-001",
        method="tools/call",
        path="/mcp/tools/search",
        status_code=200,
        response_ms=123.5,
        tool_name="search",
        protocol="mcp",
    )
    await logger.log(entry)
    await logger.flush()
    await logger.close()


@pytest.mark.asyncio
async def test_log_a2a_with_x402():
    """A2A protocol entry with x402 payment fields is flushed successfully."""
    logger = await _make_logger(protocol="a2a")
    entry = RequestLogEntry(
        request_id="integ-a2a-x402-001",
        method="POST",
        path="/api/agent/translate",
        status_code=200,
        response_ms=250.0,
        tool_name="translate",
        protocol="a2a",
        x402_amount=0.01,
        x402_tx_hash="0xabc123def456",
        x402_token="USDC-base-mainnet",
        x402_payer="0xdeadbeef",
    )
    await logger.log(entry)
    await logger.flush()
    await logger.close()


@pytest.mark.asyncio
async def test_testnet_endpoint():
    """Logs can be sent to the testnet ingest endpoint."""
    logger = await _make_logger(network="testnet")
    entry = RequestLogEntry(
        request_id="integ-testnet-001",
        method="POST",
        path="/api/test",
        status_code=201,
        response_ms=88.0,
    )
    await logger.log(entry)
    await logger.flush()
    await logger.close()
