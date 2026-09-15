import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router
from app.api.citations import router as citations_router
from app.api.compare import router as compare_router
from app.api.documents import router as documents_router
from app.api.exports import router as exports_router
from app.api.health import router as health_router
from app.api.literature_review import router as lit_review_router
from app.api.notes import router as notes_router
from app.api.operations import router as operations_router
from app.api.papers import router as papers_router
from app.api.projects import router as projects_router
from app.api.research import router as research_router
from app.api.routes import router as legacy_router
from app.api.summaries import router as summaries_router
from app.config import settings
from app.db.session import init_db

logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown routines."""
    logger.info("Starting ResearchOps AI platform...")
    init_db()
    yield
    logger.info("Shutting down ResearchOps AI platform...")


# Ensure DB tables are initialized on startup or import
init_db()


app = FastAPI(
    title="ResearchOps AI API",
    description=(
        "An intelligent scholarly literature research, document intelligence, RAG-based analysis, "
        "and DevOps operations platform."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for local testing and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Mount legacy compatibility routes (/health, /research, /papers)
app.include_router(legacy_router)

# 2. Mount expanded modular routers
app.include_router(health_router)
app.include_router(research_router)
app.include_router(projects_router)
app.include_router(papers_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(summaries_router)
app.include_router(compare_router)
app.include_router(lit_review_router)
app.include_router(notes_router)
app.include_router(citations_router)
app.include_router(exports_router)
app.include_router(operations_router)

# Mount static folder if it exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the single-page research interface."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": f"Welcome to {settings.app_name} v{settings.app_version}. Visit /docs for API documentation.",
        "health": "/health",
        "ready": "/ready",
        "metrics": "/metrics",
        "operations": "/api/operations/overview",
        "docs": "/docs",
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)
