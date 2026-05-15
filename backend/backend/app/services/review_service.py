"""
Aftergift Backend - Review Service
Phase 2B | 复用 Phase 2A mock_review.py 的规则引擎逻辑
提供与 FastAPI/Pydantic 兼容的接口
"""

import re
import json
from typing import Dict, List

# ── Quality Check Definitions ────────────────────────────────────────────────

_QUALITY_CHECKS = [
    {
        "id": "word_count",
        "label": "字数",
        "check": lambda s: len(s) >= 50,
        "ok": "字数已达到基本要求",
        "fail": "再写一点点，别人会更理解这件礼物为什么重要"
    },
    {
        "id": "has_origin",
        "label": "来历",
        "check": lambda s: any(kw in s for kw in ['来', '得到', '收到', '赠', '送', '买', '当时', '生日', '纪念日', '那天']),
        "ok": "已说明礼物是如何来到你手上的",
        "fail": "可以补充一下礼物最初是怎么来到你手上的"
    },
    {
        "id": "has_meaning",
        "label": "意义",
        "check": lambda s: any(kw in s for kw in ['重要', '喜欢', '陪伴', '记得', '想起', '意义', '当时', '在乎', '珍惜', '价值']),
        "ok": "已写到它曾经对你意味着什么",
        "fail": "如果能再写一句它曾经对你意味着什么，这个故事会更完整"
    },
    {
        "id": "has_farewell_reason",
        "label": "告别理由",
        "check": lambda s: any(kw in s for kw in ['现在', '离开', '告别', '不再', '结束', '分开', '后来', '已经']),
        "ok": "已说明为什么想让这件礼物离开",
        "fail": "可以再写一句为什么现在想让这件礼物离开"
    },
    {
        "id": "has_next_hope",
        "label": "下一站",
        "check": lambda s: any(kw in s for kw in ['希望', '愿', '以后', '下一位', '去往', '有人', '喜欢', '用', '继续']),
        "ok": "已写到对这件礼物下一站的期望",
        "fail": "如果你愿意，可以再补一句希望这件礼物去往怎样的下一站"
    }
]

# ── Detection Patterns ────────────────────────────────────────────────────────

_PHONE_RE = re.compile(r'(?<!\d)1[3-9]\d[\s\-]?\d{4}[\s\-]?\d{4}(?!\d)')
_WECHAT_RE = re.compile(
    r'(?:微信号|微信[：:\s]|WeChat|wechat|wx[_\s]?id|WX[_\s]?id|'
    r'加我微信|加微信|私聊我|联系我微信)[：:\s]*[a-zA-Z0-9_\-]{5,}',
    re.IGNORECASE
)
_QQ_RE = re.compile(r'(?:QQ[：:\s]*|qq[：:\s]*)[1-9]\d{4,}(?!\d)')
_EMAIL_RE = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
_ADDRESS_RE = re.compile(
    r'(?:小区|苑|花园|城|栋|号楼?|单元|门牌|房号?|'
    r'路\s*\d+|街\s*\d+|弄|巷|坡|坪|楼)[^\s，。,\.]{1,20}',
    re.IGNORECASE
)
_SOCIAL_RE = re.compile(
    r'(?:微博|抖音|小红书|Instagram|Twitter|Mastodon|'
    r'Telegram|t\.me|@|github)[^\s，。,\.]+',
    re.IGNORECASE
)
_ID_RE = re.compile(
    r'(?:TA?[叫管是]+|她?叫|他?叫)[^\s，。,\.]+',
    re.IGNORECASE
)
_REVENGE_RE = re.compile(
    r'(?:渣男|渣女|妈宝男|扶弟魔|报复|曝光|挂人|人肉|'
    r'骗子|毁掉|滚开|不要脸|下头)[^\s，。,\.]*',
    re.IGNORECASE
)
_CURSE_RE = re.compile(
    r'(?:去死|该死|恨死|恶心死了|想打|想杀|想弄死|想毁掉)'
    r'((?:他|她|它|这|那个|此人)?[^\s，。,\.]*)?',
    re.IGNORECASE
)

