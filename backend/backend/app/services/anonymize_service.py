"""
Aftergift Backend - Anonymization Service
Phase 2B | 轻量匿名化建议函数，不自动修改用户内容
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

# ── Rewrite Suggestions ────────────────────────────────────────────────────────

_ANON_SUGGESTIONS: Dict[str, Dict] = {
    "phone": {
        "reason": "手机号可直接定位到具体个人",
        "suggestion": "后来我们不再联系了"
    },
    "wechat": {
        "reason": "微信号可加好友、获取朋友圈信息",
        "suggestion": "我们后来失去了联系"
    },
    "qq": {
        "reason": "QQ号可查询个人信息和历史动态",
        "suggestion": "我们后来失去了联系"
    },
    "email": {
        "reason": "邮箱可作为登录凭证或联系方式",
        "suggestion": "我们后来失去了联系"
    },
    "address": {
        "reason": "具体地址可精确定位居住地点",
        "suggestion": "我们曾经住的地方 / 后来搬到了不同的地方"
    },
    "social": {
        "reason": "社交平台账号可获取更多个人信息",
        "suggestion": "我们后来在不同的平台上各自生活"
    },
    "name_pattern": {
        "reason": "直接暴露他人姓名，违反匿名原则",
        "suggestion": "那个人 / TA / 我曾在乎的人"
    },
    "revenge_words": {
        "reason": "报复性词汇会引发对立情绪，与平台温和流转的定位冲突",
        "suggestion": "这段关系让我失去了信任 / 让我感到受伤"
    },
    "curse": {
        "reason": "诅咒类表达会升级冲突，不符合温和告别原则",
        "suggestion": "把感受写出来，但不要用伤害性的语言"
    },
}


# ── Service Functions ─────────────────────────────────────────────────────────

def detect_identity_patterns(text: str) -> List[Dict]:
    """
    检测文本中的身份信息模式。

    Returns:
        List of detected patterns, each with: type, matched_text, position
    """
    findings = []
    combined = text  # In production, combine short_story + full_story

    for pattern_name, pattern in _IDENTITY_PATTERNS.items():
        matches = pattern.findall(combined)
        if matches:
            for match in matches:
                findings.append({
                    "type": pattern_name,
                    "matched_text": str(match) if match else pattern_name,
                    "reason": _ANON_SUGGESTIONS.get(pattern_name, {}).get("reason", "未知风险")
                })

    # Revenge words
    if _REVENGE_PATTERNS.search(combined):
        findings.append({
            "type": "revenge_words",
            "matched_text": "报复性词汇",
            "reason": _ANON_SUGGESTIONS["revenge_words"]["reason"]
        })

    # Curse words
    if _CURSE_PATTERNS.search(combined):
        findings.append({
            "type": "curse",
            "matched_text": "诅咒表达",
            "reason": _ANON_SUGGESTIONS["curse"]["reason"]
        })

    return findings


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
        if pattern_type in _ANON_SUGGESTIONS:
            suggestions.append({
                "type": _get_readable_type(pattern_type),
                "original": finding["matched_text"],
                "reason": finding["reason"],
                "suggestion": _ANON_SUGGESTIONS[pattern_type]["suggestion"]
            })

    return suggestions


def _get_readable_type(pattern_type: str) -> str:
    """将内部类型名转换为可读标签。"""
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


def mask_sensitive_text(text: str) -> str:
    """
    对敏感信息进行脱敏遮盖（用于展示，不修改原始数据）。
    这是一个可选的辅助函数，用于在某些展示场景下遮盖敏感信息。

    注意：这个函数不修改数据库中的原始数据，只是生成脱敏后的展示文本。
    """
    result = text
    result = _IDENTITY_PATTERNS["phone"].sub("[手机号已遮蔽]", result)
    result = _IDENTITY_PATTERNS["wechat"].sub("[微信号已遮蔽]", result)
    result = _IDENTITY_PATTERNS["qq"].sub("[QQ号已遮蔽]", result)
    result = _IDENTITY_PATTERNS["email"].sub("[邮箱已遮蔽]", result)
    return result
