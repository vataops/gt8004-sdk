"""Tests for GT8004Logger."""

import pytest
import pytest_asyncio

from gt8004.logger import GT8004Logger
from gt8004.types import RequestLogEntry


class TestLoggerInit:
    def test_default_init(self):
        logger = GT8004Logger(agent_id="test-agent", api_key="test-key")
        assert logger.agent_id == "test-agent"
        assert logger.api_key == "test-key"
        assert logger.protocol is None
        assert logger.transport.ingest_url == "https://ingest.gt8004.xyz/v1/ingest"

    def test_mcp_protocol(self):
        logger = GT8004Logger(agent_id="a", api_key="k", protocol="mcp")
        assert logger.protocol == "mcp"

    def test_a2a_protocol(self):
        logger = GT8004Logger(agent_id="a", api_key="k", protocol="a2a")
        assert logger.protocol == "a2a"

    def test_invalid_protocol_raises(self):
        with pytest.raises(ValueError, match="protocol must be one of"):
            GT8004Logger(agent_id="a", api_key="k", protocol="http")

    def test_invalid_protocol_random(self):
        with pytest.raises(ValueError):
            GT8004Logger(agent_id="a", api_key="k", protocol="grpc")

    def test_testnet_network(self):
        logger = GT8004Logger(agent_id="a", api_key="k", network="testnet")
        assert logger.transport.ingest_url == "https://testnet.ingest.gt8004.xyz/v1/ingest"

    def test_invalid_network_raises(self):
        with pytest.raises(ValueError, match="network must be"):
            GT8004Logger(agent_id="a", api_key="k", network="devnet")

    def test_custom_ingest_url_overrides_network(self):
        logger = GT8004Logger(
            agent_id="a", api_key="k",
            ingest_url="http://localhost:9092/v1/ingest",
            network="testnet",
        )
        assert logger.transport.ingest_url == "http://localhost:9092/v1/ingest"

    def test_custom_batch_settings(self):
        logger = GT8004Logger(
            agent_id="a", api_key="k",
            batch_size=100, flush_interval=10.0
        )
        assert logger.transport.batch_size == 100
        assert logger.transport.flush_interval == 10.0


class TestLoggerLog:
    @pytest.mark.asyncio
    async def test_log_sets_protocol(self):
        logger = GT8004Logger(agent_id="a", api_key="k", protocol="mcp")
        entry = RequestLogEntry(
            request_id="r1", method="POST", path="/test",
            status_code=200, response_ms=10.0,
        )
        assert entry.protocol is None
        await logger.log(entry)
        assert entry.protocol == "mcp"
        # Clean up buffer
        logger.transport.buffer.clear()

    @pytest.mark.asyncio
    async def test_log_preserves_existing_protocol(self):
        logger = GT8004Logger(agent_id="a", api_key="k", protocol="mcp")
        entry = RequestLogEntry(
            request_id="r1", method="POST", path="/test",
            status_code=200, response_ms=10.0, protocol="a2a",
        )
        await logger.log(entry)
        assert entry.protocol == "a2a"
        logger.transport.buffer.clear()

    @pytest.mark.asyncio
    async def test_log_adds_to_buffer(self):
        logger = GT8004Logger(agent_id="a", api_key="k")
        entry = RequestLogEntry(
            request_id="r1", method="GET", path="/test",
            status_code=200, response_ms=5.0,
        )
        await logger.log(entry)
        assert len(logger.transport.buffer) == 1
        assert logger.transport.buffer[0] is entry
        logger.transport.buffer.clear()
