# api/main.py
"""
ShopFloorScheduler — FastAPI application entry point.

Run locally:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

Swagger UI:  http://localhost:8000/docs
ReDoc:       http://localhost:8000/redoc
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routers import health, schedule, history, auth, analytics, reschedule, ws
from core.logger import logger

# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ShopFloorScheduler API",
    description=(
        "AI-powered production scheduling and optimization system. "
        "Upload your production data, choose an algorithm, and receive "
        "an optimized schedule with full KPI analytics."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS — allow Next.js frontend running on port 3000 (and any other origin in dev)
# ---------------------------------------------------------------------------

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static files — serve generated Gantt chart PNGs
# ---------------------------------------------------------------------------

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(schedule.router)
app.include_router(history.router)
app.include_router(analytics.router)
app.include_router(reschedule.router)
app.include_router(ws.router)

# ---------------------------------------------------------------------------
# Startup / Shutdown events
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup():
    import asyncio
    from api.routers.ws import set_main_loop
    set_main_loop(asyncio.get_running_loop())

    from core.database import init_db
    init_db()  # Create SQLite tables if they don't exist (TASK-13)
    logger.info("ShopFloorScheduler API starting up (v2.0.0 — Phase 3).")
    logger.info("Swagger docs available at http://localhost:8000/docs")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("ShopFloorScheduler API shutting down.")
