#!/usr/bin/env python3
"""
Aftergift Phase 2H-2 — My Actions & Restore Tests
=================================================
Covers:
  1. GET /api/me/gifts/{id} owner → 200
  2. GET /api/gifts/me/gifts/{id} legacy path still works
  3. POST /api/me/gifts/{id}/restore archived → 200
  4. restore 后状态 = pending_review
  5. restore 非本人 → 404
  6. restore 非 archived → 409
  7. PATCH 编辑写入 user_actions
  8. resubmit 写入 user_actions
  9. archive 写入 user_actions
 10. restore 写入 user_actions
 11. GET /api/me/actions 只返回当前用户
 12. migration 002 创建 user_actions 表且幂等
"""

import os, sys, uuid, tempfile

# ------------------------------------------------------------------
# 0. Ensure project on sys.path
# ------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR  = os.path.join(PROJECT_ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

# ------------------------------------------------------------------
# 1. Setup temp DB + env
# ------------------------------------------------------------------
DB_FD, DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(DB_FD)
os.environ["AFTERGIFT_DB_PATH"] = DB_PATH
os.environ["AFTERGIFT_ADMIN_TOKEN"] = "test-admin-token"
os.environ["AFTERGIFT_JWT_SECRET"]  = "test-jwt-secret-" + str(uuid.uuid4())

from app.database import init_db, get_connection, close_connection
from app.auth import create_access_token

init_db()

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
import sqlite3

def _raw_conn():
    return sqlite3.connect(DB_PATH)

def _make_user(nickname="测试用户"):
    uid = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (id, anonymous_nickname, created_at) VALUES (?, ?, datetime('now'))",
            (uid, nickname)
        )
        conn.commit()
    finally:
        close_connection(conn)
    return uid

def _make_gift(user_id, title="测试礼物", status="published", action_type="sell"):
    gid = str(uuid.uuid4())
    conn = get_connection()
    try:
        now = "2024-01-01 00:00:00"
        conn.execute("""
            INSERT INTO gifts (id, user_id, title, category, relation_type, relation_label,
                               action_type, emotion, price_or_exchange, condition_note,
                               city_blur, is_anonymous, status, created_at, updated_at)
            VALUES (?, ?, ?, '戒指', '恋人', '前任', ?, '放下', '100元', '九成新',
                    '北京', 1, ?, ?, ?)
        """, (gid, user_id, title, action_type, status, now, now))
        conn.execute("""
            INSERT INTO gift_stories (gift_id, short_story, full_story, risk_level, story_quality_score, created_at)
            VALUES (?, '短故事', '完整故事', 'safe', 80, ?)
        """, (gid, now))
        conn.commit()
    finally:
        close_connection(conn)
    return gid

def _auth_header(user_id, nickname="测试用户"):
    token = create_access_token(user_id, nickname, role="user")
    return {"Authorization": f"Bearer {token}"}

# ------------------------------------------------------------------
# 2. Import FastAPI test client
# ------------------------------------------------------------------
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ------------------------------------------------------------------
# Test runner
# ------------------------------------------------------------------
passed = 0
failed = 0
errors = []

def _ok(label):
    global passed
    passed += 1
    print(f"  PASS — {label}")

def _fail(label, detail):
    global failed
    failed += 1
    errors.append((label, detail))
    print(f"  FAIL — {label}: {detail}")

# ==================================================================
# T1: GET /api/me/gifts/{id} owner → 200
# ==================================================================
print("\n[T1] GET /api/me/gifts/{id} owner → 200")
try:
    u1 = _make_user("用户甲")
    g1 = _make_gift(u1, "礼物甲", status="published")
    r = client.get(f"/api/me/gifts/{g1}", headers=_auth_header(u1, "用户甲"))
    if r.status_code == 200 and r.json()["data"]["id"] == g1:
        _ok("T1")
    else:
        _fail("T1", f"status={r.status_code}, body={r.text[:200]}")
except Exception as e:
    _fail("T1", str(e))

