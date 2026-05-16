#!/usr/bin/env python3
"""
Aftergift Backend - Migration Tests
Phase 2F.1 | test_migrations.py

测试数据库迁移的幂等性、旧数据库升级、schema_migrations 追踪。
不依赖 pytest，可直接 python3 运行。
"""

import sys
import os
import sqlite3
import tempfile

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

print("Aftergift Backend - Migration Tests (Phase 2F.1)")
print("=" * 50)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _create_old_schema_db(db_path: str) -> None:
    """创建一个不含 redaction_summary 的"旧版"数据库。"""
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            anonymous_nickname TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS gifts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS review_logs (
            id TEXT PRIMARY KEY,
            gift_id TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            reviewer_type TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def _column_exists(db_path: str, table: str, column: str) -> bool:
    conn = sqlite3.connect(db_path)
    cur = conn.execute(f"PRAGMA table_info({table})")
    exists = any(row[1] == column for row in cur.fetchall())
    conn.close()
    return exists


def _migration_recorded(db_path: str, name: str) -> bool:
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE migration_name = ?",
        (name,)
    )
    exists = cur.fetchone() is not None
    conn.close()
    return exists


# ── Tests ────────────────────────────────────────────────────────────────────

def test_migration_adds_column():
    """旧数据库运行 migration 后，redaction_summary 列存在。"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        _create_old_schema_db(db_path)
        assert not _column_exists(db_path, "review_logs", "redaction_summary"), \
            "Old DB should not have redaction_summary"

        # Run migration via runner
        from scripts.migrate_db import run_migrations
        results = run_migrations(db_path=db_path)

        assert _column_exists(db_path, "review_logs", "redaction_summary"), \
            "Migration should add redaction_summary"
        assert any("applied" in r for r in results), \
            f"Expected 'applied' in results: {results}"

        os.unlink(db_path)
        print("  ✅ PASS [migration_adds_column] column added to old DB")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [migration_adds_column] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_migration_idempotent():
    """再次运行 migration 不应报错（幂等）。"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        _create_old_schema_db(db_path)

        from scripts.migrate_db import run_migrations
        run_migrations(db_path=db_path)  # First run
        results = run_migrations(db_path=db_path)  # Second run

        assert any("skipped" in r for r in results), \
            f"Expected 'skipped' on second run: {results}"

        os.unlink(db_path)
        print("  ✅ PASS [migration_idempotent] second run skipped")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [migration_idempotent] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_migrations_recorded():
    """migration 执行后 schema_migrations 表有记录。"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        _create_old_schema_db(db_path)

        from scripts.migrate_db import run_migrations
        run_migrations(db_path=db_path)

        assert _migration_recorded(db_path, "001_add_review_logs_redaction_summary"), \
            "schema_migrations should record 001"

        os.unlink(db_path)
        print("  ✅ PASS [schema_migrations_recorded] migration tracked")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [schema_migrations_recorded] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_new_schema_safe_skip():
    """新 schema 初始化后的数据库，migration 应安全跳过。"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Create DB with new schema (includes redaction_summary)
        conn = sqlite3.connect(db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                anonymous_nickname TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS review_logs (
                id TEXT PRIMARY KEY,
                gift_id TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                reviewer_type TEXT NOT NULL,
                redaction_summary TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()

        from scripts.migrate_db import run_migrations
        results = run_migrations(db_path=db_path)

        assert any("skipped" in r for r in results), \
            f"Expected skip for new schema: {results}"
        assert _migration_recorded(db_path, "001_add_review_logs_redaction_summary"), \
            "Should record even when skipped"

        os.unlink(db_path)
        print("  ✅ PASS [new_schema_safe_skip] migration skipped on new schema")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [new_schema_safe_skip] {e}")
        import traceback
        traceback.print_exc()
        return False


# ── Runner ───────────────────────────────────────────────────────────────────

TESTS = [
    test_migration_adds_column,
    test_migration_idempotent,
    test_schema_migrations_recorded,
    test_new_schema_safe_skip,
]

if __name__ == "__main__":
    passed = 0
    failed = 0
    for t in TESTS:
        if t():
            passed += 1
        else:
            failed += 1
    print(f"\nResult: {passed}/{len(TESTS)} passed")
    if failed == 0:
        print("ALL TESTS PASSED ✅")
    else:
        print(f"SOME TESTS FAILED ❌ ({failed} failures)")
        sys.exit(1)
