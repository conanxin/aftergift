#!/usr/bin/env python3
"""
Aftergift Phase 2G-1 | Search API Tests
Tests for GET /api/gifts with search, filter, pagination, sort.
Run: python3 backend/tests/test_search_api.py
"""

import sys
import os
import sqlite3
import tempfile
import shutil

# Add backend/backend to path so 'from app import ...' works
# __file__ is backend/tests/test_search_api.py → dirname is backend/tests/
# .. goes to backend/ → then backend/ again points to backend/backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# ── Setup test environment BEFORE importing app modules ──────────────────────

# Create a temp directory for test DB
_test_db_dir = tempfile.mkdtemp(prefix="aftergift_test_")
_test_db_path = os.path.join(_test_db_dir, "test.db")

# Set env var before any app import
os.environ["AFTERGIFT_DB_PATH"] = _test_db_path

# Import after env is set
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_connection, close_connection, init_db

client = TestClient(app)

# ── Test DB setup ────────────────────────────────────────────────────────────

def _seed_test_data():
    """Insert sample gifts into the test DB."""
    conn = get_connection()

    # Insert sample gifts (use existing user-001 from seed data)
    # Use unique IDs to avoid collision with seed_data.sql
    samples = [
        ("gift-t001", "user-001", "旧台灯", "家居", "lover", "恋人", "sell", "平静",
         "50元", "", "北京", 1, "published", "2024-01-02 00:00:00", "2024-01-02 00:00:00"),
        ("gift-t002", "user-001", "围巾", "服饰", "friend", "朋友", "giveaway", "感谢",
         "免费", "", "上海", 1, "published", "2024-01-03 00:00:00", "2024-01-03 00:00:00"),
        ("gift-t003", "user-001", "手账本", "文具", "family", "家人", "keep", "纪念",
         "", "", "", 0, "published", "2024-01-04 00:00:00", "2024-01-04 00:00:00"),
        ("gift-t004", "user-001", "相机", "数码", "lover", "恋人", "exchange", "遗憾",
         "换书", "", "广州", 1, "published", "2024-01-05 00:00:00", "2024-01-05 00:00:00"),
        ("gift-t005", "user-001", "杯子", "家居", "colleague", "同事", "donate", "释怀",
         "", "", "深圳", 0, "published", "2024-01-06 00:00:00", "2024-01-06 00:00:00"),
        ("gift-t006", "user-001", "耳机", "数码", "friend", "朋友", "sell", "重启",
         "200元", "", "杭州", 1, "published", "2024-01-07 00:00:00", "2024-01-07 00:00:00"),
        ("gift-t007", "user-001", "戒指", "饰品", "lover", "恋人", "keep", "遗憾",
         "", "", "", 1, "published", "2024-01-08 00:00:00", "2024-01-08 00:00:00"),
        ("gift-t008", "user-001", "书", "书籍", "family", "家人", "giveaway", "感谢",
         "", "", "成都", 0, "published", "2024-01-09 00:00:00", "2024-01-09 00:00:00"),
        # Non-published gift (should NOT appear in search)
        ("gift-t009", "user-001", "秘密礼物", "其他", "lover", "恋人", "keep", "平静",
         "", "", "", 1, "pending_review", "2024-01-10 00:00:00", "2024-01-10 00:00:00"),
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
        ("story-t001", "gift-t001", "这盏灯陪我们度过了很多夜晚。", "完整故事：灯是在某个冬天买的。", 85, "safe", "2024-01-02 00:00:00"),
        ("story-t002", "gift-t002", "朋友织的围巾，很温暖。", "完整故事：围巾是手工织的。", 90, "safe", "2024-01-03 00:00:00"),
        ("story-t003", "gift-t003", "记录了很多家庭回忆。", "完整故事：手账本是母亲送的。", 88, "safe", "2024-01-04 00:00:00"),
        ("story-t004", "gift-t004", "相机记录了很多旅行。", "完整故事：相机是前任送的。", 82, "safe", "2024-01-05 00:00:00"),
        ("story-t005", "gift-t005", "杯子是离职时同事送的。", "完整故事：杯子上有公司logo。", 80, "safe", "2024-01-06 00:00:00"),
        ("story-t006", "gift-t006", "耳机音质很好，但不想用了。", "完整故事：耳机是朋友推荐的。", 85, "safe", "2024-01-07 00:00:00"),
        ("story-t007", "gift-t007", "戒指太紧了，戴不上。", "完整故事：戒指是订婚时买的。", 78, "safe", "2024-01-08 00:00:00"),
        ("story-t008", "gift-t008", "这本书读了很多遍。", "完整故事：书是父亲留下的。", 92, "safe", "2024-01-09 00:00:00"),
        ("story-t009", "gift-t009", "秘密故事。", "完整故事：秘密。", 70, "caution", "2024-01-10 00:00:00"),
    ]

    for s in stories:
        conn.execute("""
            INSERT INTO gift_stories (id, gift_id, short_story, full_story,
                                      story_quality_score, risk_level, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, s)

    conn.commit()
    close_connection(conn)


def _setup():
    """Initialize test DB with schema and seed data."""
    # Remove old test DB if exists
    if os.path.exists(_test_db_path):
        os.remove(_test_db_path)
    # Initialize schema
    init_db(drop_existing=False)
    # Seed test data
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


# ── Tests ────────────────────────────────────────────────────────────────────

def test_search_by_keyword():
    """1. GET /api/gifts?q=灯 → 返回匹配结果。"""
    resp = client.get("/api/gifts?q=灯")
    data = _unwrap(resp)
    items = data["items"]
    assert len(items) >= 1, f"Expected at least 1 result for '灯', got {len(items)}"
    titles = [i["title"] for i in items]
    assert "旧台灯" in titles, f"Expected '旧台灯' in results, got {titles}"
    print("PASS: test_search_by_keyword")


def test_search_no_results():
    """2. GET /api/gifts?q=不存在的词 → 返回空 items，但 200。"""
    resp = client.get("/api/gifts?q=不存在的词XYZ")
    data = _unwrap(resp)
    assert data["items"] == [], f"Expected empty items, got {data['items']}"
    assert data["total"] == 0, f"Expected total 0, got {data['total']}"
    print("PASS: test_search_no_results")


def test_filter_emotion():
    """3. emotion filter 正常。"""
    resp = client.get("/api/gifts?emotion=平静")
    data = _unwrap(resp)
    for item in data["items"]:
        assert item["emotion"] == "平静", f"Expected emotion '平静', got {item['emotion']}"
    print("PASS: test_filter_emotion")


def test_filter_action_type():
    """4. action_type filter 正常。"""
    resp = client.get("/api/gifts?action_type=sell")
    data = _unwrap(resp)
    for item in data["items"]:
        assert item["action_type"] == "sell", f"Expected action_type 'sell', got {item['action_type']}"
    print("PASS: test_filter_action_type")


def test_pagination():
    """5. page / limit 正常。"""
    resp = client.get("/api/gifts?page=1&limit=3")
    data = _unwrap(resp)
    assert len(data["items"]) <= 3, f"Expected <= 3 items, got {len(data['items'])}"
    assert data["page"] == 1
    assert data["limit"] == 3
    assert data["total_pages"] >= 1
    print("PASS: test_pagination")


def test_sort_order_whitelist():
    """6. sort/order 白名单正常。"""
    resp = client.get("/api/gifts?sort=title&order=asc")
    data = _unwrap(resp)
    assert len(data["items"]) > 0
    print("PASS: test_sort_order_whitelist")


def test_illegal_sort_rejected():
    """7. 非法 sort 不应执行 SQL 注入。"""
    resp = client.get("/api/gifts?sort=DROP+TABLE+gifts")
    data = _unwrap(resp)
    # Should fallback to default sort (created_at desc) and still return results
    assert len(data["items"]) >= 0
    # Verify table still exists by doing another query
    resp2 = client.get("/api/gifts")
    data2 = _unwrap(resp2)
    assert len(data2["items"]) >= 0
    print("PASS: test_illegal_sort_rejected")


def test_no_unpublished():
    """8. 搜索不会返回非 published 内容。"""
    resp = client.get("/api/gifts")
    data = _unwrap(resp)
    titles = [i["title"] for i in data["items"]]
    assert "秘密礼物" not in titles, f"Unpublished gift should not appear, got {titles}"
    print("PASS: test_no_unpublished")


def test_search_crosses_title_and_story():
    """9. q 同时搜索 gift title 和 story。"""
    # Search by story content
    resp = client.get("/api/gifts?q=手工织的")
    data = _unwrap(resp)
    titles = [i["title"] for i in data["items"]]
    assert "围巾" in titles, f"Expected '围巾' from story match, got {titles}"
    print("PASS: test_search_crosses_title_and_story")


def test_response_meta():
    """10. 返回 total/page/total_pages。"""
    resp = client.get("/api/gifts")
    data = _unwrap(resp)
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert "total_pages" in data
    assert "has_more" in data
    assert "filters" in data
    assert data["total"] >= 8  # We inserted 8 published gifts
    print("PASS: test_response_meta")


def test_combined_filter_and_search():
    """11. 组合搜索 + 筛选正常。"""
    resp = client.get("/api/gifts?q=朋友&action_type=giveaway")
    data = _unwrap(resp)
    for item in data["items"]:
        assert item["action_type"] == "giveaway"
    print("PASS: test_combined_filter_and_search")


def test_city_blur_filter():
    """12. city_blur 模糊筛选正常。"""
    resp = client.get("/api/gifts?city_blur=北京")
    data = _unwrap(resp)
    for item in data["items"]:
        assert "北京" in (item.get("city_blur") or ""), f"Expected city_blur containing '北京', got {item.get('city_blur')}"
    print("PASS: test_city_blur_filter")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _setup()
    try:
        tests = [
            test_search_by_keyword,
            test_search_no_results,
            test_filter_emotion,
            test_filter_action_type,
            test_pagination,
            test_sort_order_whitelist,
            test_illegal_sort_rejected,
            test_no_unpublished,
            test_search_crosses_title_and_story,
            test_response_meta,
            test_combined_filter_and_search,
            test_city_blur_filter,
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
        print("All search API tests PASSED.")
    finally:
        _teardown()
