"""
Aftergift Backend - Configuration Management
Phase 2B | 使用 python-dotenv 读取环境变量
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if exists
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

# ── Environment ──────────────────────────────────────────────────────────────

ENV: str = os.getenv("AFTERGIFT_ENV", "development")
DB_PATH: str = os.getenv("AFTERGIFT_DB_PATH", "./aftergift_dev.db")
ENABLE_REAL_AI_REVIEW: bool = os.getenv("AFTERGIFT_ENABLE_REAL_AI_REVIEW", "false").lower() in ("true", "1", "yes")
ADMIN_TOKEN: str = os.getenv("AFTERGIFT_ADMIN_TOKEN", "change-me-dev-only")

# ── Derived flags ───────────────────────────────────────────────────────────

IS_DEV: bool = ENV == "development"
IS_PROD: bool = ENV == "production"

# ── Database path resolution ────────────────────────────────────────────────

def get_db_path() -> str:
    """Resolve DB path relative to backend/ directory or as absolute."""
    db_path = DB_PATH
    if not db_path.startswith("/"):
        # Relative to backend/ directory
        backend_dir = Path(__file__).parent.parent
        db_path = str(backend_dir / db_path)
    return db_path

# ── Constants ────────────────────────────────────────────────────────────────

API_PREFIX: str = "/api"
VERSION: str = "2.0.0-alpha"
APP_TITLE: str = "Aftergift Backend MVP"
APP_DESCRIPTION: str = "故事型礼物流转平台后端 API | Phase 2B"
