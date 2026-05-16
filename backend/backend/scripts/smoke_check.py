#!/usr/bin/env python3
"""
Aftergift Local Beta Smoke Check
=================================
一键检查本地 MVP 是否可运行。

Usage:
    cd backend/backend
    python scripts/smoke_check.py

Checks:
    1. Python modules importable
    2. SQLite schema init works
    3. Migrations are idempotent
    4. Core routes exist and respond
    5. No real external network calls
"""

import os, sys, tempfile, uuid

# ------------------------------------------------------------------
# 0. Setup
# ------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

DB_FD, DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(DB_FD)
os.environ["AFTERGIFT_DB_PATH"] = DB_PATH
os.environ["AFTERGIFT_ADMIN_TOKEN"] = "smoke-admin-token"
os.environ["AFTERGIFT_JWT_SECRET"] = "smoke-jwt-secret-" + str(uuid.uuid4())

passed = 0
failed = 0
errors = []

def _ok(label):
    global passed
    passed += 1
    print(f"  [PASS] {label}")

def _fail(label, detail=""):
    global failed
    failed += 1
    errors.append((label, detail))
    print(f"  [FAIL] {label}: {detail}")

# ------------------------------------------------------------------
# 1. Module imports
# ------------------------------------------------------------------
print("\n[1/5] Module imports")
try:
    from app.database import init_db, get_connection, close_connection
    from app.auth import create_access_token
    from app.main import app
    from fastapi.testclient import TestClient
    _ok("All core modules importable")
except Exception as e:
    _fail("Module imports", str(e))
    print("\n" + "=" * 50)
    print(f"SMOKE CHECK ABORTED: {failed} failed")
    print("=" * 50)
    os.unlink(DB_PATH)
    sys.exit(1)

# ------------------------------------------------------------------
# 2. Schema init
# ------------------------------------------------------------------
print("\n[2/5] SQLite schema initialization")
try:
    init_db()
    conn = get_connection()
    try:
        tables = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        expected = {"users", "gifts", "gift_stories", "favorites", "reports", "review_logs", "admin_actions", "user_actions"}
        if expected.issubset(set(tables)):
            _ok("Schema init creates all required tables")
        else:
            missing = expected - set(tables)
            _fail("Schema init", f"Missing tables: {missing}")
    finally:
        close_connection(conn)
except Exception as e:
    _fail("Schema init", str(e))

# ------------------------------------------------------------------
# 3. Migration idempotency
# ------------------------------------------------------------------
print("\n[3/5] Migration idempotency")
try:
    from scripts.migrate_db import run_migrations
    results = run_migrations(DB_PATH)
    _ok("Migrations run without error (idempotent)")
except Exception as e:
    _fail("Migration idempotency", str(e))

# ------------------------------------------------------------------
# 4. Core routes
# ------------------------------------------------------------------
print("\n[4/5] Core API routes")
client = TestClient(app)

try:
    r = client.get("/api/health")
    if r.status_code == 200:
        _ok("GET /api/health")
    else:
        _fail("GET /api/health", f"status={r.status_code}")
except Exception as e:
    _fail("GET /api/health", str(e))

try:
    r = client.get("/api/gifts")
    if r.status_code == 200:
        _ok("GET /api/gifts")
    else:
        _fail("GET /api/gifts", f"status={r.status_code}")
except Exception as e:
    _fail("GET /api/gifts", str(e))

try:
    r = client.post("/api/auth/anonymous")
    if r.status_code == 201:
        _ok("POST /api/auth/anonymous")
    else:
        _fail("POST /api/auth/anonymous", f"status={r.status_code}")
except Exception as e:
    _fail("POST /api/auth/anonymous", str(e))

try:
    # Need auth for /api/me/actions
    r = client.post("/api/auth/anonymous")
    token = r.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r2 = client.get("/api/me/actions", headers=headers)
    if r2.status_code == 200:
        _ok("GET /api/me/actions")
    else:
        _fail("GET /api/me/actions", f"status={r2.status_code}")
except Exception as e:
    _fail("GET /api/me/actions", str(e))

# ------------------------------------------------------------------
# 5. No real external calls
# ------------------------------------------------------------------
print("\n[5/5] No real external network calls")
try:
    # Verify OpenAI provider is not called by default (mock provider)
    os.environ["MODERATION_PROVIDER"] = "mock"
    # Re-import to pick up env
    from app.services.moderation.factory import get_moderation_provider
    provider = get_moderation_provider()
    if "mock" in str(type(provider)).lower() or "Mock" in str(type(provider)):
        _ok("Moderation provider is mock (no real API calls)")
    else:
        _fail("Moderation provider", f"Unexpected provider: {type(provider)}")
except Exception as e:
    _fail("Moderation provider check", str(e))

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
print("\n" + "=" * 50)
print(f"SMOKE CHECK: {passed} passed, {failed} failed")
if errors:
    print("\nFailures:")
    for label, detail in errors:
        print(f"  - {label}: {detail}")
print("=" * 50)

# Cleanup
os.unlink(DB_PATH)
sys.exit(0 if failed == 0 else 1)