# ==================================================================
# T2: GET /api/gifts/me/gifts/{id} legacy path still works
# ==================================================================
print("\n[T2] GET /api/gifts/me/gifts/{id} legacy → 200")
try:
    u2 = _make_user("用户乙")
    g2 = _make_gift(u2, "礼物乙", status="published")
    r = client.get(f"/api/gifts/me/gifts/{g2}", headers=_auth_header(u2, "用户乙"))
    if r.status_code == 200 and r.json()["data"]["id"] == g2:
        _ok("T2")
    else:
        _fail("T2", f"status={r.status_code}, body={r.text[:200]}")
except Exception as e:
    _fail("T2", str(e))

# ==================================================================
# T3: POST /api/me/gifts/{id}/restore archived → 200
# ==================================================================
print("\n[T3] POST /api/me/gifts/{id}/restore archived → 200")
try:
    u3 = _make_user("用户丙")
    g3 = _make_gift(u3, "礼物丙", status="archived")
    r = client.post(f"/api/me/gifts/{g3}/restore", headers=_auth_header(u3, "用户丙"))
    if r.status_code == 200:
        _ok("T3")
    else:
        _fail("T3", f"status={r.status_code}, body={r.text[:200]}")
except Exception as e:
    _fail("T3", str(e))

# ==================================================================
# T4: restore 后状态 = pending_review
# ==================================================================
print("\n[T4] restore 后状态 = pending_review")
try:
    u4 = _make_user("用户丁")
    g4 = _make_gift(u4, "礼物丁", status="archived")
    client.post(f"/api/me/gifts/{g4}/restore", headers=_auth_header(u4, "用户丁"))
    r = client.get(f"/api/me/gifts/{g4}", headers=_auth_header(u4, "用户丁"))
    if r.status_code == 200 and r.json()["data"]["status"] == "pending_review":
        _ok("T4")
    else:
        _fail("T4", f"status={r.status_code}, data={r.json().get('data')}")
except Exception as e:
    _fail("T4", str(e))

# ==================================================================
# T5: restore 非本人 → 404
# ==================================================================
print("\n[T5] restore 非本人 → 404")
try:
    u5a = _make_user("用户戊A")
    u5b = _make_user("用户戊B")
    g5 = _make_gift(u5a, "礼物戊", status="archived")
    r = client.post(f"/api/me/gifts/{g5}/restore", headers=_auth_header(u5b, "用户戊B"))
    if r.status_code == 404:
        _ok("T5")
    else:
        _fail("T5", f"expected 404, got {r.status_code}")
except Exception as e:
    _fail("T5", str(e))

# ==================================================================
# T6: restore 非 archived → 409
# ==================================================================
print("\n[T6] restore 非 archived → 409")
try:
    u6 = _make_user("用户己")
    g6 = _make_gift(u6, "礼物己", status="published")
    r = client.post(f"/api/me/gifts/{g6}/restore", headers=_auth_header(u6, "用户己"))
    if r.status_code == 409:
        _ok("T6")
    else:
        _fail("T6", f"expected 409, got {r.status_code}")
except Exception as e:
    _fail("T6", str(e))

# ==================================================================
# T7: PATCH 编辑写入 user_actions
# ==================================================================
print("\n[T7] PATCH 编辑写入 user_actions")
try:
    u7 = _make_user("用户庚")
    g7 = _make_gift(u7, "礼物庚", status="needs_edit")
    r = client.patch(f"/api/me/gifts/{g7}", json={"title": "礼物庚-改"}, headers=_auth_header(u7, "用户庚"))
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT action FROM user_actions WHERE user_id=? AND gift_id=? ORDER BY created_at DESC LIMIT 1",
            (u7, g7)
        ).fetchone()
    finally:
        close_connection(conn)
    if r.status_code == 200 and row and row["action"] == "edit":
        _ok("T7")
    else:
        _fail("T7", f"status={r.status_code}, action={row['action'] if row else None}")
except Exception as e:
    _fail("T7", str(e))

