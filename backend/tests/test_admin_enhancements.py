#!/usr/bin/env python3
"""
Aftergift Backend - Admin Enhancements Tests
Phase 2F | test_admin_enhancements.py

不依赖 pytest，可作为普通 Python 脚本运行。
测试 Admin 审核台增强功能：筛选、分页、decision note、reports、logs、actions。

Phase 2K-2.1: 每个测试使用独立临时 DB（init_db + run_migrations），
不依赖真实 aftergift_dev.db，避免 no such table 错误。
"""

import sys
import os
import tempfile
import traceback

# ── Test DB Setup ─────────────────────────────────────────────────────────────
# 在 import app 模块前设置 AFTERGIFT_DB_PATH，使 app 使用临时 DB
_TEST_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TEST_DB.close()
os.environ["AFTERGIFT_DB_PATH"] = _TEST_DB.name

# 确保 backend/backend/ 在 sys.path 中，使 'from app.xxx' 能正确解析
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# 初始化 schema 和 migrations（必须在 import app 之后、但在创建 TestClient 之前）
from app.database import init_db
from scripts.migrate_db import run_migrations

init_db(drop_existing=True)
run_migrations(db_path=os.environ["AFTERGIFT_DB_PATH"])

# ── Now import app (uses the temp DB) ─────────────────────────────────────────
from starlette.testclient import TestClient
from app.main import app

# ── Test helpers ───────────────────────────────────────────────────────────────

def _admin_token():
    from app.config import ADMIN_TOKEN
    return ADMIN_TOKEN


