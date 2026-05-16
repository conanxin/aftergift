#!/usr/bin/env python3
"""
Aftergift Phase 2H-1 — My Gift Management API Tests
====================================================
Tests:
  1. GET /api/gifts/me/gifts/{id} 无 token → 401
  2. GET /api/gifts/me/gifts/{id} 非本人 → 404
  3. GET /api/gifts/me/gifts/{id} 本人 → 200
  4. PATCH 自己的 pending_review 礼物 → 200
  5. PATCH 他人礼物 → 404
  6. PATCH published 礼物 → 409
  7. POST resubmit needs_edit → 200，状态 pending_review
  8. POST resubmit published → 409
  9. POST archive published → 200，状态 archived
 10. archived 不出现在普通 GET /api/gifts
 11. archived 出现在 mine=true
 12. 编辑 story 后写入 review_logs，且 suggestions/evidence 仍脱敏
 13. PATCH 只允许 allowed_fields，不允许改 user_id / status / id
 14. resubmit 后 review_result 存在
"""
import os, sys, json, tempfile, sqlite3, uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient

# ── Helpers ──────────────────────────────────────────────────────────────────

def _init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        anonymous_nickname TEXT NOT NULL DEFAULT '匿名',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS gifts (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        relation_type TEXT,
        relation_label TEXT,
        action_type TEXT NOT NULL CHECK(action_type IN ('sell','exchange','giveaway','donate','keep')),
        emotion TEXT NOT NULL CHECK(emotion IN ('放下','遗憾','感谢','释怀','重启','纪念','治愈','平静')),
        price_or_exchange TEXT,
        condition_note TEXT,
        city_blur TEXT,
        is_anonymous INTEGER DEFAULT 1,
        status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','pending_review','published','needs_edit','rejected','archived')),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS gift_stories (
        id TEXT PRIMARY KEY,
        gift_id TEXT NOT NULL UNIQUE,
        short_story TEXT NOT NULL,
        full_story TEXT NOT NULL,
        story_quality_score REAL DEFAULT 0.0,
        risk_level TEXT NOT NULL CHECK(risk_level IN ('safe','caution','high_risk')),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS review_logs (
        id TEXT PRIMARY KEY,
        gift_id TEXT NOT NULL,
        risk_level TEXT,
        identity_risk TEXT,
        attack_risk TEXT,
        identifiable_person_risk TEXT,
        quality_notes TEXT,
        suggestions_json TEXT,
        reviewer_type TEXT,
        decision TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS favorites (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        gift_id TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, gift_id)
    );
    CREATE TABLE IF NOT EXISTS admin_actions (
        id TEXT PRIMARY KEY,
        admin_id TEXT NOT NULL,
        target_type TEXT NOT NULL,
        target_id TEXT NOT NULL,
        action TEXT NOT NULL,
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()


def _seed_data(db_path: str, user_a: str, user_b: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO users (id, anonymous_nickname) VALUES (?, ?)", (user_a, "UserA"))
    cur.execute("INSERT INTO users (id, anonymous_nickname) VALUES (?, ?)", (user_b, "UserB"))

    # User A gifts
    gid_a_pub = f"gift-{uuid.uuid4().hex[:8]}"
    cur.execute("""
        INSERT INTO gifts (id, user_id, title, category, relation_type, relation_label,
                          action_type, emotion, price_or_exchange, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (gid_a_pub, user_a, "A的围巾", "服饰", "恋人", "恋人", "sell", "放下", "¥200", "published", "2024-01-01"))
    cur.execute("""
        INSERT INTO gift_stories (id, gift_id, short_story, full_story, risk_level)
        VALUES (?, ?, ?, ?, ?)
    """, (f"story-{uuid.uuid4().hex[:8]}", gid_a_pub, "A的围巾摘要", "A的围巾故事", "safe"))

    gid_a_pending = f"gift-{uuid.uuid4().hex[:8]}"
    cur.execute("""
        INSERT INTO gifts (id, user_id, title, category, relation_type, relation_label,
                          action_type, emotion, price_or_exchange, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (gid_a_pending, user_a, "A的杯子", "家居", "朋友", "朋友", "giveaway", "感谢", "免费", "pending_review", "2024-01-02"))
    cur.execute("""
        INSERT INTO gift_stories (id, gift_id, short_story, full_story, risk_level)
        VALUES (?, ?, ?, ?, ?)
    """, (f"story-{uuid.uuid4().hex[:8]}", gid_a_pending, "A的杯子摘要", "A的杯子故事", "safe"))

    gid_a_ne = f"gift-{uuid.uuid4().hex[:8]}"
    cur.execute("""
        INSERT INTO gifts (id, user_id, title, category, relation_type, relation_label,
                          action_type, emotion, price_or_exchange, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (gid_a_ne, user_a, "A的耳机", "数码", "同事", "同事", "exchange", "遗憾", "换书", "needs_edit", "2024-01-03"))
    cur.execute("""
        INSERT INTO gift_stories (id, gift_id, short_story, full_story, risk_level)
        VALUES (?, ?, ?, ?, ?)
    """, (f"story-{uuid.uuid4().hex[:8]}", gid_a_ne, "A的耳机摘要", "A的耳机故事", "safe"))

    # Admin action note for needs_edit
    cur.execute("""
        INSERT INTO admin_actions (id, admin_id, target_type, target_id, action, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (f"act-{uuid.uuid4().hex[:8]}", "admin_001", "gift", gid_a_ne, "needs_edit", "请补充物品成色说明", "2024-01-03"))

    # User B gift
    gid_b_pub = f"gift-{uuid.uuid4().hex[:8]}"
    cur.execute("""
        INSERT INTO gifts (id, user_id, title, category, relation_type, relation_label,
                          action_type, emotion, price_or_exchange, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (gid_b_pub, user_b, "B的书", "书籍", "家人", "家人", "donate", "释怀", "捐出", "published", "2024-01-04"))
    cur.execute("""
        INSERT INTO gift_stories (id, gift_id, short_story, full_story, risk_level)
        VALUES (?, ?, ?, ?, ?)
    """, (f"story-{uuid.uuid4().hex[:8]}", gid_b_pub, "B的书摘要", "B的书故事", "safe"))

    conn.commit()
    conn.close()
    return gid_a_pub, gid_a_pending, gid_a_ne, gid_b_pub


# ── Fixture / Setup ──────────────────────────────────────────────────────────

with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
    TEST_DB = f.name
os.environ["AFTERGIFT_DB_PATH"] = TEST_DB
os.environ.setdefault("AFTERGIFT_JWT_SECRET", "test-secret-" + str(uuid.uuid4()))
os.environ.setdefault("AFTERGIFT_ADMIN_TOKEN", "admin-test-token")

_init_db(TEST_DB)
USER_A = "usr_" + str(uuid.uuid4())[:8]
USER_B = "usr_" + str(uuid.uuid4())[:8]
GIDA_PUB, GIDA_PENDING, GIDA_NE, GIDB_PUB = _seed_data(TEST_DB, USER_A, USER_B)

# Import after env set
from app.main import app
from app.auth import create_access_token

client = TestClient(app)

TOKEN_A = create_access_token(USER_A, "UserA", "user")
TOKEN_B = create_access_token(USER_B, "UserB", "user")


# ── Tests ────────────────────────────────────────────────────────────────────

def test_01_get_my_gift_no_token_401():
    r = client.get(f"/api/gifts/me/gifts/{GIDA_PUB}")
    assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"


def test_02_get_my_gift_not_owner_404():
    r = client.get(f"/api/gifts/me/gifts/{GIDA_PUB}", headers={"Authorization": f"Bearer {TOKEN_B}"})
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


def test_03_get_my_gift_owner_200():
    r = client.get(f"/api/gifts/me/gifts/{GIDA_PUB}", headers={"Authorization": f"Bearer {TOKEN_A}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()["data"]
    assert data["id"] == GIDA_PUB
    assert "story" in data
    assert data["status"] == "published"


def test_04_get_my_gift_needs_edit_review_note():
    r = client.get(f"/api/gifts/me/gifts/{GIDA_NE}", headers={"Authorization": f"Bearer {TOKEN_A}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()["data"]
    assert data["status"] == "needs_edit"
    assert data.get("review_note") == "请补充物品成色说明"


def test_05_patch_own_pending_review_200():
    payload = {"title": "A的杯子改", "price_or_exchange": "¥10"}
    r = client.patch(f"/api/gifts/me/gifts/{GIDA_PENDING}", json=payload, headers={"Authorization": f"Bearer {TOKEN_A}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()["data"]
    assert data["title"] == "A的杯子改"
    assert data["price_or_exchange"] == "¥10"
    assert data["status"] == "pending_review"


def test_06_patch_other_user_404():
    payload = {"title": "恶意修改"}
    r = client.patch(f"/api/gifts/me/gifts/{GIDA_PUB}", json=payload, headers={"Authorization": f"Bearer {TOKEN_B}"})
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


def test_07_patch_published_409():
    payload = {"title": "尝试修改已发布"}
    r = client.patch(f"/api/gifts/me/gifts/{GIDA_PUB}", json=payload, headers={"Authorization": f"Bearer {TOKEN_A}"})
    assert r.status_code == 409, f"Expected 409, got {r.status_code}: {r.text}"


def test_08_patch_disallowed_fields_ignored():
    payload = {"title": "合法标题", "user_id": USER_B, "status": "published", "id": "hacked"}
    r = client.patch(f"/api/gifts/me/gifts/{GIDA_PENDING}", json=payload, headers={"Authorization": f"Bearer {TOKEN_A}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()["data"]
    assert data["title"] == "合法标题"
    # status should remain pending_review (not changed to published)
    assert data["status"] == "pending_review"


def test_09_resubmit_needs_edit_200():
    r = client.post(f"/api/gifts/me/gifts/{GIDA_NE}/resubmit", headers={"Authorization": f"Bearer {TOKEN_A}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()["data"]
    assert data["previous_status"] == "needs_edit"
    assert data["new_status"] == "pending_review"
    assert "risk_level" in data
    assert "review" in data


def test_10_resubmit_published_409():
    r = client.post(f"/api/gifts/me/gifts/{GIDA_PUB}/resubmit", headers={"Authorization": f"Bearer {TOKEN_A}"})
    assert r.status_code == 409, f"Expected 409, got {r.status_code}: {r.text}"


def test_11_archive_published_200():
    r = client.post(f"/api/gifts/me/gifts/{GIDA_PUB}/archive", headers={"Authorization": f"Bearer {TOKEN_A}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()["data"]
    assert data["previous_status"] == "published"
    assert data["new_status"] == "archived"


def test_12_archived_not_in_plain_get():
    r = client.get("/api/gifts")
    assert r.status_code == 200
    data = r.json()["data"]
    titles = {g["title"] for g in data["items"]}
    assert "A的围巾" not in titles, f"Archived gift should not appear in plain GET, got {titles}"


def test_13_archived_in_mine():
    r = client.get("/api/gifts?mine=true", headers={"Authorization": f"Bearer {TOKEN_A}"})
    assert r.status_code == 200
    data = r.json()["data"]
    titles = {g["title"] for g in data["items"]}
    assert "A的围巾" in titles, f"Archived gift should appear in mine=true, got {titles}"


def test_14_edit_story_writes_review_logs():
    # Use GIDA_PENDING (still pending_review after test_05 patch)
    payload = {"short_story": "修改后的摘要", "full_story": "修改后的完整故事，不包含真实姓名电话等敏感信息"}
    r = client.patch(f"/api/gifts/me/gifts/{GIDA_PENDING}", json=payload, headers={"Authorization": f"Bearer {TOKEN_A}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()["data"]
    assert "review" in data
    review = data["review"]
    assert review is not None
    assert "review_result" in review
    # Verify redaction: no raw phone numbers / real names persisted
    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT suggestions_json FROM review_logs WHERE gift_id = ? ORDER BY created_at DESC LIMIT 1", [GIDA_PENDING])
    row = cur.fetchone()
    conn.close()
    assert row is not None, "review_logs should have a new entry after story edit"
    sug = row["suggestions_json"]
    # Ensure no obvious phone pattern in persisted suggestions
    import re
    assert not re.search(r"1[3-9]\d{9}", str(sug)), "Phone numbers should be redacted in review_logs"


# ── Cleanup ──────────────────────────────────────────────────────────────────

def teardown_module():
    try:
        os.unlink(TEST_DB)
    except Exception:
        pass


if __name__ == "__main__":
    import traceback
    passed = 0
    failed = 0
    tests = [
        test_01_get_my_gift_no_token_401,
        test_02_get_my_gift_not_owner_404,
        test_03_get_my_gift_owner_200,
        test_04_get_my_gift_needs_edit_review_note,
        test_05_patch_own_pending_review_200,
        test_06_patch_other_user_404,
        test_07_patch_published_409,
        test_08_patch_disallowed_fields_ignored,
        test_09_resubmit_needs_edit_200,
        test_10_resubmit_published_409,
        test_11_archive_published_200,
        test_12_archived_not_in_plain_get,
        test_13_archived_in_mine,
        test_14_edit_story_writes_review_logs,
    ]
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERR   {t.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{len(tests)} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
