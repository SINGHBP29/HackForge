from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

# Import routers from your routes folder
from routes import respond, mcp  # respond.py and mcp.py must define `router = APIRouter()`

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Server", description="MCP server running with NLP features", version="1.0")

# Enable CORS for all origins (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to specific origins for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to log raw request body
@app.middleware("http")
async def log_raw_body(request: Request, call_next):
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")
    logger.info(f"Raw body: {body_str}")

    # Recreate the request stream
    async def receive():
        return {"type": "http.request", "body": body_bytes, "more_body": False}
    request._receive = receive

    response = await call_next(request)
    return response

# Include routers
app.include_router(respond.router, prefix="")
app.include_router(mcp.router, prefix="/mcp")

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok", "message": "MCP server running with NLP features"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
