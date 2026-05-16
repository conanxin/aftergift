#!/usr/bin/env python3
"""
Aftergift Phase 2J-1 | Favorites API Contract Tests
Tests for POST/DELETE /api/gifts/{id}/favorite and related fields.

Run: python3 backend/tests/test_favorites_api.py
"""

import sys
import os
import sqlite3
import tempfile
import shutil

# Add backend/backend to path so 'from app import ...' works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# ── Setup test environment BEFORE importing app modules ──────────────────────
_test_db_dir = tempfile.mkdtemp(prefix="aftergift_fav_test_")
_test_db_path = os.path.join(_test_db_dir, "test.db")
os.environ["AFTERGIFT_DB_PATH"] = _test_db_path

from fastapi.testclient import TestClient
from app.main import app
from app.database import get_connection, close_connection, init_db

client = TestClient(app)

# ── Test DB setup ──────────────────────────────────────────────────────────

def _seed_test_data():
    conn = get_connection()

    # Two users: user-001 (owner of gift), user-002 (other user)
    users = [
        ("user-001", "tester-one",   "active", "2024-01-01 10:00:00"),
        ("user-002", "tester-two",   "active", "2024-01-01 11:00:00"),
        ("user-003", "tester-three", "active", "2024-01-01 12:00:00"),
    ]
    for u in users:
        conn.execute("""
            INSERT INTO users (id, anonymous_nickname, status, created_at)
            VALUES (?, ?, ?, ?)
        """, u)

    # Published gift: gift-f001 owned by user-001
    # Non-published gifts: pending, archived, draft
    samples = [
        ("gift-f001", "user-001", "旧台灯",     "家居", "friend",  "朋友",  "sell",     "放下",
         "200元", "", "", 0, "published",   "2024-06-01 10:00:00", "2024-06-01 10:00:00"),
        ("gift-f002", "user-001", "围巾",       "服饰", "lover",  "恋人",  "keep",     "遗憾",
         "",     "", "", 1, "published",   "2024-06-02 10:00:00", "2024-06-02 10:00:00"),
        ("gift-f003", "user-001", "手账本",     "文具", "family", "家人",  "exchange", "感谢",
         "换文具", "", "", 0, "published",  "2024-06-03 10:00:00", "2024-06-03 10:00:00"),
        ("gift-f004", "user-001", "秘密礼物",   "其他", "lover",  "恋人",  "keep",     "平静",
         "",     "", "", 1, "pending_review", "2024-06-04 10:00:00", "2024-06-04 10:00:00"),
        ("gift-f005", "user-001", "归档礼物",   "其他", "friend", "朋友",  "sell",     "放下",
         "50元", "", "", 0, "archived",    "2024-06-05 10:00:00", "2024-06-05 10:00:00"),
        ("gift-f006", "user-001", "草稿礼物",   "其他", "friend", "朋友",  "keep",     "纪念",
         "",     "", "", 1, "draft",       "2024-06-06 10:00:00", "2024-06-06 10:00:00"),
    ]
    for s in samples:
        conn.execute("""
            INSERT INTO gifts (id, user_id, title, category, relation_type, relation_label,
                               action_type, emotion, price_or_exchange, condition_note,
                               city_blur, is_anonymous, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, s)

    stories = [
        ("story-f001", "gift-f001", "旧台灯的故事。",         "完整故事：台灯是朋友送的。",         85, "safe", "2024-06-01 10:00:00"),
        ("story-f002", "gift-f002", "围巾的故事。",           "完整故事：围巾是恋人织的。",         90, "safe", "2024-06-02 10:00:00"),
        ("story-f003", "gift-f003", "手账本的故事。",         "完整故事：手账本记录了生活。",       88, "safe", "2024-06-03 10:00:00"),
        ("story-f004", "gift-f004", "秘密故事。",             "完整故事：秘密。",                   70, "caution", "2024-06-04 10:00:00"),
        ("story-f005", "gift-f005", "归档故事。",             "完整故事：归档了。",                 75, "safe", "2024-06-05 10:00:00"),
        ("story-f006", "gift-f006", "草稿故事。",             "完整故事：草稿。",                   60, "safe", "2024-06-06 10:00:00"),
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
    global _test_db_dir, _test_db_path
    # Clean up previous temp dir
    shutil.rmtree(_test_db_dir, ignore_errors=True)
    # Create fresh temp dir
    _test_db_dir = tempfile.mkdtemp(prefix="aftergift_fav_test_")
    _test_db_path = os.path.join(_test_db_dir, "test.db")
    os.environ["AFTERGIFT_DB_PATH"] = _test_db_path

    # Force reload app.database to pick up new DB_PATH env
    import importlib
    import app.database as _db
    importlib.reload(_db)

    from app.database import get_connection, close_connection, init_db
    init_db(drop_existing=True)
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE id IN ('user-001', 'user-002', 'user-003')")
    conn.commit()
    close_connection(conn)
    _seed_test_data()


def _teardown():
    shutil.rmtree(_test_db_dir, ignore_errors=True)


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_token(user_id: str, nickname: str) -> str:
    resp = client.post("/api/auth/anonymous", json={
        "id": user_id, "nickname": nickname
    })
    assert resp.status_code == 201, f"Failed to create test identity: {resp.text}"
    return resp.json()["data"]["access_token"]


def _extract(body):
    if isinstance(body, dict):
        d = body.get("data", body)
        return d if isinstance(d, dict) else body
    return body


# ── Tests ─────────────────────────────────────────────────────────────────

def test_post_favorite_no_token_returns_401():
    """POST /api/gifts/{id}/favorite 无 token → 401"""
    _setup()
    try:
        resp = client.post("/api/gifts/gift-f001/favorite")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
        print(f"  ✅ PASS [post_fav_no_token] 401")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [post_fav_no_token] {e}")
        return False
    finally:
        _teardown()


def test_post_favorite_success_returns_201():
    """POST /api/gifts/{id}/favorite 有 token → 201 + is_favorited + favorite_count"""
    _setup()
    try:
        token = _get_token("user-002", "收藏用户")
        resp = client.post("/api/gifts/gift-f001/favorite",
                           headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        body = resp.json()
        data = _extract(body)
        assert data["is_favorited"] == True, f"Expected is_favorited=True, got {data}"
        assert data["favorite_count"] == 1, f"Expected favorite_count=1, got {data}"
        assert "gift_id" in data, f"Missing gift_id in response: {data}"
        print(f"  ✅ PASS [post_fav_success] 201, is_favorited={data['is_favorited']}, count={data['favorite_count']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [post_fav_success] {e}")
        return False
    finally:
        _teardown()


def test_post_favorite_idempotent_returns_200():
    """重复 POST favorite 幂等：第二次返回 200，不 409"""
    _setup()
    try:
        token = _get_token("user-002", "幂等测试用户")
        h = {"Authorization": f"Bearer {token}"}

        resp1 = client.post("/api/gifts/gift-f001/favorite", headers=h)
        assert resp1.status_code == 201, f"First call failed: {resp1.status_code}"

        resp2 = client.post("/api/gifts/gift-f001/favorite", headers=h)
        # Must be 200 idempotent, not 409
        assert resp2.status_code == 200, f"Expected 200 (idempotent), got {resp2.status_code}: {resp2.text}"
        body = resp2.json()
        data = _extract(body)
        assert data["is_favorited"] == True
        assert data["favorite_count"] == 1  # Still 1, not 2
        print(f"  ✅ PASS [post_fav_idempotent] 200 on duplicate, count={data['favorite_count']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [post_fav_idempotent] {e}")
        return False
    finally:
        _teardown()


def test_delete_favorite_success_returns_200():
    """DELETE /api/gifts/{id}/favorite 有 token → 200 + is_favorited=false + count"""
    _setup()
    try:
        token = _get_token("user-002", "删除测试用户")
        h = {"Authorization": f"Bearer {token}"}

        # Favorite first
        client.post("/api/gifts/gift-f001/favorite", headers=h)

        # Then delete
        resp = client.delete("/api/gifts/gift-f001/favorite", headers=h)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        data = _extract(body)
        assert data["is_favorited"] == False, f"Expected is_favorited=False, got {data}"
        assert data["favorite_count"] == 0, f"Expected favorite_count=0, got {data}"
        assert "gift_id" in data
        print(f"  ✅ PASS [del_fav_success] 200, is_favorited={data['is_favorited']}, count={data['favorite_count']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [del_fav_success] {e}")
        return False
    finally:
        _teardown()


def test_delete_favorite_idempotent_returns_200():
    """重复 DELETE favorite 幂等：返回 200，不 404"""
    _setup()
    try:
        token = _get_token("user-002", "幂等删除用户")
        h = {"Authorization": f"Bearer {token}"}

        resp1 = client.delete("/api/gifts/gift-f001/favorite", headers=h)
        # First delete: may be 200 or 404 depending on existence
        assert resp1.status_code in (200, 404), f"Unexpected: {resp1.status_code}"

        resp2 = client.delete("/api/gifts/gift-f001/favorite", headers=h)
        assert resp2.status_code == 200, f"Expected 200 (idempotent), got {resp2.status_code}: {resp2.text}"
        body = resp2.json()
        data = _extract(body)
        assert data["is_favorited"] == False
        assert data["favorite_count"] == 0
        print(f"  ✅ PASS [del_fav_idempotent] 200 on duplicate delete, count={data['favorite_count']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [del_fav_idempotent] {e}")
        return False
    finally:
        _teardown()


def test_favorite_count_increments_after_favorite():
    """收藏后 GET /api/gifts/{id} favorite_count +1"""
    _setup()
    try:
        token = _get_token("user-002", "计数测试用户")
        h = {"Authorization": f"Bearer {token}"}

        # Check initial count
        resp0 = client.get("/api/gifts/gift-f001")
        assert resp0.status_code == 200
        initial_count = resp0.json()["data"]["favorite_count"]
        assert initial_count == 0, f"Initial count should be 0, got {initial_count}"

        # Favorite it
        client.post("/api/gifts/gift-f001/favorite", headers=h)

        # Check updated count
        resp1 = client.get("/api/gifts/gift-f001")
        assert resp1.status_code == 200
        new_count = resp1.json()["data"]["favorite_count"]
        assert new_count == initial_count + 1, f"Expected {initial_count+1}, got {new_count}"
        print(f"  ✅ PASS [fav_count_increments] 0 → {new_count}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [fav_count_increments] {e}")
        return False
    finally:
        _teardown()


def test_get_gift_is_favorited_true_when_authenticated():
    """有 token 时 GET /api/gifts/{id} 返回 is_favorited=true（登录用户已收藏）"""
    _setup()
    try:
        token = _get_token("user-002", "已收藏用户")
        h = {"Authorization": f"Bearer {token}"}

        # user-002 favorites gift-f002
        client.post("/api/gifts/gift-f002/favorite", headers=h)

        # GET detail with same token
        resp = client.get("/api/gifts/gift-f002", headers=h)
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["is_favorited"] == True, f"Expected is_favorited=True, got {body.get('is_favorited')}"
        print(f"  ✅ PASS [is_favorited_true_when_authed]")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [is_favorited_true_when_authed] {e}")
        return False
    finally:
        _teardown()


def test_get_gift_is_favorited_false_without_token():
    """无 token 时 GET /api/gifts/{id} 返回 is_favorited=false"""
    _setup()
    try:
        # No token at all
        resp = client.get("/api/gifts/gift-f001")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body.get("is_favorited") == False, f"Expected is_favorited=False for anonymous, got {body.get('is_favorited')}"
        print(f"  ✅ PASS [is_favorited_false_no_token]")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [is_favorited_false_no_token] {e}")
        return False
    finally:
        _teardown()


def test_favorite_blocked_for_pending_review_gift():
    """不允许收藏 pending_review 礼物 → 422"""
    _setup()
    try:
        token = _get_token("user-002", "阻止测试用户")
        h = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/gifts/gift-f004/favorite", headers=h)
        assert resp.status_code == 422, f"Expected 422 for pending_review, got {resp.status_code}: {resp.text}"
        print(f"  ✅ PASS [fav_blocked_pending_review] 422")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [fav_blocked_pending_review] {e}")
        return False
    finally:
        _teardown()


def test_favorite_blocked_for_archived_gift():
    """不允许收藏 archived 礼物 → 422"""
    _setup()
    try:
        token = _get_token("user-002", "归档阻止用户")
        h = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/gifts/gift-f005/favorite", headers=h)
        assert resp.status_code == 422, f"Expected 422 for archived, got {resp.status_code}: {resp.text}"
        print(f"  ✅ PASS [fav_blocked_archived] 422")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [fav_blocked_archived] {e}")
        return False
    finally:
        _teardown()


def test_favorite_blocked_for_draft_gift():
    """不允许收藏 draft 礼物 → 422"""
    _setup()
    try:
        token = _get_token("user-002", "草稿阻止用户")
        h = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/gifts/gift-f006/favorite", headers=h)
        assert resp.status_code == 422, f"Expected 422 for draft, got {resp.status_code}: {resp.text}"
        print(f"  ✅ PASS [fav_blocked_draft] 422")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [fav_blocked_draft] {e}")
        return False
    finally:
        _teardown()


def test_favorites_of_me_returns_user_favorites():
    """GET /api/gifts?favorites_of=me 返回当前用户的收藏"""
    _setup()
    try:
        token = _get_token("user-003", "收藏列表用户")
        h = {"Authorization": f"Bearer {token}"}

        # user-003 favorites two gifts
        client.post("/api/gifts/gift-f001/favorite", headers=h)
        client.post("/api/gifts/gift-f002/favorite", headers=h)

        # Query favorites_of=me
        resp = client.get("/api/gifts?favorites_of=me", headers=h)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        data = body["data"] if "data" in body else body
        items = data["items"] if "items" in data else data
        ids = {item["id"] for item in items}
        assert "gift-f001" in ids, f"gift-f001 not in favorites_of=me: {ids}"
        assert "gift-f002" in ids, f"gift-f002 not in favorites_of=me: {ids}"
        print(f"  ✅ PASS [favorites_of_me] returned {len(items)} items: {ids}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [favorites_of_me] {e}")
        return False
    finally:
        _teardown()


def test_unfavorite_removes_from_favorites_of_me():
    """取消收藏后 favorites_of=me 不再返回该礼物"""
    _setup()
    try:
        token = _get_token("user-003", "取消收藏用户")
        h = {"Authorization": f"Bearer {token}"}

        # Favorite
        client.post("/api/gifts/gift-f003/favorite", headers=h)

        # Verify it's there
        resp1 = client.get("/api/gifts?favorites_of=me", headers=h)
        items1 = resp1.json()["data"]["items"]
        assert any(item["id"] == "gift-f003" for item in items1), "gift-f003 should be in favorites"

        # Unfavorite
        client.delete("/api/gifts/gift-f003/favorite", headers=h)

        # Verify it's gone
        resp2 = client.get("/api/gifts?favorites_of=me", headers=h)
        items2 = resp2.json()["data"]["items"]
        assert not any(item["id"] == "gift-f003" for item in items2), "gift-f003 should NOT be in favorites after unfavorite"
        print(f"  ✅ PASS [unfavorite_removes_from_favorites_of_me]")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [unfavorite_removes_from_favorites_of_me] {e}")
        return False
    finally:
        _teardown()


def test_discovery_popular_sorted_by_favorite_count():
    """Discovery popular rail 按 favorite_count 降序排列"""
    _setup()
    try:
        token = _get_token("user-002", "popular排序用户")
        h = {"Authorization": f"Bearer {token}"}

        # Give gift-f001 two favorites, gift-f002 one favorite
        client.post("/api/gifts/gift-f001/favorite", headers=h)
        client.post("/api/gifts/gift-f001/favorite",
                    headers={"Authorization": f"Bearer {_get_token('user-001', '另一个用户')}"})
        client.post("/api/gifts/gift-f002/favorite", headers=h)

        resp = client.get("/api/gifts/discovery?rail=popular")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()["data"]
        items = body["items"] if isinstance(body, dict) and "items" in body else body
        # First item should have >= favorite_count of second
        if len(items) >= 2:
            assert items[0]["favorite_count"] >= items[1]["favorite_count"], \
                f"Popular not sorted by favorite_count: {items[0]['favorite_count']} vs {items[1]['favorite_count']}"
        print(f"  ✅ PASS [discovery_popular_sorted] first={items[0]['favorite_count']}, second={items[1]['favorite_count']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [discovery_popular_sorted] {e}")
        return False
    finally:
        _teardown()


def test_favorite_count_in_list_gifts():
    """GET /api/gifts 列表项包含 favorite_count"""
    _setup()
    try:
        token = _get_token("user-002", "列表计数用户")
        h = {"Authorization": f"Bearer {token}"}
        client.post("/api/gifts/gift-f001/favorite", headers=h)

        resp = client.get("/api/gifts")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        gift_item = next((i for i in items if i["id"] == "gift-f001"), None)
        assert gift_item is not None, "gift-f001 not in list"
        assert "favorite_count" in gift_item, f"favorite_count missing in list item: {gift_item.keys()}"
        assert gift_item["favorite_count"] == 1, f"Expected favorite_count=1, got {gift_item['favorite_count']}"
        print(f"  ✅ PASS [list_gifts_has_favorite_count]")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [list_gifts_has_favorite_count] {e}")
        return False
    finally:
        _teardown()


# ── Main ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Aftergift Backend - Favorites API Tests (Phase 2J-1)")
    print("=" * 58)

    tests = [
        test_post_favorite_no_token_returns_401,
        test_post_favorite_success_returns_201,
        test_post_favorite_idempotent_returns_200,
        test_delete_favorite_success_returns_200,
        test_delete_favorite_idempotent_returns_200,
        test_favorite_count_increments_after_favorite,
        test_get_gift_is_favorited_true_when_authenticated,
        test_get_gift_is_favorited_false_without_token,
        test_favorite_blocked_for_pending_review_gift,
        test_favorite_blocked_for_archived_gift,
        test_favorite_blocked_for_draft_gift,
        test_favorites_of_me_returns_user_favorites,
        test_unfavorite_removes_from_favorites_of_me,
        test_discovery_popular_sorted_by_favorite_count,
        test_favorite_count_in_list_gifts,
    ]

    passed = sum(t() for t in tests)
    total = len(tests)
    print(f"\nResult: {passed}/{total} passed")
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {total - passed} test(s) failed.")
        sys.exit(1)