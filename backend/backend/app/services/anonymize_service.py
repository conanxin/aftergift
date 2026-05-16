"""
Aftergift Backend - Anonymization Service
Phase 2E-3 | Review Log Redaction

Enhanced with redaction functions for audit trail privacy:
1. redact_sensitive_text() — replaces PII with placeholders
2. summarize_redactions() — records what was redacted (without storing originals)
3. safe_excerpt() — redact then truncate for log views

Design principle: review_logs should NEVER store raw PII.
"""

import re
from typing import List, Dict

# ── Detection Patterns ────────────────────────────────────────────────────────

_IDENTITY_PATTERNS = {
    "phone": re.compile(r'(?<!\d)1[3-9]\d[\s\-]?\d{4}[\s\-]?\d{4}(?!\d)'),
    "wechat": re.compile(
        r'(?:微信号|微信[：:\s]|WeChat|wechat|wx[_\s]?id|WX[_\s]?id|'
        r'加我微信|加微信|私聊我|联系我微信)[：:\s]*[a-zA-Z0-9_\-]{5,}',
        re.IGNORECASE
    ),
    "qq": re.compile(r'(?:QQ[：:\s]*|qq[：:\s]*)[1-9]\d{4,}(?!\d)'),
    "email": re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'),
    "address": re.compile(
        r'(?:小区|苑|花园|城|栋|号楼?|单元|门牌|房号?|'
        r'路\s*\d+|街\s*\d+|弄|巷|坡|坪|楼|室)[^\s，。,\.]*',
        re.IGNORECASE
    ),
    "social": re.compile(
        r'(?:微博|抖音|小红书|Instagram|Twitter|Mastodon|'
        r'Telegram|t\.me|@|github)[^\s，。,\.]+',
        re.IGNORECASE
    ),
    "name_pattern": re.compile(
        r'(?:TA?[叫管是]+|她?叫|他?叫)[^\s，。,\.]+',
        re.IGNORECASE
    ),
}

_REVENGE_PATTERNS = re.compile(
    r'(?:渣男|渣女|妈宝男|扶弟魔|报复|曝光|挂人|人肉|'
    r'骗子|毁掉|滚开|不要脸|下头)[^\s，。,\.]*',
    re.IGNORECASE
)

_CURSE_PATTERNS = re.compile(
    r'(?:去死|该死|恨死|恶心死了|想打|想杀|想弄死|想毁掉)'
    r'((?:他|她|它|这|那个|此人)?[^\s，。,\.]*)?',
    re.IGNORECASE
)

# ── Redaction Placeholders ────────────────────────────────────────────────────

_REDACTION_LABELS = {
    "phone": "[手机号已隐藏]",
    "wechat": "[社交账号已隐藏]",
    "qq": "[社交账号已隐藏]",
    "email": "[邮箱已隐藏]",
    "address": "[地点信息已隐藏]",
    "social": "[社交账号已隐藏]",
    "name_pattern": "[姓名已隐藏]",
    "revenge_words": "[不当表达已隐藏]",
    "curse": "[不当表达已隐藏]",
}


# ── Service Functions ─────────────────────────────────────────────────────────

def detect_identity_patterns(text: str) -> List[Dict]:
    """
    检测文本中的身份信息模式。

    Returns:
        List of detected patterns, each with: type, matched_text, position
    """
    findings = []
    combined = text

    for pattern_name, pattern in _IDENTITY_PATTERNS.items():
        matches = pattern.findall(combined)
        if matches:
            for match in matches:
                findings.append({
                    "type": pattern_name,
                    "matched_text": str(match) if match else pattern_name,
                    "reason": _get_reason(pattern_name)
                })

    # Revenge words
    if _REVENGE_PATTERNS.search(combined):
        findings.append({
            "type": "revenge_words",
            "matched_text": "报复性词汇",
            "reason": _get_reason("revenge_words")
        })

    # Curse words
    if _CURSE_PATTERNS.search(combined):
        findings.append({
            "type": "curse",
            "matched_text": "诅咒表达",
            "reason": _get_reason("curse")
        })

    return findings


