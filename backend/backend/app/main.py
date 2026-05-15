"""
Aftergift Backend - FastAPI Main Entry Point
Phase 2B | app/main.py
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import APP_TITLE, APP_DESCRIPTION, VERSION, API_PREFIX
from app.routers import gifts, reviews, favorites, reports, admin, auth

# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (local development only) ────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(gifts.router, prefix=API_PREFIX)
app.include_router(reviews.router, prefix=API_PREFIX)
app.include_router(favorites.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["health"])
def health():
    """健康检查"""
    return {
        "code": 200,
        "message": "ok",
        "data": {
            "version": VERSION,
            "status": "running"
        }
    }


# ── Root ─────────────────────────────────────────────────────────────────────

@app.get("/", tags=["root"])
def root():
    return {
        "message": f"Aftergift Backend MVP {VERSION}",
        "docs": "/docs"
    }
