"""
Aftergift Backend - Database Connection Layer
Phase 2B | 使用 sqlite3 标准库，设置 row_factory = sqlite3.Row
复用 Phase 2A schema/sqlite_schema.sql 和 schema/seed_data.sql
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional

# ── Path setup ──────────────────────────────────────────────────────────────

# backend/app/database.py → backend/ → aftergift-backend-mvp/
# Use absolute path from project root so imports from scripts/ work correctly
_BACKEND_ROOT = Path(__file__).resolve().parent.parent  # → aftergift-backend-mvp/backend/
_SCHEMA_DIR = (_BACKEND_ROOT / ".." / "schema").resolve()  # → aftergift-backend-mvp/schema/
SCHEMA_PATH = str(_SCHEMA_DIR / "sqlite_schema.sql")
SEED_PATH = str(_SCHEMA_DIR / "seed_data.sql")

def _get_db_path() -> str:
    """从 config 导入，避免循环导入"""
    db_path = os.getenv("AFTERGIFT_DB_PATH", "./aftergift_dev.db")
    if not db_path.startswith("/"):
        db_path = str(_BACKEND_ROOT / db_path)
    return db_path

DB_PATH: str = _get_db_path()

# ── Connection factory ───────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """
    获取数据库连接。
    每次新建连接时设置 row_factory = sqlite3.Row，
    保证可以直接用 row['col_name'] 访问列。
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── Database initialization ──────────────────────────────────────────────────

def init_db(drop_existing: bool = False) -> dict:
    """
    初始化数据库：执行 schema 和 seed data。

    Args:
        drop_existing: 如果为 True，删除旧数据库重新创建（开发用）

    Returns:
        包含表数量和记录数量的 dict
    """
    if drop_existing and os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = get_connection()

    # Execute schema
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    # Execute seed data
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    conn.commit()

    # Count tables and records
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    table_count = len(cur.fetchall())

    cur = conn.execute("SELECT COUNT(*) FROM gifts")
    gift_count = cur.fetchone()[0]

    conn.close()
    return {"tables": table_count, "gifts": gift_count}

def close_connection(conn: sqlite3.Connection) -> None:
    """关闭数据库连接。"""
    conn.close()
