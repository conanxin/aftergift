#!/usr/bin/env python3
"""
Aftergift Backend - Database Migration Runner
Phase 2F.1 | scripts/migrate_db.py

用法:
    cd backend/backend
    python scripts/migrate_db.py

环境变量:
    AFTERGIFT_DB_PATH — 数据库文件路径（默认 ./aftergift_dev.db）
"""

import sys
import os
import sqlite3
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).resolve().parent          # → backend/scripts/
_BACKEND_ROOT = _SCRIPT_DIR.parent                      # → backend/
_PROJECT_ROOT = _BACKEND_ROOT.parent                    # → aftergift/
_MIGRATIONS_DIR = _PROJECT_ROOT / "migrations"          # → aftergift/migrations/

sys.path.insert(0, str(_BACKEND_ROOT))

from app.database import get_connection, DB_PATH

# ── Migration registry ───────────────────────────────────────────────────────

MIGRATIONS = [
    {
        "name": "001_add_review_logs_redaction_summary",
        "sql_file": _MIGRATIONS_DIR / "001_add_review_logs_redaction_summary.sql",
        "check_column": ("review_logs", "redaction_summary"),
    },
    {
        "name": "002_add_user_actions",
        "sql_file": _MIGRATIONS_DIR / "002_add_user_actions.sql",
        "check_table": "user_actions",
    },
]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """检查表是否已存在。"""
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    return cur.fetchone() is not None


def _ensure_schema_migrations_table(conn: sqlite3.Connection) -> None:
    """创建 schema_migrations 追踪表（如果不存在）。"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_name TEXT UNIQUE NOT NULL,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def _is_migration_applied(conn: sqlite3.Connection, name: str) -> bool:
    """检查 migration 是否已在 schema_migrations 中记录。"""
    cur = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE migration_name = ?",
        (name,)
    )
    return cur.fetchone() is not None


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """检查表中是否已存在指定列。"""
    cur = conn.execute(f"PRAGMA table_info({table})")
    for row in cur.fetchall():
        if row[1] == column:
            return True
    return False


def apply_migration(conn: sqlite3.Connection, migration: dict) -> str:
    """
    执行单个 migration，返回状态字符串。

    幂等逻辑：
    1. 如果 schema_migrations 已记录 → skipped
    2. 如果 check_column 指定的列已存在 → 记录并 skipped
    3. 否则执行 SQL 文件 → applied
    """
    name = migration["name"]

    if _is_migration_applied(conn, name):
        return f"skipped (already recorded): {name}"

    table, column = migration.get("check_column", (None, None))
    if table and column and _column_exists(conn, table, column):
        # Column already exists — record it and skip
        conn.execute(
            "INSERT INTO schema_migrations (migration_name) VALUES (?)",
            (name,)
        )
        conn.commit()
        return f"skipped (column exists): {name}"

    check_table = migration.get("check_table")
    if check_table and _table_exists(conn, check_table):
        conn.execute(
            "INSERT INTO schema_migrations (migration_name) VALUES (?)",
            (name,)
        )
        conn.commit()
        return f"skipped (table exists): {name}"

    # Execute SQL file
    sql_path = migration["sql_file"]
    if not sql_path.exists():
        return f"error (file not found): {sql_path}"

    sql = sql_path.read_text(encoding="utf-8")
    conn.executescript(sql)

    conn.execute(
        "INSERT INTO schema_migrations (migration_name) VALUES (?)",
        (name,)
    )
    conn.commit()
    return f"applied: {name}"


def run_migrations(db_path: str = None) -> list:
    """
    运行所有未应用的 migrations。

    Args:
        db_path: 可选，覆盖默认数据库路径。

    Returns:
        每个 migration 的状态字符串列表。
    """
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_schema_migrations_table(conn)
        results = []
        for migration in MIGRATIONS:
            status = apply_migration(conn, migration)
            results.append(status)
        return results
    finally:
        conn.close()


def main():
    print(f"Aftergift Database Migration Runner")
    print(f"Database: {DB_PATH}")
    print(f"Migrations dir: {_MIGRATIONS_DIR}")
    print("-" * 50)

    results = run_migrations()
    for status in results:
        print(f"  {status}")

    print("-" * 50)
    print("Migration complete.")


if __name__ == "__main__":
    main()
