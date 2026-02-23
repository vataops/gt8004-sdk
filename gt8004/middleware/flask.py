"""WSGI middleware for GT8004 request logging.

Works with Flask, Django, and any WSGI-compatible framework.
Uses a background event loop to bridge sync WSGI to async BatchTransport.
"""

from __future__ import annotations

import asyncio
import io
import threading
import time
import uuid
from typing import TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from ..logger import GT8004Logger

from ..types import RequestLogEntry
from ._extract import BODY_LIMIT, extract_tool_name, extract_x402_payment


class GT8004FlaskMiddleware:
    """
    WSGI middleware that logs requests to GT8004.

    Usage (Flask):
        from flask import Flask
        from gt8004 import GT8004Logger
        from gt8004.middleware.flask import GT8004FlaskMiddleware

        logger = GT8004Logger(agent_id="...", api_key="...", protocol="a2a")
        logger.transport.start_auto_flush()

        app = Flask(__name__)
        app.wsgi_app = GT8004FlaskMiddleware(app.wsgi_app, logger)

    Usage (Django wsgi.py):
        application = GT8004FlaskMiddleware(application, logger)
    """

    def __init__(self, app, logger: "GT8004Logger"):
        self.app = app
        self.logger = logger
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._loop_lock = threading.Lock()

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create a background event loop for async logging."""
        with self._loop_lock:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                self._thread = threading.Thread(
                    target=self._loop.run_forever, daemon=True
                )
                self._thread.start()
            return self._loop

    def __call__(self, environ, start_response):
        start_time = time.time()
        request_id = str(uuid.uuid4())

        # Capture request
        method = environ.get("REQUEST_METHOD", "")
        path = environ.get("PATH_INFO", "/")

        # Read and restore request body stream
        body_stream = environ.get("wsgi.input")
        body_bytes = body_stream.read() if body_stream else b""
        environ["wsgi.input"] = io.BytesIO(body_bytes)

        request_body = None
        request_body_size = len(body_bytes)
        if body_bytes and request_body_size <= BODY_LIMIT:
            request_body = body_bytes.decode("utf-8", errors="ignore")

        # Intercept response status and headers
        status_code = 200
        response_headers: list[tuple[str, str]] = []

        def start_response_wrapper(status, headers, exc_info=None):
            nonlocal status_code, response_headers
            status_code = int(status.split(" ", 1)[0])
            response_headers = headers
            return start_response(status, headers, exc_info)

        # Call the WSGI app
        response_chunks = list(self.app(environ, start_response_wrapper))
        response_body_bytes = b"".join(response_chunks)

        elapsed = (time.time() - start_time) * 1000

        # Build log entry
        protocol = self.logger.protocol
        tool_name = extract_tool_name(protocol, request_body, path)

        response_body = None
        response_body_size = len(response_body_bytes)
        if response_body_bytes and response_body_size <= BODY_LIMIT:
            response_body = response_body_bytes.decode("utf-8", errors="ignore")

        # Extract headers
        user_agent = environ.get("HTTP_USER_AGENT")
        content_type = environ.get("CONTENT_TYPE")
        referer = environ.get("HTTP_REFERER")
        raw_headers = {
            "user-agent": user_agent,
            "content-type": content_type,
            "referer": referer,
        }
        headers = {k: v for k, v in raw_headers.items() if v is not None}

        # Extract x402 payment info from request + response headers
        resp_header_dict = {k.lower(): v for k, v in response_headers}
        x402 = extract_x402_payment(
            payment_request=environ.get("HTTP_X_PAYMENT"),
            payment_response=resp_header_dict.get("x-payment-response"),
        )

        entry = RequestLogEntry(
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            response_ms=elapsed,
            tool_name=tool_name,
            protocol=protocol,
            request_body=request_body,
            request_body_size=request_body_size,
            response_body=response_body,
            response_body_size=response_body_size,
            headers=headers if headers else None,
            ip_address=environ.get("REMOTE_ADDR"),
            user_agent=user_agent,
            referer=referer,
            content_type=content_type,
            timestamp=datetime.utcnow().isoformat() + "Z",
            x402_amount=x402["x402_amount"],
            x402_tx_hash=x402["x402_tx_hash"],
            x402_token=x402["x402_token"],
            x402_payer=x402["x402_payer"],
        )

        # Bridge sync WSGI to async logger via background event loop
        loop = self._get_loop()
        asyncio.run_coroutine_threadsafe(self.logger.log(entry), loop)

        return response_chunks
