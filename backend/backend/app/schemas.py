"""
Aftergift Backend - Pydantic Schemas
Phase 2B | 定义所有 API 请求/响应模型
参考 docs/API_DESIGN.md 和 docs/DATA_MODEL.md
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── Enums (imported from models) ───────────────────────────────────────────

from app.models import (
    ActionType, EmotionTag, RiskLevel,
    ReportReason, ReportStatus, AdminDecision,
    ACTION_LABELS,
)


# ── Common ───────────────────────────────────────────────────────────────────

class ApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[dict | list] = None


# ── Quality Notes ────────────────────────────────────────────────────────────

class QualityNoteItem(BaseModel):
    ok: bool
    message: str


class QualityNotes(BaseModel):
    word_count: QualityNoteItem
    has_origin: QualityNoteItem
    has_meaning: QualityNoteItem
    has_farewell_reason: QualityNoteItem
    has_next_hope: QualityNoteItem


# ── Gift Schemas ────────────────────────────────────────────────────────────

class GiftCreate(BaseModel):
    """POST /api/gifts 请求体"""
    title: str = Field(..., min_length=1, max_length=50, description="礼物名称")
    category: str = Field(..., description="礼物类型")
    relation_type: Optional[str] = Field(None, description="关系类型")
    action_type: ActionType = Field(..., description="处理方式")
    emotion: str = Field(..., description="情绪标签")
    price_or_exchange: Optional[str] = Field(None, description="价格或交换意向")
    condition_note: Optional[str] = Field(None, description="物品状态备注")
    city_blur: Optional[str] = Field(None, description="城市（仅城市名）")
    is_anonymous: bool = Field(True, description="是否匿名发布")
    short_story: str = Field(..., min_length=1, max_length=100, description="一句话故事")
    full_story: str = Field(..., min_length=10, max_length=2000, description="完整故事")


class GiftListItem(BaseModel):
    """GET /api/gifts 列表项"""
    id: str
    title: str
    category: str
    relation_label: Optional[str]
    action_type: str
    action_label: str
    emotion: str
    excerpt: Optional[str]
    price_or_exchange: Optional[str]
    status: str
    is_anonymous: bool
    anonymous_nickname: Optional[str]
    created_at: str


class GiftListResponse(BaseModel):
    """GET /api/gifts 响应"""
    items: List[GiftListItem]
    pagination: dict


class StoryDetail(BaseModel):
    """故事详情（嵌套在 GiftDetail 里）"""
    short_story: str
    full_story: str
    risk_level: str
    quality_score: Optional[float]
    created_at: str


class GiftDetail(BaseModel):
    """GET /api/gifts/{id} 响应"""
    id: str
    title: str
    category: str
    relation_label: Optional[str]
    action_type: str
    action_label: str
    emotion: str
    price_or_exchange: Optional[str]
    condition_note: Optional[str]
    city_blur: Optional[str]
    is_anonymous: bool
    anonymous_nickname: Optional[str]
    status: str
    story: Optional[StoryDetail]
    created_at: str
    updated_at: str


class GiftCreateResponse(BaseModel):
    """POST /api/gifts 响应"""
    gift_id: str
    status: str
    estimated_review_time: str = "24小时内"


# ── Review Schemas ─────────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    """POST /api/review/mock 请求体"""
    short_story: str
    full_story: str = ""


class IssueItem(BaseModel):
    type: str
    subtype: Optional[str] = None
    original: str
    reason: str


class SuggestionItem(BaseModel):
    type: str
    original: str
    reason: str
    suggestion: str


class ReviewResult(BaseModel):
    """POST /api/review/mock 响应"""
    risk_level: str
    issues: List[IssueItem]
    suggestions: List[SuggestionItem]
    quality_notes: dict
    overall_score: float
    identity_risk: int
    attack_risk: int
    identifiable_person_risk: int


# ── Favorite Schemas ────────────────────────────────────────────────────────

class FavoriteResponse(BaseModel):
    """POST /api/gifts/{id}/favorite 响应"""
    favorite_id: str
    gift_id: str


# ── Report Schemas ───────────────────────────────────────────────────────────

class ReportCreate(BaseModel):
    """POST /api/gifts/{id}/report 请求体"""
    reason: ReportReason
    detail: Optional[str] = None


class ReportResponse(BaseModel):
    """POST /api/gifts/{id}/report 响应"""
    report_id: str
    status: str


# ── Admin Schemas ───────────────────────────────────────────────────────────

class AdminReviewItem(BaseModel):
    """GET /api/admin/reviews 列表项"""
    gift_id: str
    title: str
    short_story: str
    risk_level: str
    identity_risk: int
    attack_risk: int
    identifiable_person_risk: int
    suggestions: List[dict]
    submitted_at: str
    ai_review_notes: Optional[str] = None


class AdminReviewListResponse(BaseModel):
    """GET /api/admin/reviews 响应"""
    items: List[AdminReviewItem]
    total: int
    page: int


class AdminDecisionRequest(BaseModel):
    """POST /api/admin/reviews/{gift_id}/decision 请求体"""
    decision: AdminDecision
    note: Optional[str] = None


class AdminDecisionResponse(BaseModel):
    """POST /api/admin/reviews/{gift_id}/decision 响应"""
    gift_id: str
    new_status: str
    decided_at: str


# ── Health ─────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    version: str
    status: str
