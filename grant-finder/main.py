"""
Main FastAPI Application — AI Grant & Funding Finder
IBM Cloud Lite + IBM Granite powered grant discovery platform for startups.
"""

import os
import sys
import logging
import logging.config
from contextlib import asynccontextmanager

# Fix Windows console encoding for emoji/Unicode in log messages
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

# ── Logging Setup ────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.getenv("LOG_FILE", "logs/grant_finder.log")),
    ],
)
logger = logging.getLogger(__name__)

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== AI Grant & Funding Finder starting up ===")
    logger.info(f"IBM Granite Model: {os.getenv('IBM_GRANITE_MODEL_ID', 'ibm/granite-3-8b-instruct')}")
    logger.info(f"IBM watsonx URL:   {os.getenv('IBM_WATSONX_URL', 'not configured')}")
    logger.info(f"IBM NLU:           {'configured' if os.getenv('IBM_NLU_API_KEY') else 'not configured (fallback active)'}")
    logger.info(f"IBM COS Cache:     {'configured' if os.getenv('IBM_COS_API_KEY') else 'in-memory fallback active'}")
    yield
    logger.info("=== Grant Finder shutting down ===")


# ── App Instance ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Grant & Funding Finder",
    description=(
        "Intelligent grant discovery and proposal generation for startups. "
        "Powered by IBM Granite (watsonx.ai) and IBM Watson NLU. "
        "Problem Statement #18 — IBM Cloud Lite Services."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routes ───────────────────────────────────────────────────────────
from backend.routes.grants import router as grants_router
from backend.routes.proposals import router as proposals_router

app.include_router(grants_router)
app.include_router(proposals_router)


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
async def health_check():
    """System health check — verifies IBM service configurations."""
    granite_api_key = os.getenv("IBM_WATSONX_API_KEY", "")
    granite_project = os.getenv("IBM_WATSONX_PROJECT_ID", "")
    granite_configured = bool(granite_api_key and granite_project)

    nlu_api_key = os.getenv("IBM_NLU_API_KEY", "")
    nlu_url = os.getenv("IBM_NLU_URL", "")
    nlu_real = bool(
        nlu_api_key and nlu_api_key != "your_nlu_api_key_here"
        and nlu_url and "your-instance-id" not in nlu_url
    )

    cos_configured = bool(os.getenv("IBM_COS_API_KEY"))

    # Check live Granite availability if configured
    from backend.services.granite_service import granite_service
    granite_status = "⚠ not configured — set IBM_WATSONX_API_KEY & PROJECT_ID"
    if granite_configured:
        if granite_service._granite_available is True:
            granite_status = "live ✓ (IBM Granite responding)"
        elif granite_service._granite_available is False:
            granite_status = (
                "⚠ 403 Forbidden — associate Watson Machine Learning with project at "
                "dataplatform.cloud.ibm.com → project → Manage → Services & integrations"
            )
        else:
            granite_status = "configured ✓ (not yet tested — will verify on first request)"

    return {
        "status": "operational",
        "ibm_granite": granite_status,
        "ibm_nlu": "configured ✓" if nlu_real else "⚠ using keyword fallback (set IBM_NLU_API_KEY & IBM_NLU_URL)",
        "ibm_cos": "configured ✓" if cos_configured else "⚠ not configured — using in-memory cache",
        "model": os.getenv("IBM_GRANITE_MODEL_ID", "ibm/granite-3-8b-instruct"),
        "version": "1.0.0",
        "grants_in_database": 12,
        "tip": (
            "If ibm_granite shows 403: go to dataplatform.cloud.ibm.com -> open your project -> "
            "Manage -> Services & integrations -> Associate service -> Watson Machine Learning (Lite)"
        ) if granite_configured and granite_service._granite_available is False else None,
    }


# ── Serve Frontend ────────────────────────────────────────────────────────────
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(frontend_path):
    # Mount all static subdirectories so CSS/JS/assets are served correctly
    app.mount("/css",    StaticFiles(directory=os.path.join(frontend_path, "css")),    name="css")
    app.mount("/js",     StaticFiles(directory=os.path.join(frontend_path, "js")),     name="js")
    if os.path.isdir(os.path.join(frontend_path, "assets")):
        app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str):
        return FileResponse(os.path.join(frontend_path, "index.html"))


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=os.getenv("APP_ENV", "development") == "development",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
