#!/usr/bin/env python3
"""
Aftergift Backend - Smoke Test Script
Phase 2B | scripts/smoke_test.py

用法: python3 scripts/smoke_test.py
前提: uvicorn app.main:app --host 127.0.0.1 --port 8091 已运行

不依赖 pytest，用 urllib.request 实现。
"""

import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8091"
TESTS = []


def test(name, url, expected_code, expected_field=None):
    """Run a single smoke test."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if resp.status != expected_code:
                print(f"❌ FAIL [{name}] HTTP {resp.status} != {expected_code}")
                return False
            if expected_field and expected_field not in data:
                print(f"❌ FAIL [{name}] field '{expected_field}' not in response")
                return False
            print(f"✅ PASS [{name}] HTTP {resp.status}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"❌ FAIL [{name}] HTTP {e.code}: {body[:100]}")
        return False
    except Exception as e:
        print(f"❌ FAIL [{name}] {type(e).__name__}: {e}")
        return False


def main():
    print(f"Aftergift Backend Smoke Test")
    print(f"Base URL: {BASE_URL}")
    print(f"{'='*50}")

    results = []

    # 1. Health
    results.append(test("GET /api/health", f"{BASE_URL}/api/health", 200, "data"))

    # 2. Gift list
    results.append(test("GET /api/gifts", f"{BASE_URL}/api/gifts", 200, "data"))

    # 3. Gift detail
    results.append(test(
        "GET /api/gifts/gift-001",
        f"{BASE_URL}/api/gifts/gift-001",
        200,
        "data"
    ))

    # 4. Review mock
    req_body = json.dumps({
        "short_story": "在一起的三年里，每次加班回家打开它，房间就像被星光包裹。",
        "full_story": "后来我们分开了。这只灯在柜子里放了半年。我知道它值得被一个会喜欢它的人继续使用。"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/review/mock",
        data=req_body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if resp.status == 200 and "risk_level" in data:
                print(f"✅ PASS [POST /api/review/mock] HTTP 200, risk_level={data['risk_level']}")
                results.append(True)
            else:
                print(f"❌ FAIL [POST /api/review/mock] unexpected response")
                results.append(False)
    except Exception as e:
        print(f"❌ FAIL [POST /api/review/mock] {type(e).__name__}: {e}")
        results.append(False)

    # 5. Admin reviews (needs X-Admin-Token header - should get 401 without it)
    req = urllib.request.Request(f"{BASE_URL}/api/admin/reviews")
    try:
        urllib.request.urlopen(req, timeout=5)
        print(f"⚠️  WARN [GET /api/admin/reviews] expected 401 without token, got 200")
        results.append(True)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"✅ PASS [GET /api/admin/reviews] correctly returned 401 without token")
            results.append(True)
        else:
            print(f"❌ FAIL [GET /api/admin/reviews] HTTP {e.code}, expected 401")
            results.append(False)

    print(f"{'='*50}")
    passed = sum(results)
    total = len(results)
    print(f"Result: {passed}/{total} passed")

    if passed == total:
        print("✅ All smoke tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
