#!/usr/bin/env python3
"""
Aftergift Backend - Redaction Tests
Phase 2E-3 | test_redaction.py

不依赖 pytest，可作为普通 Python 脚本运行。
测试脱敏函数：redact_sensitive_text, summarize_redactions, safe_excerpt, redact_review_result
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import traceback

print("Aftergift Backend - Redaction Tests (Phase 2E-3)")
print("=" * 50)


def test_phone_redaction():
    """手机号脱敏"""
    try:
        from app.services.anonymize_service import redact_sensitive_text
        text = "我的手机号是13800138000，请联系我。"
        result = redact_sensitive_text(text)
        assert "13800138000" not in result, f"Phone not redacted: {result}"
        assert "[手机号已隐藏]" in result, f"Label missing: {result}"
        print(f"  ✅ PASS [phone] {result}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [phone] {e}")
        traceback.print_exc()
        return False


def test_email_redaction():
    """邮箱脱敏"""
    try:
        from app.services.anonymize_service import redact_sensitive_text
        text = "发邮件到 test@example.com 给我。"
        result = redact_sensitive_text(text)
        assert "test@example.com" not in result, f"Email not redacted: {result}"
        assert "[邮箱已隐藏]" in result, f"Label missing: {result}"
        print(f"  ✅ PASS [email] {result}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [email] {e}")
        traceback.print_exc()
        return False


def test_wechat_redaction():
    """微信账号脱敏"""
    try:
        from app.services.anonymize_service import redact_sensitive_text
        text = "微信号：wx_test_123，加我吧。"
        result = redact_sensitive_text(text)
        assert "wx_test_123" not in result, f"WeChat not redacted: {result}"
        assert "[社交账号已隐藏]" in result, f"Label missing: {result}"
        print(f"  ✅ PASS [wechat] {result}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [wechat] {e}")
        traceback.print_exc()
        return False


def test_qq_redaction():
    """QQ号脱敏"""
    try:
        from app.services.anonymize_service import redact_sensitive_text
        text = "QQ：123456789"
        result = redact_sensitive_text(text)
        assert "123456789" not in result, f"QQ not redacted: {result}"
        assert "[社交账号已隐藏]" in result, f"Label missing: {result}"
        print(f"  ✅ PASS [qq] {result}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [qq] {e}")
        traceback.print_exc()
        return False


def test_address_redaction():
    """地址类词脱敏"""
    try:
        from app.services.anonymize_service import redact_sensitive_text
        text = "我们住在某某小区3号楼2单元。"
        result = redact_sensitive_text(text)
        assert "3号楼" not in result or "[地点信息已隐藏]" in result, f"Address not redacted: {result}"
        print(f"  ✅ PASS [address] {result}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [address] {e}")
        traceback.print_exc()
        return False


def test_name_pattern_redaction():
    """他叫某某脱敏"""
    try:
        from app.services.anonymize_service import redact_sensitive_text
        text = "他叫张三，是个很好的人。"
        result = redact_sensitive_text(text)
        assert "张三" not in result, f"Name not redacted: {result}"
        assert "[姓名已隐藏]" in result, f"Label missing: {result}"
        print(f"  ✅ PASS [name_pattern] {result}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [name_pattern] {e}")
        traceback.print_exc()
        return False


def test_safe_excerpt():
    """safe_excerpt 先脱敏再截断"""
    try:
        from app.services.anonymize_service import safe_excerpt
        text = "他叫张三，手机号是13800138000。" + "这是一个很长的故事。" * 20
        result = safe_excerpt(text, limit=50)
        assert "13800138000" not in result, f"Phone in excerpt: {result}"
        assert "张三" not in result, f"Name in excerpt: {result}"
        assert len(result) <= 53, f"Excerpt too long: {len(result)} chars"
        assert result.endswith("..."), f"Excerpt not truncated: {result}"
        print(f"  ✅ PASS [safe_excerpt] len={len(result)}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [safe_excerpt] {e}")
        traceback.print_exc()
        return False


def test_summarize_redactions():
    """summarize_redactions 不包含原始敏感值"""
    try:
        from app.services.anonymize_service import summarize_redactions, redact_sensitive_text
        original = "手机号13800138000，邮箱test@example.com"
        redacted = redact_sensitive_text(original)
        summary = summarize_redactions(original, redacted)
        assert summary["redacted"] is True, f"Should be redacted: {summary}"
        assert summary["redaction_count"] >= 2, f"Count too low: {summary}"
        assert "phone" in summary["categories"], f"Missing phone: {summary}"
        assert "email" in summary["categories"], f"Missing email: {summary}"
        # Must NOT contain original values
        summary_str = str(summary)
        assert "13800138000" not in summary_str, f"Original leaked in summary!"
        assert "test@example.com" not in summary_str, f"Original leaked in summary!"
        print(f"  ✅ PASS [summarize] categories={summary['categories']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [summarize] {e}")
        traceback.print_exc()
        return False


def test_redact_review_result_issues():
    """review_result issues evidence 经脱敏后不含手机号"""
    try:
        from app.services.anonymize_service import redact_review_result
        review_result = {
            "risk_level": "high_risk",
            "issues": [
                {"category": "identity", "severity": "high", "original": "手机号13800138000"},
                {"category": "identity", "severity": "medium", "original": "他叫张三"},
            ],
            "suggestions": [
                {"type": "phone", "original": "手机号13800138000", "message": "删除手机号13800138000", "suggestion": "后来不再联系"},
            ],
            "quality_notes": {},
            "overall_score": 30,
            "provider": "mock",
        }
        redacted = redact_review_result(review_result)
        for issue in redacted["issues"]:
            assert "13800138000" not in str(issue.get("original", "")), f"Phone in issue: {issue}"
            assert "张三" not in str(issue.get("original", "")), f"Name in issue: {issue}"
        for sug in redacted["suggestions"]:
            assert "13800138000" not in str(sug.get("original", "")), f"Phone in suggestion: {sug}"
            assert "13800138000" not in str(sug.get("message", "")), f"Phone in message: {sug}"
        assert "redaction_summary" in redacted, "Missing redaction_summary"
        assert redacted["redaction_summary"]["redacted"] is True, "Should be redacted"
        print(f"  ✅ PASS [review_result] redacted={redacted['redaction_summary']['redacted']}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [review_result] {e}")
        traceback.print_exc()
        return False


def test_gentle_story_not_over_redacted():
    """普通温柔故事不会被过度脱敏"""
    try:
        from app.services.anonymize_service import redact_sensitive_text
        text = "这是一盏暖黄的台灯，陪伴我度过了三年的夜晚。现在我想把它送给需要的人。"
        result = redact_sensitive_text(text)
        # Should NOT contain any redaction labels
        assert "[手机号已隐藏]" not in result, f"False positive phone: {result}"
        assert "[姓名已隐藏]" not in result, f"False positive name: {result}"
        assert "[邮箱已隐藏]" not in result, f"False positive email: {result}"
        # Should be mostly unchanged
        assert "暖黄的台灯" in result, f"Content lost: {result}"
        print(f"  ✅ PASS [gentle_story] no false positives")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [gentle_story] {e}")
        traceback.print_exc()
        return False


def test_suggestions_json_no_sensitive():
    """suggestions_json 中不含原始敏感值"""
    try:
        from app.services.anonymize_service import redact_review_result
        review_result = {
            "risk_level": "high_risk",
            "issues": [],
            "suggestions": [
                {"type": "phone", "original": "13800138000", "message": "发现手机号13800138000", "replacement": "删除13800138000"},
            ],
            "quality_notes": {},
            "overall_score": 30,
            "provider": "mock",
        }
        redacted = redact_review_result(review_result)
        for sug in redacted["suggestions"]:
            assert "13800138000" not in str(sug), f"Phone leaked: {sug}"
        print(f"  ✅ PASS [suggestions_json] no sensitive values")
        return True
    except Exception as e:
        print(f"  ❌ FAIL [suggestions_json] {e}")
        traceback.print_exc()
        return False


def main():
    tests = [
        test_phone_redaction,
        test_email_redaction,
        test_wechat_redaction,
        test_qq_redaction,
        test_address_redaction,
        test_name_pattern_redaction,
        test_safe_excerpt,
        test_summarize_redactions,
        test_redact_review_result_issues,
        test_gentle_story_not_over_redacted,
        test_suggestions_json_no_sensitive,
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
