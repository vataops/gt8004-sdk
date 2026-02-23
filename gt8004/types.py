"""Type definitions for GT8004 SDK."""

from typing import Optional, List, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class RequestLogEntry(BaseModel):
    """A single request log entry to be sent to GT8004 analytics."""

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    request_id: str
    method: str
    path: str
    status_code: int
    response_ms: float

    # Optional analytics fields
    customer_id: Optional[str] = None
    tool_name: Optional[str] = None
    error_type: Optional[str] = None

    # X-402 payment protocol fields
    x402_amount: Optional[float] = None
    x402_tx_hash: Optional[str] = None
    x402_token: Optional[str] = None
    x402_payer: Optional[str] = None

    # Request/response body (limited size)
    request_body: Optional[str] = None
    response_body: Optional[str] = None
    request_body_size: Optional[int] = None
    response_body_size: Optional[int] = None

    # Request metadata
    headers: Optional[Dict[str, str]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    referer: Optional[str] = None
    content_type: Optional[str] = None
    accept_language: Optional[str] = None
    protocol: Optional[str] = Field(None, pattern=r"^(mcp|a2a)$")

    # Source identifier
    source: str = "sdk"

    # Timestamp (ISO 8601 format with 'Z' suffix)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))


class LogBatch(BaseModel):
    """A batch of log entries to send to the ingest API."""

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    agent_id: str
    sdk_version: str = "python-0.2.0"
    entries: List[RequestLogEntry]
