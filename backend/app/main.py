"""VisionCorrect FastAPI application entry point."""

from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.models.schemas import HealthResponse
from app.routes.correct import router as correct_router
from vision_engine import __version__ as engine_version

app = FastAPI(
    title="VisionCorrect API",
    version=engine_version,
    description=(
        "Personalized computational rendering for vision-adaptive displays. "
        "Experimental R&D prototype - not a medical device and not a replacement "
        "for prescribed corrective eyewear."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(correct_router)

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="VisionCorrect API", version=engine_version)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


@app.get("/test", include_in_schema=False)
async def test_harness() -> FileResponse:
    """Blinded 3-condition human test harness."""
    return FileResponse(os.path.join(_STATIC_DIR, "test.html"))


@app.get("/distance", include_in_schema=False)
async def distance_adaptive() -> FileResponse:
    """Webcam distance-adaptive correction demo (camera needs a secure context)."""
    return FileResponse(os.path.join(_STATIC_DIR, "distance.html"))


@app.get("/selftest", include_in_schema=False)
async def selftest() -> FileResponse:
    """Big live pre-distortion viewer for testing on your own eyes."""
    return FileResponse(os.path.join(_STATIC_DIR, "selftest.html"))


if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
