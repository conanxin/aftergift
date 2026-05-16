#!/usr/bin/env python3
"""
Aftergift Backend - Moderation Provider Contract Tests
Phase 2E-2 | test_moderation_provider.py

不依赖 pytest，可作为普通 Python 脚本运行。
测试 Moderation Provider 抽象层、factory 默认行为、mock provider 逻辑。
不调用外网，不依赖真实 API key。
"""

import sys
import os

# Add backend/backend/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import traceback

print("Aftergift Backend - Moderation Provider Tests (Phase 2E-2)")
print("=" * 56)


def test_factory_default_mock():
    """Factory 默认返回 mock provider"""
    try:
        # Reset cache to force re-evaluation
        from app.services.moderation.factory import reset_provider_cache, get_moderation_provider
        reset_provider_cache()
        provider = get_moderation_provider()
        assert provider.name == "mock", f"Expected mock, got {provider.name}"
        print(f"  ✅ PASS [factory_default_mock] default provider={provider.name}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [factory_default_mock] {e}")
        traceback.print_exc()
        return False


def test_factory_fallback_openai_no_enable():
    """provider=openai + ENABLE_REAL_AI_REVIEW=false → fallback mock"""
    try:
        from app.services.moderation.factory import reset_provider_cache
        from app.services.moderation import base
        # Patch config temporarily
        import app.config as config_backup
        import app.services.moderation.factory as factory_module

        reset_provider_cache()
        # Simulate env for this test
        orig_provider = os.environ.get("AFTERGIFT_MODERATION_PROVIDER", "")
        orig_enable = os.environ.get("AFTERGIFT_ENABLE_REAL_AI_REVIEW", "")
        os.environ["AFTERGIFT_MODERATION_PROVIDER"] = "openai"
        os.environ["AFTERGIFT_ENABLE_REAL_AI_REVIEW"] = "false"

        try:
            factory_module._cached_provider = None
            from app.services.moderation.factory import get_moderation_provider
            provider = get_moderation_provider()
            assert provider.name == "mock", f"Expected mock fallback, got {provider.name}"
            print(f"  ✅ PASS [factory_fallback_openai_no_enable] fallback to mock")
        finally:
            os.environ["AFTERGIFT_MODERATION_PROVIDER"] = orig_provider
            os.environ["AFTERGIFT_ENABLE_REAL_AI_REVIEW"] = orig_enable
            factory_module._cached_provider = None

        return True
    except Exception as e:
        print(f"  ❌ FAIL [factory_fallback_openai_no_enable] {e}")
        traceback.print_exc()
        return False


def test_factory_fallback_unknown():
    """provider=unknown → fallback mock"""
    try:
        import app.services.moderation.factory as factory_module
        factory_module._cached_provider = None

        orig = os.environ.get("AFTERGIFT_MODERATION_PROVIDER", "")
        os.environ["AFTERGIFT_MODERATION_PROVIDER"] = "unknown_provider"
        try:
            provider = factory_module.get_moderation_provider()
            assert provider.name == "mock", f"Expected mock fallback, got {provider.name}"
            print(f"  ✅ PASS [factory_fallback_unknown] fallback to mock")
        finally:
            os.environ["AFTERGIFT_MODERATION_PROVIDER"] = orig
            factory_module._cached_provider = None

        return True
    except Exception as e:
        print(f"  ❌ FAIL [factory_fallback_unknown] {e}")
        traceback.print_exc()
        return False


def test_mock_provider_detects_high_risk():
    """Mock provider 能识别高风险文本"""
    try:
        from app.services.moderation.mock_provider import MockModerationProvider
        provider = MockModerationProvider()
        result = provider.review(
            "他叫张明，我曝光他的手机号和微信。",
            "我要报复这个渣男，曝光他公司地址。"
        )
        assert result.risk_level == "high_risk", f"Expected high_risk, got {result.risk_level}"
        assert len(result.issues) >= 3, f"Expected >=3 issues, got {len(result.issues)}"
        print(f"  ✅ PASS [mock_high_risk] risk={result.risk_level}, issues={len(result.issues)}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [mock_high_risk] {e}")
        traceback.print_exc()
        return False


def test_mock_provider_normal_story():
    """Mock provider 对普通故事返回 safe 或 caution"""
    try:
        from app.services.moderation.mock_provider import MockModerationProvider
        provider = MockModerationProvider()
        result = provider.review(
            "搬家时整理出来的闲置物品，状态很好，希望找到需要的人。",
            "这是一套全新的厨房用品，包装都没拆过。朋友送的乔迁礼。"
        )
        assert result.risk_level in ("safe", "caution"), f"Expected safe/caution, got {result.risk_level}"
        assert result.provider == "mock"
        print(f"  ✅ PASS [mock_normal_story] risk={result.risk_level}, provider={result.provider}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [mock_normal_story] {e}")
        traceback.print_exc()
        return False


