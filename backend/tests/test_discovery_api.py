#!/usr/bin/env python3
"""
Aftergift Phase 2I-1 | Discovery API Tests
Tests for GET /api/gifts/discovery and GET /api/gifts/{id}/similar.
Run: python3 backend/tests/test_discovery_api.py
"""

import sys
import os
import sqlite3
import tempfile
import shutil

# Add backend/backend to path so 'from app import ...' works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# ── Setup test environment BEFORE importing app modules ──────────────────────
_test_db_dir = tempfile.mkdtemp(prefix="aftergift_test_")
_test_db_path = os.path.join(_test_db_dir, "test.db")
os.environ["AFTERGIFT_DB_PATH"] = _test_db_path

from fastapi.testclient import TestClient
from app.main import app
from app.database import get_connection, close_connection, init_db

client = TestClient(app)

# ── Test DB setup ────────────────────────────────────────────────────────────

def _seed_test_data():
    """Insert sample gifts into the test DB."""
    conn = get_connection()

    # Insert sample gifts with varied moods, relations, timestamps
    samples = [
        ("gift-d001", "user-001", "旧台灯", "家居", "lover", "恋人", "sell", "平静",
         "50元", "", "北京", 1, "published", "2024-06-01 10:00:00", "2024-06-01 10:00:00"),
        ("gift-d002", "user-001", "围巾", "服饰", "friend", "朋友", "giveaway", "感谢",
         "免费", "", "上海", 1, "published", "2024-06-02 10:00:00", "2024-06-02 10:00:00"),
        ("gift-d003", "user-001", "手账本", "文具", "family", "家人", "keep", "纪念",
         "", "", "", 0, "published", "2024-06-03 10:00:00", "2024-06-03 10:00:00"),
        ("gift-d004", "user-001", "相机", "数码", "lover", "恋人", "exchange", "遗憾",
         "换书", "", "广州", 1, "published", "2024-06-04 10:00:00", "2024-06-04 10:00:00"),
        ("gift-d005", "user-001", "杯子", "家居", "colleague", "同事", "donate", "释怀",
         "", "", "深圳", 0, "published", "2024-06-05 10:00:00", "2024-06-05 10:00:00"),
        ("gift-d006", "user-001", "耳机", "数码", "friend", "朋友", "sell", "重启",
         "200元", "", "杭州", 1, "published", "2024-06-06 10:00:00", "2024-06-06 10:00:00"),
        ("gift-d007", "user-001", "戒指", "饰品", "lover", "恋人", "keep", "遗憾",
         "", "", "", 1, "published", "2024-06-07 10:00:00", "2024-06-07 10:00:00"),
        ("gift-d008", "user-001", "书", "书籍", "family", "家人", "giveaway", "感谢",
         "", "", "成都", 0, "published", "2024-06-08 10:00:00", "2024-06-08 10:00:00"),
        # Non-published gift (should NOT appear in discovery)
        ("gift-d009", "user-001", "秘密礼物", "其他", "lover", "恋人", "keep", "平静",
         "", "", "", 1, "pending_review", "2024-06-09 10:00:00", "2024-06-09 10:00:00"),
    ]

    for s in samples:
        conn.execute("""
            INSERT INTO gifts (id, user_id, title, category, relation_type, relation_label,
                               action_type, emotion, price_or_exchange, condition_note,
                               city_blur, is_anonymous, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, s)

    # Insert stories
    stories = [
        ("story-d001", "gift-d001", "这盏灯陪我们度过了很多夜晚。", "完整故事：灯是在某个冬天买的。", 85, "safe", "2024-06-01 10:00:00"),
        ("story-d002", "gift-d002", "朋友织的围巾，很温暖。", "完整故事：围巾是手工织的。", 90, "safe", "2024-06-02 10:00:00"),
        ("story-d003", "gift-d003", "记录了很多家庭回忆。", "完整故事：手账本是母亲送的。", 88, "safe", "2024-06-03 10:00:00"),
        ("story-d004", "gift-d004", "相机记录了很多旅行。", "完整故事：相机是前任送的。", 82, "safe", "2024-06-04 10:00:00"),
        ("story-d005", "gift-d005", "杯子是离职时同事送的。", "完整故事：杯子上有公司logo。", 80, "safe", "2024-06-05 10:00:00"),
        ("story-d006", "gift-d006", "耳机音质很好，但不想用了。", "完整故事：耳机是朋友推荐的。", 85, "safe", "2024-06-06 10:00:00"),
        ("story-d007", "gift-d007", "戒指太紧了，戴不上。", "完整故事：戒指是订婚时买的。", 78, "safe", "2024-06-07 10:00:00"),
        ("story-d008", "gift-d008", "这本书读了很多遍。", "完整故事：书是父亲留下的。", 92, "safe", "2024-06-08 10:00:00"),
        ("story-d009", "gift-d009", "秘密故事。", "完整故事：秘密。", 70, "caution", "2024-06-09 10:00:00"),
    ]

    for s in stories:
        conn.execute("""
            INSERT INTO gift_stories (id, gift_id, short_story, full_story,
                                      story_quality_score, risk_level, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, s)

    # Insert favorites to test popular rail
    # gift-d002 (围巾) gets 3 favorites
    # gift-d001 (旧台灯) gets 2 favorites
    # gift-d004 (相机) gets 1 favorite
    favorites = [
        ("fav-d001", "user-002", "gift-d002", "2024-06-10 10:00:00"),
        ("fav-d002", "user-003", "gift-d002", "2024-06-10 11:00:00"),
        ("fav-d003", "user-004", "gift-d002", "2024-06-10 12:00:00"),
        ("fav-d004", "user-002", "gift-d001", "2024-06-10 10:00:00"),
        ("fav-d005", "user-003", "gift-d001", "2024-06-10 11:00:00"),
        ("fav-d006", "user-002", "gift-d004", "2024-06-10 10:00:00"),
    ]

    for f in favorites:
        conn.execute("""
            INSERT INTO favorites (id, user_id, gift_id, created_at)
            VALUES (?, ?, ?, ?)
        """, f)

    conn.commit()
    close_connection(conn)


def _setup():
    """Initialize test DB with schema and seed data."""
    if os.path.exists(_test_db_path):
        os.remove(_test_db_path)
    init_db(drop_existing=False)
    _seed_test_data()


def _teardown():
    """Clean up test DB."""
    if os.path.exists(_test_db_path):
        os.remove(_test_db_path)
    shutil.rmtree(_test_db_dir, ignore_errors=True)


# ── Test helpers ─────────────────────────────────────────────────────────────

def _unwrap(resp):
    """Unwrap FastAPI standard response {code, message, data}."""
    data = resp.json()
    assert data.get("code") == 200, f"Expected code 200, got {data.get('code')}: {data.get('message')}"
    return data.get("data", {})


# ── Discovery API Tests ─────────────────────────────────────────────────────

def test_discovery_latest():
    """1. GET /api/gifts/discovery?rail=latest → 200."""
    resp = client.get("/api/gifts/discovery?rail=latest")
    data = _unwrap(resp)
    items = data.get("items", [])
    assert len(items) > 0, "Expected items in latest rail"
    print("PASS: test_discovery_latest")


def test_discovery_latest_only_published():
    """2. latest 只返回 published 状态。"""
    resp = client.get("/api/gifts/discovery?rail=latest")
    data = _unwrap(resp)
    items = data.get("items", [])
    for item in items:
        assert item.get("status") == "published", f"Expected published, got {item.get('status')}"
    # Secret gift should not appear
    titles = [i.get("title") for i in items]
    assert "秘密礼物" not in titles, "Unpublished gift should not appear in discovery"
    print("PASS: test_discovery_latest_only_published")


def test_discovery_popular_sorted():
    """3. popular 按 favorite_count 排序。"""
    resp = client.get("/api/gifts/discovery?rail=popular")
    data = _unwrap(resp)
    items = data.get("items", [])
    assert len(items) > 0, "Expected items in popular rail"
    # Check that favorite_count exists
    for item in items:
        assert "favorite_count" in item, "Expected favorite_count field"
    # Verify descending order
    counts = [i.get("favorite_count", 0) for i in items]
    for i in range(len(counts) - 1):
        assert counts[i] >= counts[i + 1], f"Expected descending favorite_count, got {counts}"
    # Top item should be 围巾 with 3 favorites
    assert items[0].get("title") == "围巾", f"Expected '围巾' as most popular, got {items[0].get('title')}"
    print("PASS: test_discovery_popular_sorted")


def test_discovery_all_rails():
    """4. rail=all 返回 latest/popular/gentle 三个轨道。"""
    resp = client.get("/api/gifts/discovery?rail=all")
    data = _unwrap(resp)
    # API returns {"rails": {"latest": [...], "popular": [...], "gentle": [...]}}
    rails = data.get("rails", {})
    assert isinstance(rails, dict), f"Expected rails to be dict, got {type(rails)}"
    assert "latest" in rails, "Expected 'latest' rail"
    assert "popular" in rails, "Expected 'popular' rail"
    assert "gentle" in rails, "Expected 'gentle' rail"
    print("PASS: test_discovery_all_rails")


def test_discovery_invalid_rail():
    """5. 非法 rail → 400."""
    resp = client.get("/api/gifts/discovery?rail=invalid")
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    print("PASS: test_discovery_invalid_rail")


def test_discovery_limit_max():
    """6. limit 最大值限制（默认 20，不应超过）。"""
    resp = client.get("/api/gifts/discovery?rail=latest&limit=20")
    data = _unwrap(resp)
    items = data.get("items", [])
    assert len(items) <= 20, f"Expected <= 20 items, got {len(items)}"
    print("PASS: test_discovery_limit_max")


# ── Similar Stories API Tests ────────────────────────────────────────────────

def test_similar_basic():
    """7. GET /api/gifts/{id}/similar → 200."""
    resp = client.get("/api/gifts/gift-d001/similar")
    data = _unwrap(resp)
    items = data.get("items", [])
    assert isinstance(items, list), "Expected items to be a list"
    print("PASS: test_similar_basic")


def test_similar_excludes_self():
    """8. similar 不返回当前 gift。"""
    resp = client.get("/api/gifts/gift-d001/similar")
    data = _unwrap(resp)
    items = data.get("items", [])
    ids = [i.get("id") for i in items]
    assert "gift-d001" not in ids, "Similar should not include the target gift itself"
    print("PASS: test_similar_excludes_self")


def test_similar_no_unpublished():
    """9. similar 不返回 unpublished。"""
    resp = client.get("/api/gifts/gift-d001/similar")
    data = _unwrap(resp)
    items = data.get("items", [])
    for item in items:
        assert item.get("status") == "published", f"Expected published, got {item.get('status')}"
    # Secret gift should not appear
    titles = [i.get("title") for i in items]
    assert "秘密礼物" not in titles, "Unpublished gift should not appear in similar"
    print("PASS: test_similar_no_unpublished")


def test_similar_score_sorted():
    """10. similarity_score 正确排序（降序）。"""
    resp = client.get("/api/gifts/gift-d001/similar")
    data = _unwrap(resp)
    items = data.get("items", [])
    if len(items) >= 2:
        scores = [i.get("similarity_score", 0) for i in items]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], f"Expected descending scores, got {scores}"
    print("PASS: test_similar_score_sorted")


