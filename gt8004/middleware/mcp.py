"""FastMCP middleware for GT8004 request logging.

Hooks into FastMCP's middleware system to capture tool calls
at the semantic level (not raw HTTP).

Requires: pip install gt8004-sdk[mcp]
"""

import json
import time
import uuid
from typing import TYPE_CHECKING
from datetime import datetime

from fastmcp.server.middleware import Middleware, MiddlewareContext

if TYPE_CHECKING:
    from ..logger import GT8004Logger

from ..types import RequestLogEntry
from ._extract import BODY_LIMIT


class GT8004MCPMiddleware(Middleware):
    """
    FastMCP middleware that logs tool calls to GT8004.

    Usage:
        from fastmcp import FastMCP
        from gt8004 import GT8004Logger
        from gt8004.middleware.mcp import GT8004MCPMiddleware

        logger = GT8004Logger(agent_id="...", api_key="...", protocol="mcp")
        logger.transport.start_auto_flush()

        mcp = FastMCP("my-server")
        mcp.add_middleware(GT8004MCPMiddleware(logger))

        @mcp.tool()
        def search(query: str) -> str:
            return "results..."
        # Automatically logs tool_name="search", protocol="mcp"
    """

    def __init__(self, logger: "GT8004Logger"):
        self.logger = logger

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        start = time.time()
        tool_name = context.message.name
        args = context.message.arguments

        status = 200
        error_type = None
        try:
            result = await call_next(context)
        except Exception as e:
            status = 500
            error_type = type(e).__name__
            raise
        else:
            return result
        finally:
            elapsed = (time.time() - start) * 1000

            request_body = None
            if args:
                try:
                    raw = json.dumps(args)
                    request_body = raw[:BODY_LIMIT] if len(raw) > BODY_LIMIT else raw
                except (TypeError, ValueError):
                    pass

            entry = RequestLogEntry(
                request_id=str(uuid.uuid4()),
                method="tools/call",
                path=f"/mcp/tools/{tool_name}",
                status_code=status,
                response_ms=elapsed,
                tool_name=tool_name,
                protocol="mcp",
                request_body=request_body,
                error_type=error_type,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
            await self.logger.log(entry)