def _get_reason(pattern_type: str) -> str:
    reasons = {
        "phone": "发现手机号，可能暴露具体个人",
        "wechat": "发现微信号，可能暴露具体个人",
        "qq": "发现QQ号，可能暴露具体个人",
        "email": "发现邮箱地址，可能暴露具体个人",
        "address": "发现详细地址，可精确定位居住地点",
        "social": "发现社交平台账号，可能暴露具体个人",
        "name_pattern": "直接暴露他人姓名，违反匿名原则",
        "revenge_words": "报复性词汇会引发对立情绪",
        "curse": "诅咒类表达会升级冲突",
    }
    return reasons.get(pattern_type, "未知风险")


def redact_sensitive_text(text: str) -> str:
    """
    对文本中的敏感信息进行脱敏替换。

    替换规则：
    - 手机号 → [手机号已隐藏]
    - 邮箱 → [邮箱已隐藏]
    - 微信/QQ/社交账号 → [社交账号已隐藏]
    - 详细地址 → [地点信息已隐藏]
    - 姓名暴露模式 → [姓名已隐藏]

    Args:
        text: 原始文本

    Returns:
        脱敏后的文本
    """
    result = text

    # Phone numbers
    result = _IDENTITY_PATTERNS["phone"].sub(_REDACTION_LABELS["phone"], result)

    # WeChat IDs
    result = _IDENTITY_PATTERNS["wechat"].sub(
        lambda m: _redact_match(m, _REDACTION_LABELS["wechat"]), result
    )

    # QQ numbers
    result = _IDENTITY_PATTERNS["qq"].sub(
        lambda m: _redact_match(m, _REDACTION_LABELS["qq"]), result
    )

    # Email addresses
    result = _IDENTITY_PATTERNS["email"].sub(_REDACTION_LABELS["email"], result)

    # Address patterns — more strict to avoid false positives
    result = _IDENTITY_PATTERNS["address"].sub(
        lambda m: _redact_address_match(m, _REDACTION_LABELS["address"]), result
    )

    # Social media accounts
    result = _IDENTITY_PATTERNS["social"].sub(
        lambda m: _redact_match(m, _REDACTION_LABELS["social"]), result
    )

    # Name patterns ("他叫张三" → "他叫[姓名已隐藏]")
    result = _IDENTITY_PATTERNS["name_pattern"].sub(
        lambda m: _redact_name_pattern(m, _REDACTION_LABELS["name_pattern"]), result
    )

    return result


def _redact_address_match(match, label: str) -> str:
    """Helper: only redact if match contains digits or specific address keywords."""
    full = match.group(0)
    # Must contain at least one digit (for 3号楼, 路123, etc.) or be longer than 2 chars after keyword
    has_digit = any(c.isdigit() for c in full)
    # Or contains specific address sub-keywords
    has_address_detail = any(kw in full for kw in ['号楼', '单元', '门牌', '房号', '栋', '室', '弄', '巷'])
    if has_digit or has_address_detail:
        return label
    # False positive — don't redact
    return full


def _redact_match(match, label: str) -> str:
    """Helper: replace the matched portion after the keyword with label."""
    full = match.group(0)
    # Find where the actual value starts (after Chinese punctuation or whitespace)
    for i, ch in enumerate(full):
        if ch in ':：\s':
            return full[:i+1] + label
    # If no separator found, replace the whole match
    return label


def _redact_name_pattern(match, label: str) -> str:
    """Helper: replace name after '他叫' etc."""
    full = match.group(0)
    # Find the name part after the prefix
    for prefix in ['叫', '管', '是']:
        idx = full.find(prefix)
        if idx != -1:
            return full[:idx+1] + label
    return label


def summarize_redactions(original: str, redacted: str) -> Dict:
    """
    记录脱敏操作的摘要（不包含原始敏感值）。

    Args:
        original: 原始文本
        redacted: 脱敏后的文本

    Returns:
        {
            "redacted": bool,
            "redaction_count": int,
            "categories": ["phone", "email", ...]
        }
    """
    if original == redacted:
        return {"redacted": False, "redaction_count": 0, "categories": []}

    categories = set()
    count = 0

    for cat, label in _REDACTION_LABELS.items():
        if label in redacted:
            categories.add(cat)
            count += redacted.count(label)

    return {
        "redacted": True,
        "redaction_count": count,
        "categories": sorted(list(categories))
    }


