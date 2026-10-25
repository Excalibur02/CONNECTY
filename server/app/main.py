import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from server.app.config import settings
from server.app.database import init_db, generate_pairing_pin, cleanup_temporary_pairings
from server.app.services.discovery import discovery_service
from server.app.api.device import router as device_router
from server.app.api.files import router as files_router
from server.app.api.transfers import router as transfers_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("connecty.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting CONNECTY Server...")
    init_db()
    generate_pairing_pin()
    removed = cleanup_temporary_pairings()
    if removed:
        logger.info(f"Cleared {removed} temporary pairing(s) on server startup")
    discovery_service.start()
    logger.info(f"CONNECTY running at http://{settings.LAN_IP}:{settings.PORT}")
    logger.info(f"Base data directory: {settings.BASE_DIR.resolve()}")
    yield
    # Shutdown
    logger.info("Stopping CONNECTY Server...")
    discovery_service.stop()

app = FastAPI(
    title="CONNECTY - Peer-to-Peer Home File Sharing",
    description="A serverless peer-to-peer home network file sharing and streaming service",
    version=settings.PROTOCOL_VERSION,
    lifespan=lifespan
)

# Enable CORS for LAN access and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints
app.include_router(device_router)
app.include_router(files_router)
app.include_router(transfers_router)

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "device_name": settings.DEVICE_NAME,
        "lan_ip": settings.LAN_IP,
        "port": settings.PORT
    }

# Built-in lightweight mobile browser UI for phones on LAN without apps
from server.app.web_ui import get_embedded_ui_html
@app.get("/", response_class=HTMLResponse)
async def serve_builtin_ui():
    return HTMLResponse(content=get_embedded_ui_html())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
