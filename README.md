# GT8004 Python SDK

Official Python SDK for [GT8004](https://gt8004.xyz) - AI Agent Analytics & Observability Platform.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
pip install git+https://github.com/vataops/gt8004-sdk.git
```

## Quick Start

### MCP Server (FastMCP)

```python
from fastmcp import FastMCP
from gt8004 import GT8004Logger
from gt8004.middleware.mcp import GT8004MCPMiddleware

logger = GT8004Logger(agent_id="your-agent-id", api_key="your-api-key", protocol="mcp")
logger.transport.start_auto_flush()

mcp = FastMCP("my-server")
mcp.add_middleware(GT8004MCPMiddleware(logger))

@mcp.tool()
def search(query: str) -> str:
    return "results..."
# Automatically logs tool_name="search", protocol="mcp"
```

### A2A Server (FastAPI)

```python
from fastapi import FastAPI
from gt8004 import GT8004Logger
from gt8004.middleware.fastapi import GT8004Middleware

logger = GT8004Logger(agent_id="your-agent-id", api_key="your-api-key", protocol="a2a")
logger.transport.start_auto_flush()

app = FastAPI()
app.add_middleware(GT8004Middleware, logger=logger)
# Automatically extracts skill_id from A2A request bodies
```

### Flask / Django

```python
from flask import Flask
from gt8004 import GT8004Logger
from gt8004.middleware.flask import GT8004FlaskMiddleware

logger = GT8004Logger(agent_id="your-agent-id", api_key="your-api-key")
logger.transport.start_auto_flush()

app = Flask(__name__)
app.wsgi_app = GT8004FlaskMiddleware(app.wsgi_app, logger)
```

Your analytics are now live at `https://gt8004.xyz/agents/{agent-id}` with protocol-specific breakdowns.

## Features

- Multi-framework support (FastMCP, FastAPI, Flask, Django)
- Protocol-aware logging (MCP, A2A)
- Automatic tool/skill name extraction per protocol
- Non-blocking async transport
- Auto-retry with exponential backoff
- Circuit breaker protection

## Supported Frameworks

| Framework | Middleware | Install |
|-----------|-----------|---------|
| FastMCP (MCP servers) | `GT8004MCPMiddleware` | `pip install gt8004-sdk[mcp]` |
| FastAPI / Starlette | `GT8004Middleware` | `pip install gt8004-sdk[fastapi]` |
| Flask / Django | `GT8004FlaskMiddleware` | `pip install gt8004-sdk` |

## Protocol Support

| Protocol | Tool Name Source | Example |
|----------|----------------|---------|
| *(none)* | URL path last segment | `/api/search` -> `search` |
| `mcp` | FastMCP `on_call_tool` hook | `@mcp.tool() def search(...)` -> `search` |
| `a2a` | Request body `skill_id` | `{"skill_id":"translate"}` -> `translate` |

## License

MIT - see [LICENSE](LICENSE)