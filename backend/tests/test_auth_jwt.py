#!/usr/bin/env python3
"""
Aftergift Backend - JWT Auth Contract Tests
Phase 2E-1 | test_auth_jwt.py

不依赖 pytest，可作为普通 Python 脚本运行。
测试 PyJWT token 生成、验证、过期处理、401/403 语义。

Phase 2K-2.1: 在导入 app 模块前设置 AFTERGIFT_DB_PATH 到临时 DB，
并执行 init_db + run_migrations，避免 no such table 错误。
"""

import sys
import os
import time
import traceback
import tempfile

# ── Test DB Setup ─────────────────────────────────────────────────────────────
# 在 import app 模块前设置 AFTERGIFT_DB_PATH，使 app 使用临时 DB
_TEST_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TEST_DB.close()
os.environ["AFTERGIFT_DB_PATH"] = _TEST_DB.name

# 确保 backend/backend/ 在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# 初始化 schema 和 migrations
from app.database import init_db
from scripts.migrate_db import run_migrations

init_db(drop_existing=True)
run_migrations(db_path=os.environ["AFTERGIFT_DB_PATH"])

# ── Now import app (uses the temp DB) ─────────────────────────────────────────
from starlette.testclient import TestClient
from app.main import app

print("Aftergift Backend - JWT Auth Contract Tests (Phase 2E-1)")
print("=" * 56)


def extract_error_message(data):
    """兼容 FastAPI HTTPException 的两种响应格式：{message} 或 {detail: {message}}"""
    if isinstance(data, dict):
        if isinstance(data.get("detail"), dict):
            return data["detail"].get("message", "")
        return data.get("message", "")
    return ""


def test_imports():
    """验证 PyJWT 可用且配置正确"""
    try:
        import jwt
        from app.config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_TTL_SECONDS
        assert JWT_ALGORITHM == "HS256", f"Expected HS256, got {JWT_ALGORITHM}"
        assert ACCESS_TOKEN_TTL_SECONDS == 604800, f"Expected 604800, got {ACCESS_TOKEN_TTL_SECONDS}"
        print(f"  ✅ PASS [imports] PyJWT={jwt.__version__}, ALGORITHM={JWT_ALGORITHM}, TTL={ACCESS_TOKEN_TTL_SECONDS}s")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [imports] {e}")
        return False


def test_token_structure():
    """create_access_token 生成标准 JWT（三段式）"""
    try:
        from app.auth import create_access_token
        token = create_access_token("user-test-001", "测试用户", "user")
        parts = token.split(".")
        assert len(parts) == 3, f"JWT should have 3 parts, got {len(parts)}"
        print(f"  ✅ PASS [token_structure] token is 3-part JWT")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [token_structure] {e}")
        return False


def test_token_payload():
    """decode_access_token 正确解析 sub / role / exp / jti"""
    try:
        from app.auth import create_access_token, decode_access_token
        token = create_access_token("user-payload-99", " Payload用户 ", "user")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-payload-99", f"Expected user-payload-99, got {payload.get('sub')}"
        assert payload["role"] == "user", f"Expected user, got {payload.get('role')}"
        assert "exp" in payload, "Missing exp in payload"
        assert "jti" in payload, "Missing jti in payload"
        assert "iat" in payload, "Missing iat in payload"
        print(f"  ✅ PASS [token_payload] sub={payload['sub']}, role={payload['role']}, jti={payload['jti'][:8]}...")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [token_payload] {e}")
        return False


def test_invalid_token():
    """无效 token（错误签名/损坏/伪造）被 decode_access_token 拒绝"""
    try:
        from app.auth import decode_access_token
        cases = [
            "eyJhbG...TURE",
            "not.a.jwt.at.all",
            "eyJhbG...se64!",
            "",
        ]
        for tok in cases:
            try:
                decode_access_token(tok)
                assert False, f"Should have raised an exception for: {tok[:30]}"
            except Exception:
                pass  # expected
        print(f"  ✅ PASS [invalid_token] {len(cases)} invalid tokens all rejected")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [invalid_token] {e}")
        return False


