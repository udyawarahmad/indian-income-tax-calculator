"""FastAPI application entry point."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.export import router as export_router
from app.api.routes.history import router as history_router
from app.api.routes.profiles import router as profiles_router
from app.api.routes.tax import router as tax_router
from app.core.config import APP_NAME, APP_VERSION, CORS_ORIGINS
from app.database.db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("%s v%s started", APP_NAME, APP_VERSION)
    yield


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)

# CORS - allow configured origins; in desktop/local mode be permissive to localhost.
allow_origins = [o.strip() for o in CORS_ORIGINS if o.strip()]
# Also allow any localhost/127.0.0.1 port for desktop dev convenience
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "error": str(exc)})


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


app.include_router(tax_router)
app.include_router(history_router)
app.include_router(profiles_router)
app.include_router(export_router)

# Serve built frontend (for desktop/production) if present
FRONTEND_DIST = os.getenv("FRONTEND_DIST")
_frontend_candidates = [
    Path(FRONTEND_DIST) if FRONTEND_DIST else None,
    Path(__file__).resolve().parents[2] / "frontend" / "dist",
    Path(__file__).resolve().parents[1] / "static",
]
_frontend_dist = next((p for p in _frontend_candidates if p and p.exists() and (p / "index.html").exists()), None)
if _frontend_dist:
    assets_dir = _frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    async def root():
        return FileResponse(str(_frontend_dist / "index.html"))

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str, request: Request):
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        file_path = _frontend_dist / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_frontend_dist / "index.html"))
else:
    @app.get("/")
    async def root():
        return {"status": "ok", "app": APP_NAME, "version": APP_VERSION, "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False)