def _create_test_gift(client, token):
    """创建一个测试礼物，返回 gift_id"""
    resp = client.post(
        "/api/gifts",
        json={
            "title": "测试礼物-Admin",
            "category": "other",
            "relation_type": "friend",
            "action_type": "giveaway",
            "emotion": "放下",
            "short_story": "这是一个测试故事。",
            "full_story": "这是完整的测试故事，用于 admin 审核测试。",
            "price_or_exchange": "",
            "is_anonymous": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, f"Setup failed: {resp.text}"
    data = resp.json()["data"]
    return data["gift_id"]


def _create_anonymous_user(client):
    resp = client.post("/api/auth/anonymous")
    assert resp.status_code == 201, f"Auth setup failed: {resp.text}"
    return resp.json()["data"]["access_token"]


def _get_client():
    return TestClient(app)


# ── Tests ────────────────────────────────────────────────────────────────────

def test_reviews_no_token():
    """GET /api/admin/reviews 无 token → 401"""
    try:
        client = _get_client()
        resp = client.get("/api/admin/reviews")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print("  ✅ PASS [reviews_no_token] 401 for missing token")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [reviews_no_token] {e}")
        return False


def test_reviews_wrong_token():
    """GET /api/admin/reviews 错 token → 403"""
    try:
        client = _get_client()
        resp = client.get("/api/admin/reviews", headers={"X-Admin-Token": "wrong-token"})
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        print("  ✅ PASS [reviews_wrong_token] 403 for invalid token")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [reviews_wrong_token] {e}")
        return False


def test_reviews_with_filters():
    """GET /api/admin/reviews 正确 token + filters → 200"""
    try:
        client = _get_client()
        token = _admin_token()
        resp = client.get(
            "/api/admin/reviews?status=pending_review&risk_level=safe&page=1&limit=5&sort=created_at&order=desc",
            headers={"X-Admin-Token": token},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "total_pages" in data
        assert "filters" in data
        print(f"  ✅ PASS [reviews_with_filters] items={len(data['items'])}, total={data['total']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [reviews_with_filters] {e}")
        traceback.print_exc()
        return False


def test_reviews_pagination_fields():
    """分页返回字段正确"""
    try:
        client = _get_client()
        token = _admin_token()
        resp = client.get(
            "/api/admin/reviews?page=1&limit=2",
            headers={"X-Admin-Token": token},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["page"] == 1
        assert data["limit"] == 2
        assert data["total_pages"] >= 1
        print(f"  ✅ PASS [reviews_pagination_fields] page={data['page']}, limit={data['limit']}, total_pages={data['total_pages']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [reviews_pagination_fields] {e}")
        return False


def test_decision_with_note():
    """POST decision with note → admin_actions 写入 note"""
    try:
        client = _get_client()
        admin_token = _admin_token()
        user_token = _create_anonymous_user(client)
        gift_id = _create_test_gift(client, user_token)

        resp = client.post(
            f"/api/admin/reviews/{gift_id}/decision",
            json={"decision": "approve", "note": "测试备注：内容合规"},
            headers={"X-Admin-Token": admin_token},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["new_status"] == "published"
        assert data["decision"] == "approve"
        assert data["note"] == "测试备注：内容合规"

        # Verify admin_actions has the note
        resp2 = client.get(
            "/api/admin/actions?target_type=gift&target_id=" + gift_id,
            headers={"X-Admin-Token": admin_token},
        )
        assert resp2.status_code == 200
        actions = resp2.json()["data"]["items"]
        assert len(actions) >= 1
        assert any(a["note"] == "测试备注：内容合规" for a in actions)

        print(f"  ✅ PASS [decision_with_note] gift={gift_id[:8]}, note recorded")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [decision_with_note] {e}")
        traceback.print_exc()
        return False


def test_review_logs():
    """GET /api/admin/reviews/{gift_id}/logs → 200"""
    try:
        client = _get_client()
        admin_token = _admin_token()
        user_token = _create_anonymous_user(client)
        gift_id = _create_test_gift(client, user_token)

        resp = client.get(
            f"/api/admin/reviews/{gift_id}/logs",
            headers={"X-Admin-Token": admin_token},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
        print(f"  ✅ PASS [review_logs] gift={gift_id[:8]}, logs={data['total']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [review_logs] {e}")
        return False


def test_reports_list():
    """GET /api/admin/reports → 200"""
    try:
        client = _get_client()
        admin_token = _admin_token()
        resp = client.get(
            "/api/admin/reports?status=pending&page=1&limit=10",
            headers={"X-Admin-Token": admin_token},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
        assert "page" in data
        print(f"  ✅ PASS [reports_list] items={len(data['items'])}, total={data['total']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [reports_list] {e}")
        return False


def test_report_decision():
    """POST report decision → 200"""
    try:
        client = _get_client()
        admin_token = _admin_token()
        user_token = _create_anonymous_user(client)
        gift_id = _create_test_gift(client, user_token)

        # Submit a report first
        report_resp = client.post(
            f"/api/gifts/{gift_id}/report",
            json={"reason": "privacy_risk", "detail": "测试举报"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert report_resp.status_code == 200, f"Report setup failed: {report_resp.text}"

        # Get the report ID
        reports_resp = client.get(
            "/api/admin/reports?status=pending",
            headers={"X-Admin-Token": admin_token},
        )
        assert reports_resp.status_code == 200
        items = reports_resp.json()["data"]["items"]
        assert len(items) >= 1, "No reports found"
        report_id = items[0]["report_id"]

        # Decide on report
        decision_resp = client.post(
            f"/api/admin/reports/{report_id}/decision",
            json={"decision": "dismiss", "note": "无违规"},
            headers={"X-Admin-Token": admin_token},
        )
        assert decision_resp.status_code == 200, f"Expected 200, got {decision_resp.status_code}: {decision_resp.text}"
        decision_data = decision_resp.json()["data"]
        assert decision_data["new_status"] == "resolved_dismissed"
        print(f"  ✅ PASS [report_decision] report_id={report_id[:8]}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [report_decision] {e}")
        return False


def test_admin_actions():
    """GET /api/admin/actions → 200"""
    try:
        client = _get_client()
        admin_token = _admin_token()
        resp = client.get(
            "/api/admin/actions?page=1&limit=5",
            headers={"X-Admin-Token": admin_token},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
        assert "page" in data
        print(f"  ✅ PASS [admin_actions] items={len(data['items'])}, total={data['total']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [admin_actions] {e}")
        return False


def test_sql_injection_protection():
    """SQL 注入防护：恶意 sort 参数 → 400"""
    try:
        client = _get_client()
        admin_token = _admin_token()
        resp = client.get(
            "/api/admin/reviews?sort=gift_id;DROP TABLE users;&order=desc",
            headers={"X-Admin-Token": admin_token},
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        print("  ✅ PASS [sql_injection_protection] 400 for malicious sort")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [sql_injection_protection] {e}")
        return False


def test_invalid_status_filter():
    """无效 status filter → 400"""
    try:
        client = _get_client()
        admin_token = _admin_token()
        resp = client.get(
            "/api/admin/reviews?status=not_a_valid_status",
            headers={"X-Admin-Token": admin_token},
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        print("  ✅ PASS [invalid_status_filter] 400 for invalid status")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [invalid_status_filter] {e}")
        return False


# ── Runner ───────────────────────────────────────────────────────────────────

TESTS = [
    test_reviews_no_token,
    test_reviews_wrong_token,
    test_reviews_with_filters,
    test_reviews_pagination_fields,
    test_decision_with_note,
    test_review_logs,
    test_reports_list,
    test_report_decision,
    test_admin_actions,
    test_sql_injection_protection,
    test_invalid_status_filter,
]

if __name__ == "__main__":
    print("Aftergift Backend - Admin Enhancements Tests (Phase 2F)")
    print("=" * 58)

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

    # Cleanup temp DB
    try:
        os.unlink(_TEST_DB.name)
    except Exception:
        pass
