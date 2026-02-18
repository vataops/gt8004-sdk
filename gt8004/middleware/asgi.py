"""Pure ASGI middleware for GT8004 request logging.

Unlike GT8004Middleware (Starlette BaseHTTPMiddleware), this operates at the
raw ASGI level and can be applied as the **outermost** wrapper around any ASGI
app.  This is critical when an outer ASGI middleware (e.g. x402 payment
middleware) may short-circuit responses (402) before they reach inner
Starlette/FastAPI middleware.

Usage:
    from gt8004 import GT8004Logger
    from gt8004.middleware.asgi import GT8004ASGIMiddleware

    logger = GT8004Logger(agent_id="...", api_key="...", protocol="mcp")

    # Apply x402 first, then GT8004 outermost
    app = MCPPaymentMiddleware(app, ...)
    app = GT8004ASGIMiddleware(app, logger)
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from starlette.types import ASGIApp, Receive, Scope, Send

from ..types import RequestLogEntry
from ._extract import BODY_LIMIT, extract_tool_name, extract_x402_payment

if TYPE_CHECKING:
    from ..logger import GT8004Logger


_DEFAULT_EXCLUDE_PATHS: set[str] = {
    "/health",
    "/healthz",
    "/readyz",
    "/_health",
}


class GT8004ASGIMiddleware:
    """ASGI middleware that logs ALL HTTP requests including those short-circuited
    by outer middleware layers (e.g. x402 402 responses).

    Must be the outermost ASGI wrapper to see every request.
    """

    def __init__(
        self,
        app: ASGIApp,
        logger: "GT8004Logger",
        exclude_paths: set[str] | None = None,
    ):
        self.app = app
        self.logger = logger
        self.exclude_paths = (
            exclude_paths if exclude_paths is not None else _DEFAULT_EXCLUDE_PATHS
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path", "")
        if path in self.exclude_paths:
            return await self.app(scope, receive, send)

        start = time.time()
        method = scope.get("method", "")

        # Extract headers from ASGI scope
        raw_headers: dict[str, str] = {}
        for key, value in scope.get("headers", []):
            raw_headers[key.decode("latin-1")] = value.decode("latin-1")

        # Capture request body (passthrough — inner app also reads from receive)
        request_body = bytearray()

        async def receive_wrapper():
            msg = await receive()
            chunk = msg.get("body", b"")
            if len(request_body) < BODY_LIMIT:
                request_body.extend(chunk[: BODY_LIMIT - len(request_body)])
            return msg

        # Capture response status + body
        status_code = 0
        response_body = bytearray()

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                if len(response_body) < BODY_LIMIT:
                    response_body.extend(chunk[: BODY_LIMIT - len(response_body)])
            await send(message)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        finally:
            elapsed = (time.time() - start) * 1000

            req_str = None
            if request_body:
                try:
                    req_str = bytes(request_body).decode("utf-8", errors="ignore")
                except Exception:
                    pass

            resp_str = None
            if response_body:
                try:
                    resp_str = bytes(response_body).decode("utf-8", errors="ignore")
                except Exception:
                    pass

            tool_name = extract_tool_name(self.logger.protocol, req_str, path)
            x402 = extract_x402_payment(raw_headers.get("x-payment"))

            client = scope.get("client")
            hdr = {
                k: v
                for k, v in {
                    "user-agent": raw_headers.get("user-agent"),
                    "content-type": raw_headers.get("content-type"),
                    "referer": raw_headers.get("referer"),
                }.items()
                if v is not None
            }

            entry = RequestLogEntry(
                request_id=str(uuid.uuid4()),
                method=method,
                path=path,
                status_code=status_code,
                response_ms=elapsed,
                tool_name=tool_name,
                protocol=self.logger.protocol,
                request_body=req_str,
                request_body_size=len(request_body) if request_body else None,
                response_body=resp_str,
                response_body_size=len(response_body) if response_body else None,
                headers=hdr or None,
                ip_address=client[0] if client else None,
                user_agent=raw_headers.get("user-agent"),
                content_type=raw_headers.get("content-type"),
                timestamp=datetime.utcnow().isoformat() + "Z",
                x402_amount=x402["x402_amount"],
                x402_tx_hash=x402["x402_tx_hash"],
                x402_token=x402["x402_token"],
                x402_payer=x402["x402_payer"],
            )

            try:
                await self.logger.log(entry)
            except Exception:
                logging.warning("GT8004 ASGI logging failed", exc_info=True)