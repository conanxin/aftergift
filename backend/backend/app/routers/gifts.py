"""
Aftergift Backend - Gifts Router
Phase 2B | GET /api/gifts, GET /api/gifts/{id}, POST /api/gifts
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.database import get_connection, close_connection
from app.models import ACTION_LABELS, GiftStatus
from app.schemas import (
    GiftCreate, GiftListItem, GiftListResponse,
    GiftDetail, GiftCreateResponse, StoryDetail
)
from app.services import review_service
from app.auth import _require_auth

router = APIRouter(prefix="/gifts", tags=["gifts"])

# ── Response wrapper ─────────────────────────────────────────────────────────

def wrap(data, code=200, message="success"):
    """Wrap response in standard {code, message, data} format."""
    return JSONResponse(content={"code": code, "message": message, "data": data})


def _build_action_label(action_type: str) -> str:
    labels = {
        "sell": "出售", "exchange": "交换", "giveaway": "赠送",
        "donate": "捐出", "keep": "只讲故事"
    }
    return labels.get(action_type, action_type)


@router.get("")
def list_gifts(
    action_type: str | None = Query(None, description="筛选：sell/exchange/giveaway/donate/keep"),
    emotion: str | None = Query(None, description="筛选情绪标签"),
    page: int = Query(1, ge=1),
    limit: int = Query(8, ge=1, le=50),
):
    """获取公开礼物列表（仅 published 状态）"""
    conn = get_connection()
    offset = (page - 1) * limit

    # Build query
    sql = """
        SELECT g.id, g.title, g.category, g.relation_label, g.action_type,
               g.emotion, gs.short_story as excerpt, g.price_or_exchange,
               g.status, g.is_anonymous, u.anonymous_nickname, g.created_at
        FROM gifts g
        JOIN users u ON g.user_id = u.id
        LEFT JOIN gift_stories gs ON g.id = gs.gift_id
        WHERE g.status = 'published'
    """
    count_sql = """
        SELECT COUNT(*)
        FROM gifts g
        WHERE g.status = 'published'
    """
    params = []

    if action_type:
        sql += " AND g.action_type = ?"
        count_sql += " AND g.action_type = ?"
        params.append(action_type)

    if emotion:
        sql += " AND g.emotion = ?"
        count_sql += " AND g.emotion = ?"
        params.append(emotion)

    # Total count
    cur = conn.execute(count_sql, params)
    total = cur.fetchone()[0]

    # Page items
    sql += " ORDER BY g.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    close_connection(conn)

    items = []
    for row in rows:
        items.append({
            "id": row["id"],
            "title": row["title"],
            "category": row["category"],
            "relation_label": row["relation_label"],
            "action_type": row["action_type"],
            "action_label": _build_action_label(row["action_type"]),
            "emotion": row["emotion"],
            "excerpt": row["excerpt"],
            "price_or_exchange": row["price_or_exchange"],
            "status": row["status"],
            "is_anonymous": bool(row["is_anonymous"]),
            "anonymous_nickname": row["anonymous_nickname"],
            "created_at": row["created_at"]
        })

    has_more = offset + limit < total

    return wrap({
        "items": items,
        "pagination": {
            "page": page, "limit": limit, "total": total,
            "has_more": has_more
        }
    })


@router.get("/{gift_id}")
def get_gift(gift_id: str):
    """获取礼物详情（含完整故事）"""
    conn = get_connection()

    sql = """
        SELECT g.*, u.anonymous_nickname,
               gs.short_story, gs.full_story,
               gs.risk_level, gs.story_quality_score,
               gs.created_at as story_created_at
        FROM gifts g
        JOIN users u ON g.user_id = u.id
        LEFT JOIN gift_stories gs ON g.id = gs.gift_id
        WHERE g.id = ? AND g.status = 'published'
    """
    cur = conn.execute(sql, [gift_id])
    row = cur.fetchone()
    close_connection(conn)

    if not row:
        raise HTTPException(status_code=404, detail="礼物不存在或暂不可查看")

    story = None
    if row["short_story"]:
        story = {
            "short_story": row["short_story"],
            "full_story": row["full_story"],
            "risk_level": row["risk_level"],
            "quality_score": row["story_quality_score"],
            "created_at": row["story_created_at"]
        }

    return wrap({
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "relation_label": row["relation_label"],
        "action_type": row["action_type"],
        "action_label": _build_action_label(row["action_type"]),
        "emotion": row["emotion"],
        "price_or_exchange": row["price_or_exchange"],
        "condition_note": row["condition_note"],
        "city_blur": row["city_blur"],
        "is_anonymous": bool(row["is_anonymous"]),
        "anonymous_nickname": row["anonymous_nickname"],
        "status": row["status"],
        "story": story,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    })


@router.post("")
def create_gift(
    gift: GiftCreate,
    request: Request,
):
    """
    发布新礼物。

    Phase 2D 策略：
    - 需要 Bearer token（通过 POST /api/auth/anonymous 获取）
    - 无 token → 401
    - token 有效 → 使用该 user_id 发布
    - Phase 2E 接入真实 JWT + 手机号认证
    """
    user_id = _require_auth(request)
    review_result = review_service.mock_review(gift.short_story, gift.full_story)
    risk_level = review_result["risk_level"]
    publish_status = review_service.get_publish_status(review_result)

    # 2. Generate IDs
    gift_id = f"gift-{uuid.uuid4().hex[:8]}"
    story_id = f"story-{uuid.uuid4().hex[:8]}"
    review_log_id = f"review-{uuid.uuid4().hex[:8]}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 3. Extract flat risk flags for review_logs (backward compat with old schema)
    def _issue_flag(issues, category, subtype=None):
        for i in issues:
            if subtype:
                if i.get("category") == category and i.get("subtype") == subtype:
                    return i.get("severity", "medium")
            else:
                if i.get("category") == category:
                    return i.get("severity", "medium")
        return "none"

    issues = review_result.get("issues", [])
    identity_risk = _issue_flag(issues, "identity")
    attack_risk = _issue_flag(issues, "attack")
    identifiable_person_risk = _issue_flag(issues, "identifiable_person")

    conn = get_connection()

    # 4. Insert gift
    conn.execute("""
        INSERT INTO gifts (id, user_id, title, category, relation_type, relation_label,
                          action_type, emotion, price_or_exchange, condition_note,
                          city_blur, is_anonymous, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        gift_id, user_id, gift.title, gift.category,
        gift.relation_type, gift.relation_type,
        gift.action_type.value, gift.emotion,
        gift.price_or_exchange, gift.condition_note,
        gift.city_blur, int(gift.is_anonymous),
        publish_status, now, now
    ))

    # 5. Insert story
    conn.execute("""
        INSERT INTO gift_stories (id, gift_id, short_story, full_story,
                                  story_quality_score, risk_level, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        story_id, gift_id, gift.short_story, gift.full_story,
        review_result.get("overall_score", 80), risk_level, now
    ))

    # Map provider name to reviewer_type enum value
    PROVIDER_TO_REVIEWER_TYPE = {
        "mock": "ai_rule_engine",
        "openai": "ai_moderation_api",
        "baidu": "ai_moderation_api",
    }
    reviewer_type = PROVIDER_TO_REVIEWER_TYPE.get(
        review_result.get("provider", "mock"), "ai_rule_engine"
    )

    # 6. Insert review log
    conn.execute("""
        INSERT INTO review_logs (id, gift_id, risk_level, identity_risk,
                                 attack_risk, identifiable_person_risk,
                                 quality_notes, suggestions_json,
                                 reviewer_type, decision, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        review_log_id, gift_id, risk_level,
        identity_risk, attack_risk, identifiable_person_risk,
        str(review_result.get("quality_notes", {})),
        str(review_result.get("suggestions", [])),
        reviewer_type,
        "approve" if risk_level == "safe" else None,
        now
    ))

    conn.commit()
    close_connection(conn)

    msg = "礼物已发布" if risk_level == "safe" else "需要修改后重新提交" if risk_level == "caution" else "已提交审核"
    return wrap(
        {
            "gift_id": gift_id,
            "status": publish_status,
            "estimated_review_time": "即时发布" if risk_level == "safe" else "需修改后重新提交" if risk_level == "caution" else "24小时内",
            "review": {
                "risk_level": risk_level,
                "issues_count": len(review_result.get("issues", [])),
            }
        },
        code=201,
        message=msg
    )