_ANON_SUGGESTIONS = [
    {"type": "真实姓名", "reason": "直接暴露他人真实姓名，违反匿名原则",
     "original_pattern": "XXX 叫 / 全名 / 姓名", "suggestion": "那个人 / TA / 我曾在乎的人"},
    {"type": "手机号码", "reason": "手机号可直接定位到具体个人",
     "original_pattern": "11位数字组合", "suggestion": "后来我们不再联系了"},
    {"type": "微信号", "reason": "微信号可加好友、获取朋友圈信息",
     "original_pattern": "微信号：xxx / 加我微信", "suggestion": "我们后来失去了联系"},
    {"type": "QQ号", "reason": "QQ号可查询个人信息和历史动态",
     "original_pattern": "QQ：123456789", "suggestion": "我们后来失去了联系"},
    {"type": "邮箱地址", "reason": "邮箱可作为登录凭证或联系方式",
     "original_pattern": "user@example.com", "suggestion": "我们后来失去了联系"},
    {"type": "报复性词汇", "reason": "这类词汇会引发对立情绪，与平台温和流转的定位冲突",
     "original_pattern": "渣男 / 渣女 / 骗子 / 毁掉", "suggestion": "这段关系让我失去了信任 / 让我感到受伤"},
    {"type": "诅咒表达", "reason": "诅咒类表达会升级冲突，不符合温和告别的价值观",
     "original_pattern": "去死 / 该死 / 恨死", "suggestion": "把感受写出来，但不要用伤害性的语言"},
    {"type": "可识别地点", "reason": "具体公司/学校+地点组合可推断出具体人物",
     "original_pattern": "XX公司 / XX学校 + 城市/地区", "suggestion": "那个人工作的地方 / 我们曾住在同一座城市"},
    {"type": "住址信息", "reason": "小区/楼栋/门牌号可精确定位居住地点",
     "original_pattern": "XX小区XX栋XX单元XXXX", "suggestion": "我们曾经住得很近 / 后来搬到了不同的地方"},
]


# ── Main Review Function ─────────────────────────────────────────────────────

