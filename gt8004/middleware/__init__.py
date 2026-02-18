"""Middleware integrations for GT8004 SDK."""

__all__ = []

# Optional: FastAPI/ASGI middleware (requires fastapi)
try:
    from .fastapi import GT8004Middleware
    __all__.append("GT8004Middleware")
except ImportError:
    pass

# Optional: Pure ASGI middleware (requires starlette)
try:
    from .asgi import GT8004ASGIMiddleware
    __all__.append("GT8004ASGIMiddleware")
except ImportError:
    pass

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
