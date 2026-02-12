# GT8004 Python SDK

Official Python SDK for [GT8004](https://github.com/HydroX-labs/gt8004) - AI Agent Analytics & Observability Platform.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
pip install git+https://github.com/HydroX-labs/gt8004-sdk.git
```

## Quick Start

```python
from fastapi import FastAPI
from gt8004 import GT8004Logger
from gt8004.middleware.fastapi import GT8004Middleware

logger = GT8004Logger(
    agent_id="your-agent-id",
    api_key="your-api-key"
)
logger.transport.start_auto_flush()

app = FastAPI()
app.add_middleware(GT8004Middleware, logger=logger)
```

**That's it!** Your analytics are now live at `https://gt8004.xyz/agents/{agent-id}` 📊

## Features

- 🚀 Zero-config FastAPI middleware
- 📊 Automatic request/response logging
- ⚡ Non-blocking async transport
- 🔄 Auto-retry with exponential backoff
- 🛡️ Circuit breaker protection

## Documentation

See [examples/](examples/) for complete examples.

## License

MIT - see [LICENSE](LICENSE)