def mock_review(short_story: str, full_story: str = "") -> Dict:
    """
    审核故事内容，返回风险等级、问题列表、建议和质量笔记。

    Phase 2B 策略（保守）：
    - safe → 直接 published（Phase 2D 接真实 AI 后改为 pending_review）
    - caution → needs_edit
    - high_risk → pending_review，等待人工复审

    Args:
        short_story: 一句话故事（必填）
        full_story: 完整故事（可选）

    Returns:
        dict with risk_level, issues, suggestions, quality_notes, overall_score,
        identity_risk, attack_risk, identifiable_person_risk
    """
    combined = f"{short_story}\n{full_story}"
    issues: List[Dict] = []
    risk_scores = {"identity": 0, "attack": 0, "identifiable": 0}

    # 1. Identity risk detection
    if _PHONE_RE.search(combined):
        issues.append({
            "type": "identity", "subtype": "phone",
            "original": "手机号码", "reason": "发现手机号，可能暴露具体个人"
        })
        risk_scores["identity"] = max(risk_scores["identity"], 3)

    if _WECHAT_RE.search(combined):
        issues.append({
            "type": "identity", "subtype": "wechat",
            "original": "微信号", "reason": "发现微信号，可加好友获取隐私信息"
        })
        risk_scores["identity"] = max(risk_scores["identity"], 3)

    if _QQ_RE.search(combined):
        issues.append({
            "type": "identity", "subtype": "qq",
            "original": "QQ号", "reason": "发现QQ号，可查询个人信息和历史动态"
        })
        risk_scores["identity"] = max(risk_scores["identity"], 3)

    if _EMAIL_RE.search(combined):
        issues.append({
            "type": "identity", "subtype": "email",
            "original": "邮箱地址", "reason": "发现邮箱地址，可作为登录凭证或联系方式"
        })
        risk_scores["identity"] = max(risk_scores["identity"], 3)

    if _ADDRESS_RE.search(combined):
        issues.append({
            "type": "identity", "subtype": "address",
            "original": "详细地址", "reason": "发现详细地址，可精确定位居住地点"
        })
        risk_scores["identity"] = max(risk_scores["identity"], 2)

    if _SOCIAL_RE.search(combined):
        issues.append({
            "type": "identity", "subtype": "social",
            "original": "社交平台账号", "reason": "发现社交平台账号，可获取更多个人信息"
        })
        risk_scores["identity"] = max(risk_scores["identity"], 3)

    # 2. Attack risk detection
    if _REVENGE_RE.search(combined):
        issues.append({
            "type": "attack", "subtype": "revenge_words",
            "original": "报复性词汇", "reason": "发现控诉或报复类词汇，与平台温和流转的定位冲突"
        })
        risk_scores["attack"] = max(risk_scores["attack"], 3)

    if _CURSE_RE.search(combined):
        issues.append({
            "type": "attack", "subtype": "curse",
            "original": "诅咒表达", "reason": "发现诅咒类表达，会升级冲突，不符合温和告别原则"
        })
        risk_scores["attack"] = max(risk_scores["attack"], 3)

    # 3. Identifiable person risk
    if _ID_RE.search(combined):
        name_pattern = re.compile(
            r'(?:TA?[叫管是]+|她?叫|他?叫)[^\s，。,\.]+',
            re.IGNORECASE
        )
        if name_pattern.search(combined):
            issues.append({
                "type": "identifiable", "subtype": "name_pattern",
                "original": "姓名暴露模式", "reason": "直接暴露他人姓名，违反匿名原则"
            })
            risk_scores["identifiable"] = max(risk_scores["identifiable"], 3)

    # 4. Build anonymization suggestions
    suggestions: List[Dict] = []
    for issue in issues:
        for anon in _ANON_SUGGESTIONS:
            if issue.get("subtype") in anon["type"].lower() or issue.get("type") in anon["type"].lower():
                suggestions.append({
                    "type": anon["type"],
                    "original": issue.get("original", ""),
                    "reason": anon["reason"],
                    "suggestion": anon["suggestion"]
                })
                break

    # 5. Story quality checks
    quality_notes: Dict = {}
    quality_score_sum = 0
    for qc in _QUALITY_CHECKS:
        check_result = qc["check"](combined)
        quality_notes[qc["id"]] = {
            "ok": bool(check_result),
            "message": qc["ok"] if check_result else qc["fail"]
        }
        if check_result:
            quality_score_sum += 1

    quality_score = quality_score_sum / len(_QUALITY_CHECKS) if _QUALITY_CHECKS else 0

    # 6. Determine risk level
    max_identity = risk_scores["identity"]
    max_attack = risk_scores["attack"]
    max_identifiable = risk_scores["identifiable"]

    if max_identity >= 3 or max_attack >= 3 or max_identifiable >= 3:
        risk_level = "high_risk"
    elif max_identity >= 2 or max_attack >= 2 or max_identifiable >= 2 or len(issues) >= 3:
        risk_level = "caution"
    else:
        risk_level = "safe"

    # 7. Overall score (inverse of risk)
    if risk_level == "high_risk":
        overall_score = 0.2 + (quality_score * 0.1)
    elif risk_level == "caution":
        overall_score = 0.5 + (quality_score * 0.2)
    else:
        overall_score = 0.7 + (quality_score * 0.3)

    overall_score = min(1.0, overall_score)

    return {
        "risk_level": risk_level,
        "issues": issues,
        "suggestions": suggestions,
        "quality_notes": quality_notes,
        "overall_score": round(overall_score, 2),
        "identity_risk": max_identity,
        "attack_risk": max_attack,
        "identifiable_person_risk": max_identifiable
    }


def get_publish_status(review_result: Dict) -> str:
    """
    根据审核结果决定礼物发布状态。

    Phase 2B 策略（保守）：
    - safe → published（立即公开）
    - caution → needs_edit（需用户修改）
    - high_risk → pending_review（进入人工审核队列）

    Phase 2D 真实 AI 上线后应改为：
    - safe → pending_review
    - caution → needs_edit
    - high_risk → pending_review
    """
    risk = review_result.get("risk_level", "safe")
    if risk == "safe":
        return "published"
    elif risk == "caution":
        return "needs_edit"
    else:  # high_risk
        return "pending_review"
