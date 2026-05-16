#!/usr/bin/env python3
"""
Aftergift Phase 2G-2 — My Gifts / My Favorites API Tests
=============================================================
Tests:
  1. mine=true without token → 401
  2. mine=true with valid token → 200
  3. mine=true returns user's pending_review + published
  4. mine=true does NOT return other user's gifts
  5. favorites_of=me without token → 401
  6. favorites_of=me with valid token → 200
  7. favorites_of=me returns user's favorited gifts
  8. favorites_of=me does NOT return other user's favorites
  9. plain GET /api/gifts without token → 200
 10. plain GET /api/gifts does NOT return unpublished
 11. mine + q search works together
 12. is_mine / is_favorited fields correctness
"""
import os, sys, json, tempfile, sqlite3, uuid

# Ensure app package is importable
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
    CREATE TABLE IF NOT EXISTS favorites (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        gift_id TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, gift_id)
    );
    """)
    conn.commit()
    conn.close()


def _seed_data(db_path: str, user_a: str, user_b: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Users
    cur.execute("INSERT INTO users (id, anonymous_nickname) VALUES (?, ?)", (user_a, "UserA"))
    cur.execute("INSERT INTO users (id, anonymous_nickname) VALUES (?, ?)", (user_b, "UserB"))
    # Gifts for user_a
    gid_a_pub = f"gift-{uuid.uuid4().hex[:8]}"
    cur.execute("""
        INSERT INTO gifts (id, user_id, title, category, relation_type, relation_label,
                          action_type, emotion, price_or_exchange, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (gid_a_pub, user_a, "A的戒指", "首饰", "恋人", "恋人", "sell", "放下", "¥500", "published", "2024-01-01"))
    cur.execute("""
        INSERT INTO gift_stories (id, gift_id, short_story, full_story, risk_level)
        VALUES (?, ?, ?, ?, ?)
    """, (f"story-{uuid.uuid4().hex[:8]}", gid_a_pub, "A的戒指摘要", "A的戒指故事", "safe"))

    gid_a_pending = f"gift-{uuid.uuid4().hex[:8]}"
    cur.execute("""
        INSERT INTO gifts (id, user_id, title, category, relation_type, relation_label,
                          action_type, emotion, price_or_exchange, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (gid_a_pending, user_a, "A的台灯", "家居", "朋友", "朋友", "giveaway", "感谢", "免费", "pending_review", "2024-01-02"))
    cur.execute("""
        INSERT INTO gift_stories (id, gift_id, short_story, full_story, risk_level)
        VALUES (?, ?, ?, ?, ?)
    """, (f"story-{uuid.uuid4().hex[:8]}", gid_a_pending, "A的台灯摘要", "A的台灯故事", "safe"))

    # Gifts for user_b
    gid_b_pub = f"gift-{uuid.uuid4().hex[:8]}"
    cur.execute("""
        INSERT INTO gifts (id, user_id, title, category, relation_type, relation_label,
                          action_type, emotion, price_or_exchange, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (gid_b_pub, user_b, "B的书", "书籍", "同事", "同事", "exchange", "遗憾", "换一本", "published", "2024-01-03"))
    cur.execute("""
        INSERT INTO gift_stories (id, gift_id, short_story, full_story, risk_level)
        VALUES (?, ?, ?, ?, ?)
    """, (f"story-{uuid.uuid4().hex[:8]}", gid_b_pub, "B的书摘要", "B的书故事", "safe"))

    gid_b_pending = f"gift-{uuid.uuid4().hex[:8]}"
    cur.execute("""
        INSERT INTO gifts (id, user_id, title, category, relation_type, relation_label,
                          action_type, emotion, price_or_exchange, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (gid_b_pending, user_b, "B的耳机", "数码", "恋人", "恋人", "sell", "释怀", "¥200", "pending_review", "2024-01-04"))
    cur.execute("""
        INSERT INTO gift_stories (id, gift_id, short_story, full_story, risk_level)
        VALUES (?, ?, ?, ?, ?)
    """, (f"story-{uuid.uuid4().hex[:8]}", gid_b_pending, "B的耳机摘要", "B的耳机故事", "safe"))

    # Favorites: user_a favorites user_b's published gift
    cur.execute("INSERT INTO favorites (id, user_id, gift_id) VALUES (?, ?, ?)",
                (f"fav-{uuid.uuid4().hex[:8]}", user_a, gid_b_pub))
    # Favorites: user_b favorites user_a's published gift
    cur.execute("INSERT INTO favorites (id, user_id, gift_id) VALUES (?, ?, ?)",
                (f"fav-{uuid.uuid4().hex[:8]}", user_b, gid_a_pub))
    conn.commit()
    conn.close()
    return gid_a_pub, gid_a_pending, gid_b_pub


# ── Fixture / Setup ──────────────────────────────────────────────────────────

# We need to set env before importing main so config picks it up
with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
    TEST_DB = f.name
os.environ["AFTERGIFT_DB_PATH"] = TEST_DB
os.environ.setdefault("AFTERGIFT_JWT_SECRET", "test-secret-" + str(uuid.uuid4()))
os.environ.setdefault("AFTERGIFT_ADMIN_TOKEN", "admin-test-token")

_init_db(TEST_DB)
USER_A = "usr_" + str(uuid.uuid4())[:8]
USER_B = "usr_" + str(uuid.uuid4())[:8]
GIDA, GIDA_P, GIDB = _seed_data(TEST_DB, USER_A, USER_B)

# Import after env set
from app.main import app
from app.auth import create_access_token

client = TestClient(app)

TOKEN_A = create_access_token(USER_A, "UserA")
TOKEN_B = create_access_token(USER_B, "UserB")


# ── Tests ────────────────────────────────────────────────────────────────────

def test_01_mine_no_token_401():
    r = client.get("/api/gifts?mine=true")
    assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"


def test_02_mine_with_token_200():
    r = client.get("/api/gifts?mine=true", headers={"Authorization": f"Bearer {TOKEN_A}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()["data"]
    assert "items" in data


def test_03_mine_returns_user_pending_and_published():
    r = client.get("/api/gifts?mine=true", headers={"Authorization": f"Bearer {TOKEN_A}"})
    data = r.json()["data"]
    names = {g["title"] for g in data["items"]}
    assert "A的戒指" in names, f"Expected published gift, got {names}"
    assert "A的台灯" in names, f"Expected pending_review gift, got {names}"


def test_04_mine_not_other_user():
    r = client.get("/api/gifts?mine=true", headers={"Authorization": f"Bearer {TOKEN_A}"})
    data = r.json()["data"]
    names = {g["title"] for g in data["items"]}
    assert "B的书" not in names, f"Should not contain other user's gift, got {names}"
    assert "B的耳机" not in names, f"Should not contain other user's gift, got {names}"


def test_05_favorites_of_me_no_token_401():
    r = client.get("/api/gifts?favorites_of=me")
    assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"


def test_06_favorites_of_me_with_token_200():
    r = client.get("/api/gifts?favorites_of=me", headers={"Authorization": f"Bearer {TOKEN_A}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()["data"]
    assert "items" in data


def test_07_favorites_returns_user_favorites():
    r = client.get("/api/gifts?favorites_of=me", headers={"Authorization": f"Bearer {TOKEN_A}"})
    data = r.json()["data"]
    names = {g["title"] for g in data["items"]}
    assert "B的书" in names, f"Expected favorited gift, got {names}"


def test_08_favorites_not_other_user_favorites():
    r = client.get("/api/gifts?favorites_of=me", headers={"Authorization": f"Bearer {TOKEN_A}"})
    data = r.json()["data"]
    names = {g["title"] for g in data["items"]}
    # User A did not favorite A's own published gift (user B did)
    assert "A的戒指" not in names, f"Should not contain non-favorited gift, got {names}"


def test_09_plain_get_no_token_200():
    r = client.get("/api/gifts")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


def test_10_plain_get_no_unpublished():
    r = client.get("/api/gifts")
    data = r.json()["data"]
    names = {g["title"] for g in data["items"]}
    assert "A的台灯" not in names, f"Plain GET should not show pending_review, got {names}"
    assert "B的耳机" not in names, f"Plain GET should not show pending_review, got {names}"


def test_11_mine_with_q_search():
    r = client.get("/api/gifts?mine=true&q=台灯", headers={"Authorization": f"Bearer {TOKEN_A}"})
    data = r.json()["data"]
    names = [g["title"] for g in data["items"]]
    assert "A的台灯" in names, f"Expected search match, got {names}"
    assert "A的戒指" not in names, f"Expected no match for ring, got {names}"


def test_12_is_mine_and_is_favorited_fields():
    # User A viewing plain list with token
    r = client.get("/api/gifts", headers={"Authorization": f"Bearer {TOKEN_A}"})
    data = r.json()["data"]
    for g in data["items"]:
        assert "is_mine" in g, f"Missing is_mine in {g['title']}"
        assert "is_favorited" in g, f"Missing is_favorited in {g['title']}"
    # A's own gift
    a_gift = next((g for g in data["items"] if g["title"] == "A的戒指"), None)
    assert a_gift is not None
    assert a_gift["is_mine"] is True
    # B's gift that A favorited
    b_gift = next((g for g in data["items"] if g["title"] == "B的书"), None)
    assert b_gift is not None
    assert b_gift["is_favorited"] is True
    assert b_gift["is_mine"] is False


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
        test_01_mine_no_token_401,
        test_02_mine_with_token_200,
        test_03_mine_returns_user_pending_and_published,
        test_04_mine_not_other_user,
        test_05_favorites_of_me_no_token_401,
        test_06_favorites_of_me_with_token_200,
        test_07_favorites_returns_user_favorites,
        test_08_favorites_not_other_user_favorites,
        test_09_plain_get_no_token_200,
        test_10_plain_get_no_unpublished,
        test_11_mine_with_q_search,
        test_12_is_mine_and_is_favorited_fields,
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
