"""Example FastAPI application with GT8004 SDK integration."""

import os
from fastapi import FastAPI
from gt8004 import GT8004Logger
from gt8004.middleware.fastapi import GT8004Middleware

# Initialize GT8004 logger
logger = GT8004Logger(
    agent_id=os.getenv("GT8004_AGENT_ID", "example-agent"),
    api_key=os.getenv("GT8004_API_KEY", "your-api-key"),
    ingest_url=os.getenv("GT8004_INGEST_URL", "http://localhost:9092/v1/ingest"),
    batch_size=50,  # Flush after 50 requests
    flush_interval=5.0,  # Or flush every 5 seconds
)

# Start auto-flush background task
logger.transport.start_auto_flush()

# Create FastAPI app
app = FastAPI(title="GT8004 Example Agent")

# Add GT8004 middleware (this will automatically log all requests)
app.add_middleware(GT8004Middleware, logger=logger)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Hello from GT8004 Example Agent"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/chat")
async def chat(message: dict):
    """Example chat endpoint."""
    user_message = message.get("message", "")
    response = {
        "reply": f"You said: {user_message}",
        "agent": "example-agent"
    }
    return response


@app.on_event("startup")
async def startup_event():
    """Run on app startup."""
    print("GT8004 Example Agent started")
    print(f"Agent ID: {logger.agent_id}")
    print(f"Ingest URL: {logger.transport.ingest_url}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on app shutdown - flush pending logs."""
    print("Flushing pending logs...")
    await logger.close()
    print("GT8004 Example Agent stopped")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
