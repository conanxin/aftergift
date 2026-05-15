#!/usr/bin/env python3
"""
Aftergift Backend - Contract Tests
Phase 2B | tests/test_fastapi_contract.py

不依赖 pytest，可作为普通 Python 脚本运行。
检查模块可导入、配置默认值、服务逻辑正确性。
"""

import sys
import os

# Add backend/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_schemas_import():
    """schemas 可导入"""
    try:
        from app import schemas
        assert hasattr(schemas, 'GiftCreate')
        assert hasattr(schemas, 'GiftListItem')
        assert hasattr(schemas, 'GiftDetail')
        assert hasattr(schemas, 'ReviewResult')
        print("✅ PASS [schemas] all key schemas importable")
        return True
    except Exception as e:
        print(f"❌ FAIL [schemas] {e}")
        return False


def test_review_service():
    """review_service 可返回 risk_level"""
    try:
        from app.services import review_service
        result = review_service.mock_review(
            "在一起的三年里，每次加班回家打开它，房间就像被星光包裹。",
            "这只灯在柜子里放了半年。我知道它值得被一个会喜欢它的人继续使用。"
        )
        assert "risk_level" in result
        assert result["risk_level"] in ("safe", "caution", "high_risk")
        assert "issues" in result
        assert "suggestions" in result
        assert "quality_notes" in result
        print(f"✅ PASS [review_service] risk_level={result['risk_level']}, issues={len(result['issues'])}")
        return True
    except Exception as e:
        print(f"❌ FAIL [review_service] {e}")
        return False


def test_review_service_high_risk():
    """review_service 能识别高风险内容"""
    try:
        from app.services import review_service
        result = review_service.mock_review(
            "他叫张明，我曝光他的手机号和微信。",
            "我要报复这个渣男，曝光他公司地址。"
        )
        assert result["risk_level"] == "high_risk"
        print(f"✅ PASS [review_service high_risk] correctly detected high_risk")
        return True
    except Exception as e:
        print(f"❌ FAIL [review_service high_risk] {e}")
        return False


def test_config_defaults():
    """config 可读取默认值"""
    try:
        from app.config import ENV, DB_PATH, ADMIN_TOKEN, ENABLE_REAL_AI_REVIEW
        assert ENV == "development"
        assert ADMIN_TOKEN == "change-me-dev-only" or ADMIN_TOKEN.startswith("dev-"), \
            f"ADMIN_TOKEN should be default or from .env, got {ADMIN_TOKEN!r}"
        assert ENABLE_REAL_AI_REVIEW is False
        print(f"✅ PASS [config] ENV={ENV}, DB_PATH={DB_PATH}")
        return True
    except Exception as e:
        print(f"❌ FAIL [config] {e}")
        return False


def test_database_row_factory():
    """database get_connection 设置 row_factory"""
    try:
        from app.database import get_connection
        conn = get_connection()
        cur = conn.execute("SELECT 1 as id")
        row = cur.fetchone()
        # With row_factory = sqlite3.Row, should support dict-like access
        assert row["id"] == 1, f"Expected row['id'] == 1, got {row['id']}"
        conn.close()
        print("✅ PASS [database] row_factory = sqlite3.Row works correctly")
        return True
    except Exception as e:
        print(f"❌ FAIL [database] {e}")
        return False


def test_routers_exist():
    """routers 文件存在"""
    try:
        from app.routers import gifts, reviews, favorites, reports, admin
        print("✅ PASS [routers] all router modules exist")
        return True
    except Exception as e:
        print(f"❌ FAIL [routers] {e}")
        return False


def test_models_enums():
    """models 枚举定义正确"""
    try:
        from app.models import GiftStatus, RiskLevel, ActionType, ReportReason
        assert GiftStatus.PUBLISHED == "published"
        assert RiskLevel.SAFE == "safe"
        assert ActionType.SELL == "sell"
        assert ReportReason.PRIVACY == "privacy"
        print("✅ PASS [models] all enums correct")
        return True
    except Exception as e:
        print(f"❌ FAIL [models] {e}")
        return False


def test_anonymize_service():
    """anonymize_service 可检测身份模式"""
    try:
        from app.services import anonymize_service
        text = "他叫张明，手机号是13812345678，微信是zhangming"
        findings = anonymize_service.detect_identity_patterns(text)
        assert len(findings) >= 2, f"Expected >= 2 findings, got {len(findings)}"
        print(f"✅ PASS [anonymize_service] detected {len(findings)} identity patterns")
        return True
    except Exception as e:
        print(f"❌ FAIL [anonymize_service] {e}")
        return False


def main():
    print("Aftergift Backend - Contract Tests")
    print(f"{'='*50}")

    tests = [
        test_schemas_import,
        test_review_service,
        test_review_service_high_risk,
        test_config_defaults,
        test_database_row_factory,
        test_routers_exist,
        test_models_enums,
        test_anonymize_service,
    ]

    results = [t() for t in tests]

    print(f"{'='*50}")
    passed = sum(results)
    total = len(results)
    print(f"Result: {passed}/{total} passed")

    if passed == total:
        print("✅ All contract tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
