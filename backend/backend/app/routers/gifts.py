"""
Aftergift Backend - Gifts Router
Phase 2B  | GET /api/gifts, GET /api/gifts/{id}, POST /api/gifts
Phase 2E-3 | Review log redaction applied before persistence
Phase 2G-1 | Search, filter, pagination, sort with SQL injection defense
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
from app.services.anonymize_service import redact_sensitive_text, summarize_redactions
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


# ── Search helpers ───────────────────────────────────────────────────────────

# Whitelist for sort / order to prevent SQL injection
_SORT_WHITELIST = {"created_at", "title", "emotion", "action_type"}
_ORDER_WHITELIST = {"asc", "desc"}


def _build_search_clause(q: str | None) -> tuple[str, list]:
    """
    Build parameterized search clause for gifts + gift_stories.
    Returns (sql_fragment, params).
    """
    if not q or not q.strip():
        return "", []
    term = q.strip()
    # Search across: title, category, relation_type, relation_label,
    # action_type, emotion, city_blur, short_story, full_story
    clause = """ AND (
        g.title LIKE ? OR g.category LIKE ? OR g.relation_type LIKE ?
        OR g.relation_label LIKE ? OR g.action_type LIKE ?
        OR g.emotion LIKE ? OR g.city_blur LIKE ?
        OR gs.short_story LIKE ? OR gs.full_story LIKE ?
    )"""
    pattern = f"%{term}%"
    params = [pattern] * 9
    return clause, params


def _build_matched_fields(row, q: str | None) -> list[str]:
    """Determine which fields matched the search term (lightweight)."""
    if not q or not q.strip():
        return []
    term = q.strip().lower()
    matched = []
    checks = [
        ("title", row["title"] or ""),
        ("category", row["category"] or ""),
        ("relation_type", row["relation_type"] or ""),
        ("relation_label", row["relation_label"] or ""),
        ("action_type", row["action_type"] or ""),
        ("emotion", row["emotion"] or ""),
        ("city_blur", row["city_blur"] or ""),
        ("short_story", row["short_story"] or ""),
        ("full_story", row["full_story"] or ""),
    ]
    for field, value in checks:
        if term in value.lower():
            matched.append(field)
    return matched


def _excerpt(text: str | None, max_len: int = 120) -> str:
    """Return plain-text excerpt, no HTML."""
    if not text:
        return ""
    t = text.strip()
    if len(t) <= max_len:
        return t
    return t[:max_len] + "……"


# ── List gifts (Phase 2G-1 enhanced) ─────────────────────────────────────────

@router.get("")
def list_gifts(
    q: str | None = Query(None, description="关键词搜索"),
    emotion: str | None = Query(None, description="筛选情绪标签"),
    action_type: str | None = Query(None, description="筛选：sell/exchange/giveaway/donate/keep"),
    relation_type: str | None = Query(None, description="筛选关系类型"),
    city_blur: str | None = Query(None, description="模糊城市"),
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    sort: str = Query("created_at", description="排序字段"),
    order: str = Query("desc", description="asc / desc"),
):
    """
    获取公开礼物列表（仅 published 状态）。
    Phase 2G-1 增强：支持关键词搜索、多维度筛选、分页、排序。
    """
    # Validate sort/order against whitelist
    if sort not in _SORT_WHITELIST:
        sort = "created_at"
    if order not in _ORDER_WHITELIST:
        order = "desc"

    conn = get_connection()
    offset = (page - 1) * limit

    # Build base SQL
    sql = """
        SELECT g.id, g.title, g.category, g.relation_type, g.relation_label,
               g.action_type, g.emotion, gs.short_story, gs.full_story,
               g.price_or_exchange, g.status, g.is_anonymous,
               u.anonymous_nickname, g.created_at, g.city_blur
        FROM gifts g
        JOIN users u ON g.user_id = u.id
        LEFT JOIN gift_stories gs ON g.id = gs.gift_id
        WHERE g.status = 'published'
    """
    count_sql = """
        SELECT COUNT(*)
        FROM gifts g
        LEFT JOIN gift_stories gs ON g.id = gs.gift_id
        WHERE g.status = 'published'
    """
    params = []
    count_params = []

    # Search clause
    search_clause, search_params = _build_search_clause(q)
    if search_clause:
        sql += search_clause
        count_sql += search_clause
        params.extend(search_params)
        count_params.extend(search_params)

    # Filters
    if action_type:
        sql += " AND g.action_type = ?"
        count_sql += " AND g.action_type = ?"
        params.append(action_type)
        count_params.append(action_type)

    if emotion:
        sql += " AND g.emotion = ?"
        count_sql += " AND g.emotion = ?"
        params.append(emotion)
        count_params.append(emotion)

    if relation_type:
        sql += " AND g.relation_type = ?"
        count_sql += " AND g.relation_type = ?"
        params.append(relation_type)
        count_params.append(relation_type)

    if city_blur:
        sql += " AND g.city_blur LIKE ?"
        count_sql += " AND g.city_blur LIKE ?"
        params.append(f"%{city_blur}%")
        count_params.append(f"%{city_blur}%")

    # Total count
    cur = conn.execute(count_sql, count_params)
    total = cur.fetchone()[0]

    # Page items
    sql += f" ORDER BY g.{sort} {order.upper()} LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    close_connection(conn)

    items = []
    for row in rows:
        matched = _build_matched_fields(row, q)
        story_text = row["short_story"] or row["full_story"] or ""
        items.append({
            "id": row["id"],
            "title": row["title"],
            "category": row["category"],
            "relation_type": row["relation_type"],
            "relation_label": row["relation_label"],
            "action_type": row["action_type"],
            "action_label": _build_action_label(row["action_type"]),
            "emotion": row["emotion"],
            "excerpt": row["short_story"],
            "story_excerpt": _excerpt(story_text),
            "price_or_exchange": row["price_or_exchange"],
            "status": row["status"],
            "is_anonymous": bool(row["is_anonymous"]),
            "anonymous_nickname": row["anonymous_nickname"],
            "created_at": row["created_at"],
            "city_blur": row["city_blur"],
            "matched_fields": matched if q else None,
            "search_highlight": None,  # No HTML highlight to avoid XSS
        })

    total_pages = (total + limit - 1) // limit if limit > 0 else 0
    has_more = page < total_pages

    return wrap({
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "has_more": has_more,
        "filters": {
            "q": q,
            "emotion": emotion,
            "action_type": action_type,
            "relation_type": relation_type,
            "city_blur": city_blur,
            "sort": sort,
            "order": order,
        }
    })


# ── Get gift detail ──────────────────────────────────────────────────────────

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


# ── Create gift ──────────────────────────────────────────────────────────────

@router.post("")
def create_gift(
    gift: GiftCreate,
    request: Request,
):
    """
    发布新礼物。

    Phase 2E-3 增强：
    - review_result 中的 issues / suggestions 在写入 review_logs 前自动脱敏
    - review_logs 不保存原始敏感值
    - 新增 redaction_summary 记录脱敏操作
    """
    user_id = _require_auth(request)
    review_result = review_service.mock_review(gift.short_story, gift.full_story)
    risk_level = review_result["risk_level"]
    publish_status = review_service.get_publish_status(review_result)

    # Phase 2E-3: Redact review_result before persistence
    # Redact issues evidence and suggestions
    redacted_issues = []
    for issue in review_result.get("issues", []):
        redacted_issue = dict(issue)
        if "original" in redacted_issue:
            redacted_issue["original"] = redact_sensitive_text(str(redacted_issue["original"]))
        redacted_issues.append(redacted_issue)

    redacted_suggestions = []
    for suggestion in review_result.get("suggestions", []):
        redacted_sug = dict(suggestion)
        for key in ("original", "message", "replacement"):
            if key in redacted_sug and redacted_sug[key]:
                redacted_sug[key] = redact_sensitive_text(str(redacted_sug[key]))
        redacted_suggestions.append(redacted_sug)

    # Build redaction summary
    combined_evidence = ""
    for issue in review_result.get("issues", []):
        combined_evidence += str(issue.get("original", "")) + " "
    for suggestion in review_result.get("suggestions", []):
        combined_evidence += str(suggestion.get("original", "")) + " "
        combined_evidence += str(suggestion.get("message", "")) + " "

    redaction_summary = summarize_redactions(
        combined_evidence,
        redact_sensitive_text(combined_evidence)
    )

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

    # Build suggestions_json with redaction summary embedded
    suggestions_payload = {
        "suggestions": redacted_suggestions,
        "redaction_summary": redaction_summary,
    }

    # 6. Insert review log (with redacted data)
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
        str(suggestions_payload),
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
                "redaction_summary": redaction_summary,
            }
        },
        code=201,
        message=msg
    )
