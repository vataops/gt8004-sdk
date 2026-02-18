"""FastAPI/ASGI middleware for GT8004 request logging.

Works with FastAPI, Starlette, and any ASGI-compatible framework.
"""

import time
import uuid
from typing import TYPE_CHECKING
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

if TYPE_CHECKING:
    from ..logger import GT8004Logger

from ..types import RequestLogEntry
from ._extract import BODY_LIMIT, extract_tool_name, extract_x402_payment


_DEFAULT_EXCLUDE_PATHS: set[str] = {
    "/.well-known/agent.json",
    "/.well-known/agent.json/health",
    "/healthz",
    "/readyz",
    "/health",
    "/_health",
}


class GT8004Middleware(BaseHTTPMiddleware):
    """
    ASGI middleware that automatically logs requests to GT8004.

    Works with FastAPI, Starlette, and any ASGI framework.

    Usage:
        from fastapi import FastAPI
        from gt8004 import GT8004Logger
        from gt8004.middleware.fastapi import GT8004Middleware

        logger = GT8004Logger(agent_id="...", api_key="...", protocol="a2a")
        logger.transport.start_auto_flush()

        app = FastAPI()
        app.add_middleware(GT8004Middleware, logger=logger)
    """

    def __init__(self, app, logger: "GT8004Logger", exclude_paths: set[str] | None = None):
        super().__init__(app)
        self.logger = logger
        self.exclude_paths = exclude_paths if exclude_paths is not None else _DEFAULT_EXCLUDE_PATHS

    async def dispatch(self, request: Request, call_next):
        # Skip logging for excluded paths (health checks, etc.)
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        start_time = time.time()
        request_id = str(uuid.uuid4())

        # Capture request body
        request_body = None
        request_body_size = 0
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body_bytes = await request.body()
                request_body_size = len(body_bytes)
                if request_body_size <= BODY_LIMIT:
                    request_body = body_bytes.decode("utf-8", errors="ignore")
            except Exception:
                pass

        # Process request
        response = await call_next(request)

        # Capture response body by reading the streaming response
        response_body = None
        response_body_size = 0
        try:
            body_chunks: list[bytes] = []
            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                body_chunks.append(chunk)
            raw = b"".join(body_chunks)
            response_body_size = len(raw)
            if response_body_size <= BODY_LIMIT:
                response_body = raw.decode("utf-8", errors="ignore")
            # Re-create response with the consumed body
            response = Response(
                content=raw,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        except Exception:
            pass

        # Calculate response time
        response_time = (time.time() - start_time) * 1000  # ms

        # Protocol-specific tool name extraction
        protocol = self.logger.protocol
        path = str(request.url.path)
        tool_name = extract_tool_name(protocol, request_body, path)

        # Create log entry
        raw_headers = {
            "user-agent": request.headers.get("user-agent"),
            "content-type": request.headers.get("content-type"),
            "referer": request.headers.get("referer"),
        }
        headers = {k: v for k, v in raw_headers.items() if v is not None}

        # Extract x402 payment info from X-Payment header
        x402 = extract_x402_payment(request.headers.get("x-payment"))

        entry = RequestLogEntry(
            request_id=request_id,
            method=request.method,
            path=path,
            status_code=response.status_code,
            response_ms=response_time,
            tool_name=tool_name,
            protocol=protocol,
            request_body=request_body,
            request_body_size=request_body_size,
            response_body=response_body,
            response_body_size=response_body_size,
            headers=headers if headers else None,
            ip_address=request.client.host if request.client else None,
            timestamp=datetime.utcnow().isoformat() + "Z",
            x402_amount=x402["x402_amount"],
            x402_tx_hash=x402["x402_tx_hash"],
            x402_token=x402["x402_token"],
            x402_payer=x402["x402_payer"],
        )

        # Log asynchronously
        await self.logger.log(entry)

        return response