def test_similar_matched_reasons():
    """11. matched_reason 存在。"""
    resp = client.get("/api/gifts/gift-d001/similar")
    data = _unwrap(resp)
    items = data.get("items", [])
    for item in items:
        assert "matched_reasons" in item, "Expected matched_reasons field"
        assert isinstance(item["matched_reasons"], list), "matched_reasons should be a list"
    print("PASS: test_similar_matched_reasons")


def test_list_has_favorite_count():
    """12. GET /api/gifts 返回 favorite_count 字段。"""
    resp = client.get("/api/gifts")
    data = _unwrap(resp)
    items = data.get("items", [])
    assert len(items) > 0, "Expected items in list"
    for item in items:
        assert "favorite_count" in item, "Expected favorite_count field in list items"
    # Verify counts match seeded favorites
    scarf = next((i for i in items if i.get("title") == "围巾"), None)
    if scarf:
        assert scarf.get("favorite_count") == 3, f"Expected 3 favorites for 围巾, got {scarf.get('favorite_count')}"
    print("PASS: test_list_has_favorite_count")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _setup()
    try:
        tests = [
            test_discovery_latest,
            test_discovery_latest_only_published,
            test_discovery_popular_sorted,
            test_discovery_all_rails,
            test_discovery_invalid_rail,
            test_discovery_limit_max,
            test_similar_basic,
            test_similar_excludes_self,
            test_similar_no_unpublished,
            test_similar_score_sorted,
            test_similar_matched_reasons,
            test_list_has_favorite_count,
        ]
        passed = 0
        failed = 0
        for t in tests:
            try:
                t()
                passed += 1
            except Exception as e:
                failed += 1
                print(f"FAIL: {t.__name__}: {e}")
        print(f"\n{'='*50}")
        print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
        if failed > 0:
            sys.exit(1)
        print("All discovery API tests PASSED.")
    finally:
        _teardown()