def safe_excerpt(text: str, limit: int = 120) -> str:
    """
    先脱敏，再截断文本，用于日志和列表展示。

    Args:
        text: 原始文本
        limit: 最大字符数

    Returns:
        脱敏并截断后的文本
    """
    redacted = redact_sensitive_text(text)
    if len(redacted) <= limit:
        return redacted
    return redacted[:limit] + "..."


def redact_review_result(review_result: Dict) -> Dict:
    """
    对 review_result 中的 issues 和 suggestions 进行脱敏。

    重点脱敏字段：
    - issues[*].original (evidence)
    - suggestions[*].original
    - suggestions[*].message (可能包含原始值)
    - suggestions[*].replacement (可能包含原始值)

    Args:
        review_result: provider.review() 返回的 dict

    Returns:
        脱敏后的 review_result dict
    """
    import copy
    result = copy.deepcopy(review_result)

    # Redact issues evidence
    if "issues" in result and isinstance(result["issues"], list):
        for issue in result["issues"]:
            if "original" in issue and issue["original"]:
                issue["original"] = redact_sensitive_text(str(issue["original"]))

    # Redact suggestions
    if "suggestions" in result and isinstance(result["suggestions"], list):
        for suggestion in result["suggestions"]:
            if "original" in suggestion and suggestion["original"]:
                suggestion["original"] = redact_sensitive_text(str(suggestion["original"]))
            if "message" in suggestion and suggestion["message"]:
                suggestion["message"] = redact_sensitive_text(str(suggestion["message"]))
            if "replacement" in suggestion and suggestion["replacement"]:
                suggestion["replacement"] = redact_sensitive_text(str(suggestion["replacement"]))

    # Add redaction summary
    # Build combined from ORIGINAL values (before redaction) to detect changes
    original_combined = ""
    for issue in review_result.get("issues", []):
        original_combined += str(issue.get("original", "")) + " "
    for suggestion in review_result.get("suggestions", []):
        original_combined += str(suggestion.get("original", "")) + " "
        original_combined += str(suggestion.get("message", "")) + " "

    redacted_combined = redact_sensitive_text(original_combined)
    result["redaction_summary"] = summarize_redactions(original_combined, redacted_combined)

    return result


# ── Legacy functions (kept for backward compatibility) ──────────────────────────

def suggest_rewrites(text: str) -> List[Dict]:
    """
    为检测到的身份信息提供匿名化改写建议。

    Returns:
        List of rewrite suggestions, each with: type, original, reason, suggestion
    """
    findings = detect_identity_patterns(text)
    suggestions = []

    for finding in findings:
        pattern_type = finding["type"]
        suggestions.append({
            "type": _get_readable_type(pattern_type),
            "original": finding["matched_text"],
            "reason": finding["reason"],
            "suggestion": _get_suggestion(pattern_type)
        })

    return suggestions


def _get_readable_type(pattern_type: str) -> str:
    type_map = {
        "phone": "手机号码",
        "wechat": "微信号",
        "qq": "QQ号",
        "email": "邮箱地址",
        "address": "详细地址",
        "social": "社交平台账号",
        "name_pattern": "姓名暴露模式",
        "revenge_words": "报复性词汇",
        "curse": "诅咒表达",
    }
    return type_map.get(pattern_type, pattern_type)


def _get_suggestion(pattern_type: str) -> str:
    suggestions = {
        "phone": "后来我们不再联系了",
        "wechat": "我们后来失去了联系",
        "qq": "我们后来失去了联系",
        "email": "我们后来失去了联系",
        "address": "我们曾经住的地方 / 后来搬到了不同的地方",
        "social": "我们后来在不同的平台上各自生活",
        "name_pattern": "那个人 / TA / 我曾在乎的人",
        "revenge_words": "这段关系让我失去了信任 / 让我感到受伤",
        "curse": "把感受写出来，但不要用伤害性的语言",
    }
    return suggestions.get(pattern_type, "建议匿名化处理")


def mask_sensitive_text(text: str) -> str:
    """
    对敏感信息进行脱敏遮盖（用于展示，不修改原始数据）。

    这是 redact_sensitive_text 的别名，保持向后兼容。
    """
    return redact_sensitive_text(text)
