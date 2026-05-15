"""
Aftergift Backend - Domain Models & Enums
Phase 2B | 无 ORM，纯 Python 枚举和常量定义
"""

from enum import Enum

# ── Gift Status ─────────────────────────────────────────────────────────────

class GiftStatus(str, Enum):
    DRAFT = "draft"                  # 用户草稿，未提交
    PENDING_REVIEW = "pending_review" # 审核中
    PUBLISHED = "published"           # 已发布，公开
    NEEDS_EDIT = "needs_edit"        # 需要用户修改
    REJECTED = "rejected"            # 被拒绝
    ARCHIVED = "archived"             # 已归档（下架或用户删除）


# ── Risk Level ──────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    SAFE = "safe"
    CAUTION = "caution"
    HIGH_RISK = "high_risk"


# ── Action Type ─────────────────────────────────────────────────────────────

class ActionType(str, Enum):
    SELL = "sell"             # 出售
    EXCHANGE = "exchange"      # 交换
    GIVEAWAY = "giveaway"     # 赠送
    DONATE = "donate"         # 捐出
    KEEP = "keep"             # 只讲故事


# ── Emotion Tag ─────────────────────────────────────────────────────────────

class EmotionTag(str, Enum):
    PUT_DOWN = "放下"
    REGRET = "遗憾"
    GRATEFUL = "感谢"
    RELEASE = "释怀"
    RESTART = "重启"
    MEMORIAL = "纪念"
    HEAL = "治愈"
    CALM = "平静"


# ── Category ─────────────────────────────────────────────────────────────────

CATEGORIES = [
    "家居装饰",
    "文具",
    "数码",
    "配饰",
    "书籍",
    "玩具摆件",
    "健康",
    "其他",
]


# ── Relation Type ───────────────────────────────────────────────────────────

RELATION_TYPES = [
    "前任",
    "挚友",
    "夫妻",
    "家人",
    "同事",
    "恩师",
    "其他",
]


# ── Report Reason ───────────────────────────────────────────────────────────

class ReportReason(str, Enum):
    PRIVACY = "privacy"     # 曝光隐私
    ATTACK = "attack"       # 攻击性内容
    FAKE = "fake"           # 虚假信息
    OTHER = "other"         # 其他


# ── Report Status ───────────────────────────────────────────────────────────

class ReportStatus(str, Enum):
    PENDING = "pending"
    REVIEWING = "reviewing"
    RESOLVED_DISMISSED = "resolved_dismissed"
    RESOLVED_ACTION_TAKEN = "resolved_action_taken"


# ── Reviewer Type ───────────────────────────────────────────────────────────

class ReviewerType(str, Enum):
    AI_RULE_ENGINE = "ai_rule_engine"
    AI_MODERATION_API = "ai_moderation_api"
    HUMAN_ADMIN = "human_admin"


# ── Admin Decision ──────────────────────────────────────────────────────────

class AdminDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    NEEDS_EDIT = "needs_edit"


# ── Action Labels (display helpers) ─────────────────────────────────────────

ACTION_LABELS = {
    ActionType.SELL: "出售",
    ActionType.EXCHANGE: "交换",
    ActionType.GIVEAWAY: "赠送",
    ActionType.DONATE: "捐出",
    ActionType.KEEP: "只讲故事",
}
