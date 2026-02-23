"""Transport layer for batching and sending logs to GT8004 ingest API."""

import asyncio
import random
import time
from typing import List, Optional
import httpx

from .types import RequestLogEntry, LogBatch


class BatchTransport:
    """Handles batching and async transport of log entries to GT8004 ingest API."""

    def __init__(
        self,
        ingest_url: str,
        api_key: str,
        agent_id: str,
        batch_size: int = 50,
        flush_interval: float = 5.0,
    ):
        """
        Initialize the batch transport.

        Args:
            ingest_url: URL of the GT8004 ingest API endpoint
            api_key: API key for authentication
            agent_id: Agent ID for this SDK instance
            batch_size: Number of entries before auto-flush (default: 50)
            flush_interval: Seconds between auto-flushes (default: 5.0)
        """
        self.ingest_url = ingest_url
        self.api_key = api_key
        self.agent_id = agent_id
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        self.buffer: List[RequestLogEntry] = []
        self.lock = asyncio.Lock()
        self.client = httpx.AsyncClient(timeout=10.0)
        self.flush_task: Optional[asyncio.Task] = None
        self.consecutive_failures = 0
        self.circuit_breaker_until = 0.0

    async def add(self, entry: RequestLogEntry) -> None:
        """
        Add an entry to the buffer and flush if batch size is reached.

        Args:
            entry: The log entry to add
        """
        async with self.lock:
            self.buffer.append(entry)
            if len(self.buffer) >= self.batch_size:
                await self._flush_internal()

    async def _flush_internal(self) -> None:
        """Internal flush method (already locked)."""
        if not self.buffer:
            return

        # Circuit breaker check
        if time.time() < self.circuit_breaker_until:
            return

        batch = LogBatch(
            agent_id=self.agent_id,
            entries=self.buffer.copy()
        )
        self.buffer.clear()

        # Send with retry and exponential backoff
        for attempt in range(3):
            try:
                response = await self.client.post(
                    self.ingest_url,
                    json=batch.model_dump(by_alias=True, exclude_none=True),
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                response.raise_for_status()
                self.consecutive_failures = 0
                return
            except Exception as e:
                if attempt < 2:
                    # Exponential backoff: 1s, 2s
                    await asyncio.sleep(2 ** attempt)
                else:
                    # All retries failed
                    self.consecutive_failures += 1
                    if self.consecutive_failures >= 5:
                        # Circuit breaker: back off for 30 seconds
                        self.circuit_breaker_until = time.time() + 30
                    # Re-queue failed entries to avoid data loss
                    self.buffer = batch.entries + self.buffer

    async def flush(self) -> None:
        """Flush all pending logs immediately."""
        async with self.lock:
            await self._flush_internal()

    async def close(self) -> None:
        """Close the transport and flush pending logs."""
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()
        await self.client.aclose()

    def start_auto_flush(self) -> None:
        """Start background task for periodic flushing."""
        async def auto_flush():
            while True:
                await asyncio.sleep(self.flush_interval)
                await self.flush()

        self.flush_task = asyncio.create_task(auto_flush())
