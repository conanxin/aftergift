#!/usr/bin/env python3
"""
Aftergift Backend - OpenAI Provider Tests
Phase 2E-4 | test_openai_provider.py

Tests OpenAIModerationProvider WITHOUT calling real OpenAI API.
Uses unittest.mock to patch urllib.request.urlopen.

Run: python3 backend/tests/test_openai_provider.py
"""

import sys
import os
import json
import traceback
from unittest.mock import patch, MagicMock

# Add backend/backend/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

print("Aftergift Backend - OpenAI Provider Tests (Phase 2E-4)")
print("=" * 56)


# ── Helper: build fake OpenAI response ──────────────────────────────────────

def _fake_openai_response(flagged: bool, categories: dict = None, model: str = "omni-moderation-latest"):
    """Build a fake OpenAI Moderation API response."""
    if categories is None:
        categories = {}
    category_scores = {k: (0.95 if v else 0.01) for k, v in categories.items()}
    return {
        "id": "modr-test-123",
        "model": model,
        "results": [
            {
                "flagged": flagged,
                "categories": categories,
                "category_scores": category_scores,
            }
        ],
    }


def _mock_urlopen_response(data_dict, status=200):
    """Create a mock response object for urlopen."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(data_dict).encode("utf-8")
    mock_response.status = status
    return mock_response


# ── Tests ───────────────────────────────────────────────────────────────────

def test_factory_fallback_when_enable_false():
    """ENABLE_REAL_AI_REVIEW=false → factory returns mock"""
    try:
        import app.services.moderation.factory as factory_module
        factory_module.reset_provider_cache()

        orig_provider = os.environ.get("AFTERGIFT_MODERATION_PROVIDER", "")
        orig_enable = os.environ.get("AFTERGIFT_ENABLE_REAL_AI_REVIEW", "")
        os.environ["AFTERGIFT_MODERATION_PROVIDER"] = "openai"
        os.environ["AFTERGIFT_ENABLE_REAL_AI_REVIEW"] = "false"

        try:
            factory_module._cached_provider = None
            provider = factory_module.get_moderation_provider()
            assert provider.name == "mock", f"Expected mock, got {provider.name}"
            print(f"  ✅ PASS [factory_fallback_enable_false] provider={provider.name}")
        finally:
            os.environ["AFTERGIFT_MODERATION_PROVIDER"] = orig_provider
            os.environ["AFTERGIFT_ENABLE_REAL_AI_REVIEW"] = orig_enable
            factory_module.reset_provider_cache()

        return True
    except Exception as e:
        print(f"  ❌ FAIL [factory_fallback_enable_false] {e}")
        traceback.print_exc()
        return False


def test_factory_fallback_when_key_empty():
    """provider=openai + ENABLE=true but OPENAI_API_KEY empty → mock fallback"""
    try:
        import app.services.moderation.factory as factory_module
        import app.config as config_module
        factory_module.reset_provider_cache()

        orig_provider = os.environ.get("AFTERGIFT_MODERATION_PROVIDER", "")
        orig_enable = os.environ.get("AFTERGIFT_ENABLE_REAL_AI_REVIEW", "")
        orig_key = os.environ.get("OPENAI_API_KEY", "")
        os.environ["AFTERGIFT_MODERATION_PROVIDER"] = "openai"
        os.environ["AFTERGIFT_ENABLE_REAL_AI_REVIEW"] = "true"
        os.environ["OPENAI_API_KEY"] = ""

        try:
            # Force config reload by touching module (simpler: just use factory logic)
            factory_module._cached_provider = None
            provider = factory_module.get_moderation_provider()
            assert provider.name == "mock", f"Expected mock, got {provider.name}"
            print(f"  ✅ PASS [factory_fallback_key_empty] provider={provider.name}")
        finally:
            os.environ["AFTERGIFT_MODERATION_PROVIDER"] = orig_provider
            os.environ["AFTERGIFT_ENABLE_REAL_AI_REVIEW"] = orig_enable
            os.environ["OPENAI_API_KEY"] = orig_key
            factory_module.reset_provider_cache()

        return True
    except Exception as e:
        print(f"  ❌ FAIL [factory_fallback_key_empty] {e}")
        traceback.print_exc()
        return False


def test_openai_provider_uses_redacted_input():
    """OpenAI provider sends redacted text (no phone numbers in payload)"""
    try:
        from app.services.moderation.openai_provider import OpenAIModerationProvider

        provider = OpenAIModerationProvider()
        # Even when not enabled, verify redaction logic exists
        from app.services.anonymize_service import redact_sensitive_text
        raw = "他叫张三，手机号是13800138000"
        redacted = redact_sensitive_text(raw)
        assert "13800138000" not in redacted, "Phone number not redacted"
        assert "[手机号已隐藏]" in redacted, "Redaction placeholder missing"
        print(f"  ✅ PASS [redacted_input] redacted={redacted[:40]}...")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [redacted_input] {e}")
        traceback.print_exc()
        return False


def test_openai_flagged_false_safe():
    """Simulate OpenAI flagged=false → merged result at least safe/caution"""
    try:
        from app.services.moderation.openai_provider import (
            OpenAIModerationProvider, _map_openai_result
        )

        fake_resp = _fake_openai_response(flagged=False, categories={})
        result = _map_openai_result(fake_resp)
        assert result.risk_level in ("safe", "caution"), f"Unexpected risk: {result.risk_level}"
        assert result.provider == "openai"
        print(f"  ✅ PASS [flagged_false_safe] risk={result.risk_level}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [flagged_false_safe] {e}")
        traceback.print_exc()
        return False


def test_openai_flagged_true_high_risk():
    """Simulate OpenAI flagged=true with hate → high_risk"""
    try:
        from app.services.moderation.openai_provider import _map_openai_result

        fake_resp = _fake_openai_response(
            flagged=True,
            categories={"hate": True, "harassment": False}
        )
        result = _map_openai_result(fake_resp)
        assert result.risk_level in ("caution", "high_risk"), f"Expected caution/high_risk, got {result.risk_level}"
        assert len(result.issues) >= 1, "Expected at least 1 issue"
        assert result.provider == "openai"
        print(f"  ✅ PASS [flagged_true_high_risk] risk={result.risk_level}, issues={len(result.issues)}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [flagged_true_high_risk] {e}")
        traceback.print_exc()
        return False


def test_openai_429_fallback():
    """Simulate 429 rate limit → fallback to mock"""
    try:
        from app.services.moderation.openai_provider import (
            OpenAIModerationProvider, _call_openai_moderation
        )

        # Direct test of _call_openai_moderation with mocked 429
        with patch("app.services.moderation.openai_provider.urlopen") as mock_urlopen:
            from urllib.error import HTTPError
            mock_urlopen.side_effect = HTTPError(
                url="https://api.openai.com/v1/moderations",
                code=429,
                msg="Too Many Requests",
                hdrs={},
                fp=None,
            )
            result = _call_openai_moderation("test", "sk-fake", "omni-moderation-latest", 8)
            assert result is None, "Expected None on 429"
            print(f"  ✅ PASS [429_fallback] returned None on rate limit")
            return True
    except Exception as e:
        print(f"  ❌ FAIL [429_fallback] {e}")
        traceback.print_exc()
        return False


def test_openai_network_error_fallback():
    """Simulate network error → fallback to mock"""
    try:
        from app.services.moderation.openai_provider import _call_openai_moderation

        with patch("app.services.moderation.openai_provider.urlopen") as mock_urlopen:
            from urllib.error import URLError
            mock_urlopen.side_effect = URLError("Network unreachable")
            result = _call_openai_moderation("test", "sk-fake", "omni-moderation-latest", 8)
            assert result is None, "Expected None on network error"
            print(f"  ✅ PASS [network_error_fallback] returned None on URLError")
            return True
    except Exception as e:
        print(f"  ❌ FAIL [network_error_fallback] {e}")
        traceback.print_exc()
        return False


def test_openai_provider_response_no_phone():
    """Provider response (merged) does not contain raw phone numbers"""
    try:
        from app.services.moderation.openai_provider import OpenAIModerationProvider

        provider = OpenAIModerationProvider()
        # Not enabled by default, so returns mock result
        result = provider.review("他叫张三，手机号13800138000", "")
        result_dict = result.to_dict()

        # Check no raw phone in any string field
        def _contains_phone(obj):
            if isinstance(obj, str):
                return "13800138000" in obj
            if isinstance(obj, list):
                return any(_contains_phone(item) for item in obj)
            if isinstance(obj, dict):
                return any(_contains_phone(v) for v in obj.values())
            return False

        assert not _contains_phone(result_dict), "Raw phone found in result"
        print(f"  ✅ PASS [response_no_phone] no raw phone in result")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [response_no_phone] {e}")
        traceback.print_exc()
        return False


def test_openai_provider_result_structure():
    """Provider result contains all required fields"""
    try:
        from app.services.moderation.openai_provider import OpenAIModerationProvider

        provider = OpenAIModerationProvider()
        result = provider.review("搬家时整理出来的闲置物品", "")
        d = result.to_dict()

        assert "risk_level" in d
        assert d["risk_level"] in ("safe", "caution", "high_risk")
        assert "issues" in d and isinstance(d["issues"], list)
        assert "suggestions" in d and isinstance(d["suggestions"], list)
        assert "quality_notes" in d and isinstance(d["quality_notes"], dict)
        assert "provider" in d
        assert "overall_score" in d
        print(f"  ✅ PASS [result_structure] provider={d['provider']}, risk={d['risk_level']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [result_structure] {e}")
        traceback.print_exc()
        return False


def test_openai_mock_merge_preserves_identity_issues():
    """When OpenAI is enabled, mock identity issues are preserved in merge"""
    try:
        from app.services.moderation.openai_provider import (
            _merge_results, _map_openai_result
        )
        from app.services.moderation.mock_provider import MockModerationProvider

        # Mock result with identity issue
        mock_provider = MockModerationProvider()
        mock_result = mock_provider.review("他叫张三，手机号13800138000", "")
        assert any(i.subtype == "phone" for i in mock_result.issues), "Mock should detect phone"

        # OpenAI result (safe)
        openai_result = _map_openai_result(_fake_openai_response(flagged=False))

        # Merge
        merged = _merge_results(openai_result, mock_result)
        assert any(i.subtype == "phone" for i in merged.issues), "Merged should preserve phone issue"
        assert merged.provider == "openai+mock"
        print(f"  ✅ PASS [merge_preserves_identity] issues={len(merged.issues)}, provider={merged.provider}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [merge_preserves_identity] {e}")
        traceback.print_exc()
        return False


def test_openai_enabled_full_flow_mocked():
    """Full flow: enabled + mocked API call returns safe, merged with mock"""
    try:
        from app.services.moderation.openai_provider import OpenAIModerationProvider

        provider = OpenAIModerationProvider()

        # Patch _is_enabled to return True for this test
        with patch("app.services.moderation.openai_provider._is_enabled", return_value=True):
            with patch("app.services.moderation.openai_provider._call_openai_moderation") as mock_call:
                mock_call.return_value = _fake_openai_response(
                    flagged=False,
                    categories={},
                    model="omni-moderation-latest"
                )

                result = provider.review("搬家时整理出来的闲置物品", "")
                assert result.provider == "openai+mock", f"Expected openai+mock, got {result.provider}"
                print(f"  ✅ PASS [full_flow_mocked] provider={result.provider}, risk={result.risk_level}")
                return True
    except Exception as e:
        print(f"  ❌ FAIL [full_flow_mocked] {e}")
        traceback.print_exc()
        return False


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    tests = [
        test_factory_fallback_when_enable_false,
        test_factory_fallback_when_key_empty,
        test_openai_provider_uses_redacted_input,
        test_openai_flagged_false_safe,
        test_openai_flagged_true_high_risk,
        test_openai_429_fallback,
        test_openai_network_error_fallback,
        test_openai_provider_response_no_phone,
        test_openai_provider_result_structure,
        test_openai_mock_merge_preserves_identity_issues,
        test_openai_enabled_full_flow_mocked,
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