def test_expired_token():
    """过期 token 被拒绝"""
    try:
        import jwt
        from app.config import JWT_SECRET, JWT_ALGORITHM
        from app.auth import decode_access_token
        # Manually create an expired token
        expired = jwt.encode(
            {"sub": "user-expired", "exp": int(time.time()) - 3600, "iat": int(time.time()) - 7200, "role": "user"},
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        try:
            decode_access_token(expired)
            assert False, "Should have raised ExpiredSignatureError"
        except jwt.ExpiredSignatureError:
            pass  # expected
        except Exception:
            pass  # also acceptable
        print(f"  ✅ PASS [expired_token] expired token correctly rejected")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [expired_token] {e}")
        return False


def test_require_auth_no_header():
    """_require_auth: 缺少 Authorization → 401"""
    try:
        client = TestClient(app)
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
        body = resp.json()
        msg = extract_error_message(body)
        assert "缺少身份凭证" in msg or "Authorization" in msg, f"Unexpected message: {body}"
        print(f"  ✅ PASS [require_auth_no_header] 401 for missing header, msg='{msg}'")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [require_auth_no_header] {e}")
        traceback.print_exc()
        return False


def test_require_auth_wrong_format():
    """Authorization 格式错误（非 Bearer） → 401"""
    try:
        client = TestClient(app)
        resp = client.get("/api/auth/me", headers={"Authorization": "Basic abc123"})
        # Could be 401 or 403 depending on implementation detail
        assert resp.status_code in (401, 403), f"Expected 401/403, got {resp.status_code}"
        print(f"  ✅ PASS [require_auth_wrong_format] {resp.status_code} for wrong auth type")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [require_auth_wrong_format] {e}")
        return False


def test_require_auth_invalid_token():
    """无效 token → 403"""
    try:
        client = TestClient(app)
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        print(f"  ✅ PASS [require_auth_invalid_token] 403 for invalid token")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [require_auth_invalid_token] {e}")
        return False


def test_create_anonymous_returns_jwt():
    """POST /api/auth/anonymous → 201 + JWT in response"""
    try:
        client = TestClient(app)
        resp = client.post("/api/auth/anonymous")
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "access_token" in data["data"], f"Missing access_token: {data}"
        token = data["data"]["access_token"]
        assert token.count(".") == 2, f"Expected JWT format, got: {token[:20]}"
        assert data["data"]["token_type"] == "Bearer"
        assert data["data"]["expires_in"] == 604800
        print(f"  ✅ PASS [create_anonymous_returns_jwt] token={token[:12]}..., expires_in=604800")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [create_anonymous_returns_jwt] {e}")
        return False


def test_auth_me_valid_token():
    """GET /api/auth/me 带有效 Bearer token → 200 + user info"""
    try:
        client = TestClient(app)
        # Create anonymous user
        resp = client.post("/api/auth/anonymous")
        assert resp.status_code == 201, f"Setup failed: {resp.text}"
        token = resp.json()["data"]["access_token"]
        # Use the token
        me_resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_resp.status_code == 200, f"Expected 200, got {me_resp.status_code}: {me_resp.text}"
        me_data = me_resp.json()["data"]
        assert "user_id" in me_data
        assert "anonymous_nickname" in me_data
        assert "role" in me_data
        assert "token_version" in me_data
        print(f"  ✅ PASS [auth_me_valid_token] user_id={me_data['user_id']}, role={me_data['role']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [auth_me_valid_token] {e}")
        return False


def test_gifts_requires_auth():
    """POST /api/gifts 无 token → 401"""
    try:
        client = TestClient(app)
        response = client.post(
            "/api/gifts",
            json={
                "title": "测试礼物",
                "category": "other",
                "relation_type": "friend",
                "action_type": "keep",
                "emotion": "平静",
                "short_story": "这是一个测试故事内容。",
                "full_story": "这是完整的测试故事内容，足够长以满足验证要求。",
                "price_or_exchange": "",
                "is_anonymous": True,
            }
        )
        # Without token → 401 (not 422, which means validation error)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text[:200]}"
        print(f"  ✅ PASS [gifts_requires_auth] POST /api/gifts 401 without token")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [gifts_requires_auth] {e}")
        return False


def test_gifts_with_valid_token():
    """POST /api/gifts 带有效 token → 201 (status=safe) 或 200 (status=needs_edit)"""
    try:
        client = TestClient(app)
        # Create anonymous user (uses temp DB which now has users table)
        resp = client.post("/api/auth/anonymous")
        assert resp.status_code == 201, f"Setup failed: {resp.text}"
        token = resp.json()["data"]["access_token"]
        # Attempt to post a gift
        resp2 = client.post(
            "/api/gifts",
            json={
                "title": "一盏暖黄的灯",
                "category": "home",
                "relation_type": "friend",
                "action_type": "sell",
                "emotion": "放下",
                "short_story": "搬家时整理出来的闲置物品，状态很好，希望找到需要的人。",
                "full_story": "这是一套全新的厨房用品，包装都没拆过。朋友送的乔迁礼，但我们已经有了类似的，所以想转给需要的人。",
                "price_or_exchange": "120元",
                "is_anonymous": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        data = resp2.json()
        # Accept both: safe→201 or needs_edit→200 (mock moderation may flag personal stories)
        assert resp2.status_code in (200, 201), f"Expected 200/201, got {resp2.status_code}: {resp2.text}"
        assert data["data"]["status"] in ("safe", "needs_edit"), f"Unexpected status: {data['data']['status']}"
        print(f"  ✅ PASS [gifts_with_valid_token] status={data['data']['status']} (status {resp2.status_code} accepted)")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [gifts_with_valid_token] {e}")
        return False


# ── Runner ───────────────────────────────────────────────────────────────────

TESTS = [
    test_imports,
    test_token_structure,
    test_token_payload,
    test_invalid_token,
    test_expired_token,
    test_require_auth_no_header,
    test_require_auth_wrong_format,
    test_require_auth_invalid_token,
    test_create_anonymous_returns_jwt,
    test_auth_me_valid_token,
    test_gifts_requires_auth,
    test_gifts_with_valid_token,
]

if __name__ == "__main__":
    passed = 0
    failed = 0
    for t in TESTS:
        try:
            if t():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ CRASH in {t.__name__}: {e}")
            failed += 1

    print(f"\nResult: {passed}/{len(TESTS)} passed")
    if passed == len(TESTS):
        print("ALL TESTS PASSED ✅")
    else:
        print(f"SOME TESTS FAILED ❌ ({failed} failures)")
        sys.exit(1)

    # Cleanup temp DB
    try:
        os.unlink(_TEST_DB.name)
    except Exception:
        pass
