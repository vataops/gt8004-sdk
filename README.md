# GT8004 Python SDK

Official Python SDK for [GT8004](https://gt8004.xyz) - AI Agent Analytics & Observability Platform.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
pip install git+https://github.com/vataops/gt8004-sdk.git
```

With framework-specific extras:

```bash
# FastAPI / Starlette
pip install "gt8004-sdk[fastapi] @ git+https://github.com/vataops/gt8004-sdk.git"

# FastMCP (MCP servers)
pip install "gt8004-sdk[mcp] @ git+https://github.com/vataops/gt8004-sdk.git"

# All frameworks
pip install "gt8004-sdk[all] @ git+https://github.com/vataops/gt8004-sdk.git"
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

@app.on_event("shutdown")
async def shutdown():
    await logger.close()
```

### A2A + x402 Payment (ASGI)

When using x402 payment middleware, use `GT8004ASGIMiddleware` as the **outermost** wrapper to capture all requests including 402 payment responses:

```python
from fastapi import FastAPI
from gt8004 import GT8004Logger
from gt8004.middleware.asgi import GT8004ASGIMiddleware

logger = GT8004Logger(agent_id="your-agent-id", api_key="your-api-key", protocol="a2a")
logger.transport.start_auto_flush()

app = FastAPI()

# Apply x402 payment middleware first, then GT8004 outermost
app = x402_middleware(app)
app = GT8004ASGIMiddleware(app, logger)
# Automatically captures x402 payment fields (amount, tx_hash, payer)
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

## Configuration

### Environment Variables

```bash
export GT8004_AGENT_ID="your-agent-id"
export GT8004_API_KEY="your-api-key"
```

```python
import os
from gt8004 import GT8004Logger

logger = GT8004Logger(
    agent_id=os.environ["GT8004_AGENT_ID"],
    api_key=os.environ["GT8004_API_KEY"],
    network="mainnet",       # "mainnet" (default) or "testnet"
    protocol="a2a",          # "mcp" or "a2a" (optional)
    batch_size=50,           # Flush after N entries (default: 50)
    flush_interval=5.0,      # Auto-flush interval in seconds (default: 5.0)
)
```

### Lifecycle

```python
# Start auto-flush background task
logger.transport.start_auto_flush()

# Verify connectivity on startup
ok = await logger.verify_connection()

# Graceful shutdown (flushes pending logs)
await logger.close()
```

## Features

- Multi-framework support (FastMCP, FastAPI, Flask, Django)
- Protocol-aware logging (MCP, A2A)
- Automatic tool/skill name extraction per protocol
- x402 payment tracking (amount, tx hash, payer)
- Non-blocking async transport with batch buffering
- Auto-retry with exponential backoff
- Circuit breaker protection

## Supported Frameworks

| Framework | Middleware | Install Extra |
|-----------|-----------|---------------|
| FastMCP (MCP servers) | `GT8004MCPMiddleware` | `[mcp]` |
| FastAPI / Starlette | `GT8004Middleware` | `[fastapi]` |
| Pure ASGI (x402 compatible) | `GT8004ASGIMiddleware` | `[fastapi]` |
| Flask / Django (WSGI) | `GT8004FlaskMiddleware` | *(none)* |

## Protocol Support

| Protocol | Tool Name Source | Example |
|----------|----------------|---------|
| *(none)* | URL path last segment | `/api/search` -> `search` |
| `mcp` | FastMCP `on_call_tool` hook | `@mcp.tool() def search(...)` -> `search` |
| `a2a` | Request body `skill_id` or path | `{"skill_id":"translate"}` -> `translate` |

## x402 Payment Logging

All middleware adapters automatically extract x402 payment data from HTTP headers:

- `x402_amount` - Payment amount in USDC
- `x402_tx_hash` - On-chain settlement transaction hash
- `x402_token` - Token identifier (e.g. `USDC-base`)
- `x402_payer` - Payer wallet address

No additional configuration needed — payment headers (`X-Payment`, `X-Payment-Response`) are parsed automatically when present.

## License

MIT - see [LICENSE](LICENSE)