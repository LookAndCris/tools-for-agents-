"""Application entry point — creates the FastAPI app and starts uvicorn."""
from __future__ import annotations

import uvicorn

from infrastructure.config import settings
from interfaces.api.app import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_env == "development",
    )