def test_review_story_returns_provider_field():
    """review_story() 返回包含 provider 字段"""
    try:
        from app.services.review_service import review_story
        result = review_story(
            "搬家时整理出来的闲置物品，状态很好，希望找到需要的人。",
            "这是一套全新的厨房用品，包装都没拆过。"
        )
        assert "provider" in result, f"Missing provider field: {result.keys()}"
        assert result["provider"] in ("mock", "openai", "baidu"), f"Invalid provider: {result['provider']}"
        print(f"  ✅ PASS [review_story_provider] provider={result['provider']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [review_story_provider] {e}")
        traceback.print_exc()
        return False


def test_review_result_structure():
    """review_story() 返回结构包含 risk_level/issues/suggestions/quality_notes"""
    try:
        from app.services.review_service import review_story
        result = review_story("搬家时整理出来的闲置物品，状态很好，希望找到需要的人。", "")
        assert "risk_level" in result, "Missing risk_level"
        assert result["risk_level"] in ("safe", "caution", "high_risk")
        assert "issues" in result, "Missing issues"
        assert isinstance(result["issues"], list)
        assert "suggestions" in result, "Missing suggestions"
        assert isinstance(result["suggestions"], list)
        assert "quality_notes" in result, "Missing quality_notes"
        assert "provider" in result, "Missing provider"
        print(f"  ✅ PASS [review_result_structure] all fields present, risk={result['risk_level']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [review_result_structure] {e}")
        traceback.print_exc()
        return False


def test_mock_provider_name():
    """MockModerationProvider.name == 'mock'"""
    try:
        from app.services.moderation.mock_provider import MockModerationProvider
        provider = MockModerationProvider()
        assert provider.name == "mock", f"Expected 'mock', got {provider.name}"
        print(f"  ✅ PASS [mock_provider_name] name={provider.name}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [mock_provider_name] {e}")
        traceback.print_exc()
        return False


def test_openai_skeleton_falls_back_to_mock():
    """OpenAI provider skeleton falls back to mock when not enabled"""
    try:
        from app.services.moderation.openai_provider import OpenAIModerationProvider
        provider = OpenAIModerationProvider()
        result = provider.review("测试故事", "")
        assert result.provider == "mock", f"Expected mock fallback, got {result.provider}"
        print(f"  ✅ PASS [openai_skeleton_fallback] provider={result.provider}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [openai_skeleton_fallback] {e}")
        traceback.print_exc()
        return False


def test_baidu_skeleton_falls_back_to_mock():
    """Baidu provider skeleton falls back to mock when not enabled"""
    try:
        from app.services.moderation.baidu_provider import BaiduModerationProvider
        provider = BaiduModerationProvider()
        result = provider.review("测试故事", "")
        assert result.provider == "mock", f"Expected mock fallback, got {result.provider}"
        print(f"  ✅ PASS [baidu_skeleton_fallback] provider={result.provider}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [baidu_skeleton_fallback] {e}")
        traceback.print_exc()
        return False


def test_moderation_result_to_dict():
    """ModerationResult.to_dict() 正确序列化"""
    try:
        from app.services.moderation.mock_provider import MockModerationProvider
        provider = MockModerationProvider()
        result = provider.review("搬家时整理出来的闲置物品，状态很好，希望找到需要的人。", "")
        d = result.to_dict()
        assert "risk_level" in d
        assert "issues" in d
        assert "suggestions" in d
        assert "quality_notes" in d
        assert "provider" in d
        assert "overall_score" in d
        assert isinstance(d["issues"], list)
        print(f"  ✅ PASS [moderation_result_to_dict] keys={list(d.keys())}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [moderation_result_to_dict] {e}")
        traceback.print_exc()
        return False


def main():
    tests = [
        test_factory_default_mock,
        test_factory_fallback_openai_no_enable,
        test_factory_fallback_unknown,
        test_mock_provider_detects_high_risk,
        test_mock_provider_normal_story,
        test_review_story_returns_provider_field,
        test_review_result_structure,
        test_mock_provider_name,
        test_openai_skeleton_falls_back_to_mock,
        test_baidu_skeleton_falls_back_to_mock,
        test_moderation_result_to_dict,
    ]

    results = []
    for t in tests:
        try:
            results.append(t())
        except Exception as e:
            print(f"  ❌ CRASH in {t.__name__}: {e}")
            traceback.print_exc()
            results.append(False)

    passed = sum(results)
    total = len(results)
    print(f"\nResult: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASSED ✅")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED ❌")
        sys.exit(1)


if __name__ == "__main__":
    main()