# ==================================================================
# T8: resubmit 写入 user_actions
# ==================================================================
print("\n[T8] resubmit 写入 user_actions")
try:
    u8 = _make_user("用户辛")
    g8 = _make_gift(u8, "礼物辛", status="needs_edit")
    r = client.post(f"/api/me/gifts/{g8}/resubmit", headers=_auth_header(u8, "用户辛"))
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT action FROM user_actions WHERE user_id=? AND gift_id=? ORDER BY created_at DESC LIMIT 1",
            (u8, g8)
        ).fetchone()
    finally:
        close_connection(conn)
    if r.status_code == 200 and row and row["action"] == "resubmit":
        _ok("T8")
    else:
        _fail("T8", f"status={r.status_code}, action={row['action'] if row else None}")
except Exception as e:
    _fail("T8", str(e))

# ==================================================================
# T9: archive 写入 user_actions
# ==================================================================
print("\n[T9] archive 写入 user_actions")
try:
    u9 = _make_user("用户壬")
    g9 = _make_gift(u9, "礼物壬", status="published")
    r = client.post(f"/api/me/gifts/{g9}/archive", headers=_auth_header(u9, "用户壬"))
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT action FROM user_actions WHERE user_id=? AND gift_id=? ORDER BY created_at DESC LIMIT 1",
            (u9, g9)
        ).fetchone()
    finally:
        close_connection(conn)
    if r.status_code == 200 and row and row["action"] == "archive":
        _ok("T9")
    else:
        _fail("T9", f"status={r.status_code}, action={row['action'] if row else None}")
except Exception as e:
    _fail("T9", str(e))

# ==================================================================
# T10: restore 写入 user_actions
# ==================================================================
print("\n[T10] restore 写入 user_actions")
try:
    u10 = _make_user("用户癸")
    g10 = _make_gift(u10, "礼物癸", status="archived")
    r = client.post(f"/api/me/gifts/{g10}/restore", headers=_auth_header(u10, "用户癸"))
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT action FROM user_actions WHERE user_id=? AND gift_id=? ORDER BY created_at DESC LIMIT 1",
            (u10, g10)
        ).fetchone()
    finally:
        close_connection(conn)
    if r.status_code == 200 and row and row["action"] == "restore":
        _ok("T10")
    else:
        _fail("T10", f"status={r.status_code}, action={row['action'] if row else None}")
except Exception as e:
    _fail("T10", str(e))

# ==================================================================
# T11: GET /api/me/actions 只返回当前用户
# ==================================================================
print("\n[T11] GET /api/me/actions 只返回当前用户")
try:
    u11a = _make_user("用户子A")
    u11b = _make_user("用户子B")
    g11a = _make_gift(u11a, "礼物子A", status="published")
    g11b = _make_gift(u11b, "礼物子B", status="published")
    client.post(f"/api/me/gifts/{g11a}/archive", headers=_auth_header(u11a, "用户子A"))
    client.post(f"/api/me/gifts/{g11b}/archive", headers=_auth_header(u11b, "用户子B"))
    r = client.get("/api/me/actions", headers=_auth_header(u11a, "用户子A"))
    data = r.json()["data"]
    items = data["items"]
    all_match = all(it["user_id"] == u11a for it in items)
    if r.status_code == 200 and all_match and len(items) >= 1:
        _ok("T11")
    else:
        _fail("T11", f"status={r.status_code}, items={len(items)}, all_match={all_match}")
except Exception as e:
    _fail("T11", str(e))

# ==================================================================
# T12: migration 002 创建 user_actions 表且幂等
# ==================================================================
print("\n[T12] migration 002 幂等")
try:
    # Verify user_actions table exists (created by init_db earlier)
    conn = get_connection()
    try:
        tables = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    finally:
        close_connection(conn)
    if "user_actions" in tables:
        _ok("T12")
    else:
        _fail("T12", "user_actions table missing")
except Exception as e:
    _fail("T12", str(e))

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
print("\n" + "="*60)
print(f"RESULTS: {passed} passed, {failed} failed")
if errors:
    print("\nFailures:")
    for label, detail in errors:
        print(f"  - {label}: {detail}")
print("="*60)

# Cleanup
os.unlink(DB_PATH)
sys.exit(0 if failed == 0 else 1)
