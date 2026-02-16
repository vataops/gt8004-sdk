"""Main GT8004 logger class."""

from __future__ import annotations

import logging

from .transport import BatchTransport
from .types import RequestLogEntry

_log = logging.getLogger("gt8004")


class GT8004Logger:
    """
    Main logger class for GT8004 SDK.

    Usage:
        logger = GT8004Logger(
            agent_id="your-agent-id",
            api_key="your-api-key"
        )
        logger.transport.start_auto_flush()

        # Verify connection on startup
        ok = await logger.verify_connection()

        # In FastAPI middleware
        await logger.log(entry)

        # On shutdown
        await logger.close()
    """

    VALID_PROTOCOLS = ("mcp", "a2a")

    _INGEST_URLS = {
        "mainnet": "https://ingest.gt8004.xyz/v1/ingest",
        "testnet": "https://testnet.ingest.gt8004.xyz/v1/ingest",
    }

    def __init__(
        self,
        agent_id: str,
        api_key: str,
        ingest_url: str | None = None,
        network: str = "mainnet",
        batch_size: int = 50,
        flush_interval: float = 5.0,
        protocol: str | None = None,
    ):
        """
        Initialize the GT8004 logger.

        Args:
            agent_id: Your GT8004 agent ID
            api_key: Your GT8004 API key
            ingest_url: Custom ingest endpoint (overrides network selection)
            network: "mainnet" (default) or "testnet"
            batch_size: Number of entries before auto-flush (default: 50)
            flush_interval: Seconds between auto-flushes (default: 5.0)
            protocol: Protocol type - "mcp" or "a2a" (default: None for plain HTTP)
        """
        if network not in self._INGEST_URLS:
            raise ValueError(f"network must be 'mainnet' or 'testnet', got '{network}'")
        if ingest_url is None:
            ingest_url = self._INGEST_URLS[network]
        if protocol is not None and protocol not in self.VALID_PROTOCOLS:
            raise ValueError(f"protocol must be one of {self.VALID_PROTOCOLS}, got '{protocol}'")
        self.agent_id = agent_id
        self.api_key = api_key
        self.protocol = protocol
        self.transport = BatchTransport(
            ingest_url=ingest_url,
            api_key=api_key,
            agent_id=agent_id,
            batch_size=batch_size,
            flush_interval=flush_interval,
        )

    async def verify_connection(self) -> bool:
        """
        Send a startup ping to the ingest endpoint to verify connectivity.

        Sends a single synthetic log entry with source="sdk_ping" so the
        platform can confirm this agent is connected.

        Returns:
            True if the ingest endpoint accepted the ping, False otherwise.
        """
        from datetime import datetime

        entry = RequestLogEntry(
            request_id="startup-ping",
            method="PING",
            path="/_sdk/startup",
            status_code=0,
            response_ms=0,
            source="sdk_ping",
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        try:
            await self.transport.add(entry)
            await self.transport.flush()
            _log.info("GT8004 SDK: startup ping sent to %s", self.transport.ingest_url)
            return True
        except Exception as e:
            _log.warning("GT8004 SDK: startup ping failed: %s", e)
            return False

    async def log(self, entry: RequestLogEntry) -> None:
        """
        Add a log entry to the batch queue.

        Automatically sets the protocol field if not already set.

        Args:
            entry: The RequestLogEntry to log
        """
        if not entry.protocol:
            entry.protocol = self.protocol
        await self.transport.add(entry)

    async def flush(self) -> None:
        """Flush all pending logs immediately."""
        await self.transport.flush()

    async def close(self) -> None:
        """Close the logger and flush pending logs."""
        await self.transport.close()
