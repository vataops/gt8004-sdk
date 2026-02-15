"""Middleware integrations for GT8004 SDK."""

from .fastapi import GT8004Middleware

__all__ = ["GT8004Middleware"]

# Optional: FastMCP middleware (requires fastmcp)
try:
    from .mcp import GT8004MCPMiddleware
    __all__.append("GT8004MCPMiddleware")
except ImportError:
    pass

# Optional: Flask/WSGI middleware (no extra deps)
try:
    from .flask import GT8004FlaskMiddleware
    __all__.append("GT8004FlaskMiddleware")
except ImportError:
    pass
