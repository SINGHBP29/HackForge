import asyncio
import logging
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")

# Create MCP server
mcp_server = FastMCP("puchai-mcp")

@mcp_server.tool("echo")
async def echo_tool(text: str) -> str:
    """Echo back whatever text you send."""
    return f"Echo: {text}"

async def websocket_handler(websocket: WebSocket):
    await websocket.accept()
    logger.info("✅ WebSocket connection accepted")

    queue = asyncio.Queue()

    async def reader():
        while True:
            try:
                data = await websocket.receive_text()
                logger.info(f"📥 Received from client: {data}")
                await queue.put(data)
            except Exception as e:
                logger.warning(f"❌ Reader stopped: {e}")
                break
        await queue.put(None)

    async def read():
        data = await queue.get()
        return data.encode("utf-8") if data is not None else None

    async def write(data: bytes):
        text = data.decode("utf-8")
        logger.info(f"📤 Sending to client: {text}")
        await websocket.send_text(text)

    reader_task = asyncio.create_task(reader())
    try:
        if hasattr(mcp_server, "serve"):
            await mcp_server.serve(read, write)  # Preferred if available
        else:
            await mcp_server.run(read, write)
    finally:
        reader_task.cancel()
        try:
            await reader_task
        except asyncio.CancelledError:
            pass
        logger.info("🔌 WebSocket closed")

# FastAPI setup
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/mcp/ws")
async def mcp_ws(websocket: WebSocket):
    await websocket_handler(websocket)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=3000, reload=True)
