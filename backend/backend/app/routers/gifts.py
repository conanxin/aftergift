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
from app.auth import _require_auth, get_bearer_token, decode_access_token

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


# ── Row → item helper (shared) ───────────────────────────────────────────────

def _row_to_list_item(row, *, current_user_id: str | None = None,
                      favorited_ids: set | None = None,
                      q: str | None = None,
                      favorites_of: str | None = None) -> dict:
    """Convert a SQLite row to a GiftListItem dict."""
    matched = _build_matched_fields(row, q)
    story_text = row["short_story"] or row["full_story"] or ""
    gift_id = row["id"]
    is_mine = current_user_id is not None and row["user_id"] == current_user_id
    is_favorited = (favorited_ids is not None) and (gift_id in favorited_ids)
    favorite_created_at = row["favorite_created_at"] if favorites_of == "me" else None
    favorite_count = row["favorite_count"] if "favorite_count" in row.keys() else 0

    item = {
        "id": gift_id,
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
        "search_highlight": None,
        # Phase 2G-2 extras
        "is_mine": is_mine,
        "is_favorited": is_favorited,
        # Phase 2I-1
        "favorite_count": favorite_count,
    }
    if favorite_created_at:
        item["favorite_created_at"] = favorite_created_at
    return item


# ── List gifts (Phase 2G-1 enhanced, Phase 2G-2 mine/favorites) ──────────────

@router.get("")
def list_gifts(
    request: Request,
    q: str | None = Query(None, description="关键词搜索"),
    emotion: str | None = Query(None, description="筛选情绪标签"),
    action_type: str | None = Query(None, description="筛选：sell/exchange/giveaway/donate/keep"),
    relation_type: str | None = Query(None, description="筛选关系类型"),
    city_blur: str | None = Query(None, description="模糊城市"),
    mine: bool = Query(False, description="仅返回当前用户发布的礼物（需登录）"),
    favorites_of: str | None = Query(None, description="筛选收藏：me=当前用户（需登录）"),
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    sort: str = Query("created_at", description="排序字段"),
    order: str = Query("desc", description="asc / desc"),
):
    """
    获取礼物列表。
    Phase 2G-1: 支持关键词搜索、多维度筛选、分页、排序。
    Phase 2G-2: 支持 mine=true（我的发布）和 favorites_of=me（我的收藏）。
    """
    # Validate sort/order against whitelist
    if sort not in _SORT_WHITELIST:
        sort = "created_at"
    if order not in _ORDER_WHITELIST:
        order = "desc"

    # Resolve current user (optional — only needed for mine / favorites / is_mine / is_favorited)
    current_user_id = None
    token = get_bearer_token(request)
    if token:
        payload = decode_access_token(token)
        if payload:
            current_user_id = payload.get("sub")

    # Auth gate for mine / favorites_of
    if mine and not current_user_id:
        raise HTTPException(
            status_code=401,
            detail={"code": 401, "message": "请先创建匿名身份，再查看你的礼物", "data": None}
        )
    if favorites_of == "me" and not current_user_id:
        raise HTTPException(
            status_code=401,
            detail={"code": 401, "message": "请先创建匿名身份，再查看你的收藏", "data": None}
        )

    conn = get_connection()
    offset = (page - 1) * limit

    # Build base SQL
    if favorites_of == "me":
        # Join favorites table
        sql = """
            SELECT g.id, g.user_id, g.title, g.category, g.relation_type, g.relation_label,
                   g.action_type, g.emotion, gs.short_story, gs.full_story,
                   g.price_or_exchange, g.status, g.is_anonymous,
                   u.anonymous_nickname, g.created_at, g.city_blur,
                   f.created_at as favorite_created_at,
                   COALESCE(fc.count, 0) as favorite_count
            FROM favorites f
            JOIN gifts g ON f.gift_id = g.id
            JOIN users u ON g.user_id = u.id
            LEFT JOIN gift_stories gs ON g.id = gs.gift_id
            LEFT JOIN (
                SELECT gift_id, COUNT(*) as count FROM favorites GROUP BY gift_id
            ) fc ON g.id = fc.gift_id
            WHERE f.user_id = ? AND g.status = 'published'
        """
        count_sql = """
            SELECT COUNT(*)
            FROM favorites f
            JOIN gifts g ON f.gift_id = g.id
            WHERE f.user_id = ? AND g.status = 'published'
        """
        params = [current_user_id]
        count_params = [current_user_id]
    else:
        sql = """
            SELECT g.id, g.user_id, g.title, g.category, g.relation_type, g.relation_label,
                   g.action_type, g.emotion, gs.short_story, gs.full_story,
                   g.price_or_exchange, g.status, g.is_anonymous,
                   u.anonymous_nickname, g.created_at, g.city_blur,
                   COALESCE(fc.count, 0) as favorite_count
            FROM gifts g
            JOIN users u ON g.user_id = u.id
            LEFT JOIN gift_stories gs ON g.id = gs.gift_id
            LEFT JOIN (
                SELECT gift_id, COUNT(*) as count FROM favorites GROUP BY gift_id
            ) fc ON g.id = fc.gift_id
            WHERE 1=1
        """
        count_sql = """
            SELECT COUNT(*)
            FROM gifts g
            LEFT JOIN gift_stories gs ON g.id = gs.gift_id
            WHERE 1=1
        """
        params = []
        count_params = []

        # Status filter: mine=true shows all statuses; public only shows published
        if mine:
            sql += " AND g.user_id = ?"
            count_sql += " AND g.user_id = ?"
            params.append(current_user_id)
            count_params.append(current_user_id)
        else:
            sql += " AND g.status = 'published'"
            count_sql += " AND g.status = 'published'"

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

    # Check favorites for current user (for is_favorited field)
    favorited_ids = set()
    if current_user_id and not favorites_of:
        gift_ids = [row["id"] for row in rows]
        if gift_ids:
            placeholders = ",".join(["?"] * len(gift_ids))
            fav_cur = conn.execute(
                f"SELECT gift_id FROM favorites WHERE user_id = ? AND gift_id IN ({placeholders})",
                [current_user_id] + gift_ids
            )
            favorited_ids = {r[0] for r in fav_cur.fetchall()}

    close_connection(conn)

    items = []
    for row in rows:
        items.append(_row_to_list_item(
            row,
            current_user_id=current_user_id,
            favorited_ids=favorited_ids,
            q=q,
            favorites_of=favorites_of
        ))

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
            "mine": mine,
            "favorites_of": favorites_of,
            "sort": sort,
            "order": order,
        }
    })



_RAIL_WHITELIST = {"latest", "popular", "gentle", "all"}


def _discovery_query(rail: str, limit: int) -> tuple[str, list]:
    """Return (sql, params) for a given discovery rail."""
    base_select = """
        SELECT g.id, g.user_id, g.title, g.category, g.relation_type, g.relation_label,
               g.action_type, g.emotion, gs.short_story, gs.full_story,
               g.price_or_exchange, g.status, g.is_anonymous,
               u.anonymous_nickname, g.created_at, g.city_blur,
               COALESCE(fc.count, 0) as favorite_count
        FROM gifts g
        JOIN users u ON g.user_id = u.id
        LEFT JOIN gift_stories gs ON g.id = gs.gift_id
        LEFT JOIN (
            SELECT gift_id, COUNT(*) as count FROM favorites GROUP BY gift_id
        ) fc ON g.id = fc.gift_id
        WHERE g.status = 'published'
    """
    if rail == "latest":
        sql = base_select + " ORDER BY g.created_at DESC LIMIT ?"
        return sql, [limit]
    if rail == "popular":
        sql = base_select + " ORDER BY favorite_count DESC, g.created_at DESC LIMIT ?"
        return sql, [limit]
    if rail == "gentle":
        # Phase 2I-2: Prefer safe/caution stories; fallback to latest if empty
        sql = base_select + """ AND gs.risk_level IN ('safe', 'caution')
            ORDER BY g.created_at DESC LIMIT ?"""
        return sql, [limit]
    raise ValueError(f"Unknown rail: {rail}")


@router.get("/discovery")
def discovery(
    rail: str = Query("all", description="latest | popular | gentle | all"),
    limit: int = Query(6, ge=1, le=20),
):
    """
    Discovery rails — non-personalized, explainable recommendations.
    Phase 2I-2: gentle rail has fallback to latest when no safe/caution gifts.
    """
    if rail not in _RAIL_WHITELIST:
        raise HTTPException(status_code=400, detail={
            "code": 400,
            "message": f"非法 rail: {rail}",
            "data": {"allowed": list(_RAIL_WHITELIST)}
        })

    conn = get_connection()
    try:
        if rail == "all":
            result = {}
            for r in ("latest", "popular", "gentle"):
                sql, params = _discovery_query(r, limit)
                cur = conn.execute(sql, params)
                rows = cur.fetchall()
                items = [_row_to_list_item(row) for row in rows]
                # Phase 2I-2: gentle fallback
                if r == "gentle" and not items:
                    sql2, params2 = _discovery_query("latest", limit)
                    cur2 = conn.execute(sql2, params2)
                    rows2 = cur2.fetchall()
                    items = [_row_to_list_item(row2) for row2 in rows2]
                    result[r] = {"items": items, "fallback_used": True}
                else:
                    result[r] = {"items": items, "fallback_used": False} if r == "gentle" else items
            return wrap({
                "rail": "all",
                "rails": result,
                "meta": {
                    "strategy": "non_personalized",
                    "tracking": False,
                    "description": "无个性化追踪，基于公开礼物数据排序"
                }
            })
        else:
            sql, params = _discovery_query(rail, limit)
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
            items = [_row_to_list_item(row) for row in rows]
            fallback_used = False
            # Phase 2I-2: gentle fallback
            if rail == "gentle" and not items:
                sql2, params2 = _discovery_query("latest", limit)
                cur2 = conn.execute(sql2, params2)
                rows2 = cur2.fetchall()
                items = [_row_to_list_item(row2) for row2 in rows2]
                fallback_used = True
            return wrap({
                "rail": rail,
                "items": items,
                "fallback_used": fallback_used,
                "meta": {
                    "strategy": "non_personalized",
                    "tracking": False,
                }
            })
    finally:
        close_connection(conn)


# ── Similar Gifts (Phase 2I-1) ───────────────────────────────────────────────

@router.get("/{gift_id}/similar")
def similar_gifts(
    gift_id: str,
    limit: int = Query(4, ge=1, le=12),
):
    """
    返回与指定礼物相似的故事。
    相似度基于：emotion + relation_type + action_type + category。
    无个性化追踪。
    Phase 2I-1
    """
    conn = get_connection()
    try:
        # Verify base gift exists and is published
        cur = conn.execute(
            """SELECT g.*, gs.risk_level FROM gifts g
               LEFT JOIN gift_stories gs ON g.id = gs.gift_id
               WHERE g.id = ? AND g.status = 'published'""",
            [gift_id]
        )
        base = cur.fetchone()
        if not base:
            raise HTTPException(status_code=404, detail="礼物不存在或暂不可查看")

        # Fetch candidates
        cur = conn.execute("""
            SELECT g.id, g.user_id, g.title, g.category, g.relation_type, g.relation_label,
                   g.action_type, g.emotion, gs.short_story, gs.full_story,
                   g.price_or_exchange, g.status, g.is_anonymous,
                   u.anonymous_nickname, g.created_at, g.city_blur,
                   COALESCE(fc.count, 0) as favorite_count
            FROM gifts g
            JOIN users u ON g.user_id = u.id
            LEFT JOIN gift_stories gs ON g.id = gs.gift_id
            LEFT JOIN (
                SELECT gift_id, COUNT(*) as count FROM favorites GROUP BY gift_id
            ) fc ON g.id = fc.gift_id
            WHERE g.status = 'published' AND g.id != ?
        """, [gift_id])
        rows = cur.fetchall()

        # Score
        scored = []
        for row in rows:
            score = 0
            reasons = []
            if row["emotion"] == base["emotion"]:
                score += 3
                reasons.append("相同情绪")
            if row["relation_type"] == base["relation_type"]:
                score += 2
                reasons.append("相同关系类型")
            if row["action_type"] == base["action_type"]:
                score += 1
                reasons.append("相同处理方式")
            if row["category"] == base["category"]:
                score += 1
                reasons.append("相同礼物类型")
            if score > 0:
                scored.append((score, row, reasons))

        scored.sort(key=lambda x: (-x[0], x[1]["created_at"] or "", x[1]["id"]))
        top = scored[:limit]

        items = []
        for score, row, reasons in top:
            item = _row_to_list_item(row)
            item["similarity_score"] = score
            item["matched_reasons"] = reasons
            item["matched_reason"]  = "、".join(reasons) if reasons else ""
            items.append(item)

        return wrap({
            "base_gift_id": gift_id,
            "strategy": "emotion_relation_action_similarity",
            "items": items,
        })
    finally:
        close_connection(conn)

# ── Get gift detail ──────────────────────────────────────────────────────────

@router.get("/{gift_id}")
def get_gift(gift_id: str):
    """获取礼物详情（含完整故事）"""
    conn = get_connection()

    sql = """
        SELECT g.*, u.anonymous_nickname,
               gs.short_story, gs.full_story,
               gs.risk_level, gs.story_quality_score,
               gs.created_at as story_created_at,
               COALESCE(fc.count, 0) as favorite_count
        FROM gifts g
        JOIN users u ON g.user_id = u.id
        LEFT JOIN gift_stories gs ON g.id = gs.gift_id
        LEFT JOIN (
            SELECT gift_id, COUNT(*) as count FROM favorites GROUP BY gift_id
        ) fc ON g.id = fc.gift_id
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
        "updated_at": row["updated_at"],
        # Phase 2I-2: real favorite_count from JOIN
        "favorite_count": row["favorite_count"] if "favorite_count" in row.keys() else 0,
    })


# ── Discovery Rails (Phase 2I-1) ─────────────────────────────────────────────

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


# ── Phase 2H-1: My Gift Management ──────────────────────────────────────────

# Editable statuses (user can edit their own gift)
_EDITABLE_STATUSES = {"draft", "pending_review", "needs_edit"}
# Resubmittable statuses
_RESUBMITTABLE_STATUSES = {"draft", "needs_edit"}
# Archivable statuses
_ARCHIVABLE_STATUSES = {"published", "pending_review", "needs_edit"}


def _get_gift_owner(gift_id: str, conn) -> str | None:
    """Return user_id of gift owner, or None if gift doesn't exist."""
    cur = conn.execute("SELECT user_id FROM gifts WHERE id = ?", [gift_id])
    row = cur.fetchone()
    return row["user_id"] if row else None


def _get_last_review_note(gift_id: str, conn) -> str | None:
    """Return the most recent admin decision note for a gift, if any."""
    cur = conn.execute("""
        SELECT note FROM admin_actions
        WHERE target_type = 'gift' AND target_id = ? AND action = 'needs_edit'
        ORDER BY created_at DESC LIMIT 1
    """, [gift_id])
    row = cur.fetchone()
    return row["note"] if row else None


def _review_and_log(gift_id: str, short_story: str, full_story: str, conn) -> dict:
    """Run moderation review and write review_logs. Returns review_result dict."""
    review_result = review_service.mock_review(short_story, full_story)
    risk_level = review_result["risk_level"]

    # Redact before persistence
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

    review_log_id = f"review-{uuid.uuid4().hex[:8]}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

    PROVIDER_TO_REVIEWER_TYPE = {
        "mock": "ai_rule_engine",
        "openai": "ai_moderation_api",
        "baidu": "ai_moderation_api",
    }
    reviewer_type = PROVIDER_TO_REVIEWER_TYPE.get(
        review_result.get("provider", "mock"), "ai_rule_engine"
    )

    suggestions_payload = {
        "suggestions": redacted_suggestions,
        "redaction_summary": redaction_summary,
    }

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

    return {
        "review_result": review_result,
        "redaction_summary": redaction_summary,
        "risk_level": risk_level,
    }


@router.get("/me/gifts/{gift_id}")
def get_my_gift_detail(gift_id: str, request: Request):
    """
    获取当前用户自己的礼物详情（含完整故事和审核备注）。
    Phase 2H-1: 仅返回自己的礼物，非自己 → 404。
    """
    user_id = _require_auth(request)
    conn = get_connection()

    # Verify ownership
    owner_id = _get_gift_owner(gift_id, conn)
    if owner_id is None:
        close_connection(conn)
        raise HTTPException(status_code=404, detail="礼物不存在")
    if owner_id != user_id:
        close_connection(conn)
        raise HTTPException(status_code=404, detail="礼物不存在")

    sql = """
        SELECT g.*, u.anonymous_nickname,
               gs.short_story, gs.full_story,
               gs.risk_level, gs.story_quality_score,
               gs.created_at as story_created_at
        FROM gifts g
        JOIN users u ON g.user_id = u.id
        LEFT JOIN gift_stories gs ON g.id = gs.gift_id
        WHERE g.id = ?
    """
    cur = conn.execute(sql, [gift_id])
    row = cur.fetchone()

    # Get last admin review note
    review_note = _get_last_review_note(gift_id, conn)

    close_connection(conn)

    if not row:
        raise HTTPException(status_code=404, detail="礼物不存在")

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
        "relation_type": row["relation_type"],
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
        "updated_at": row["updated_at"],
        "review_note": review_note,
    })


@router.patch("/me/gifts/{gift_id}")
def update_my_gift(gift_id: str, payload: dict, request: Request):
    """
    编辑自己的礼物。
    Phase 2H-1: 仅 draft / pending_review / needs_edit 可编辑。
    编辑 story 后重新运行审核。
    """
    user_id = _require_auth(request)
    conn = get_connection()

    # Verify ownership
    owner_id = _get_gift_owner(gift_id, conn)
    if owner_id is None:
        close_connection(conn)
        raise HTTPException(status_code=404, detail="礼物不存在")
    if owner_id != user_id:
        close_connection(conn)
        raise HTTPException(status_code=404, detail="礼物不存在")

    # Check current status
    cur = conn.execute("SELECT status FROM gifts WHERE id = ?", [gift_id])
    current_status = cur.fetchone()["status"]
    if current_status not in _EDITABLE_STATUSES:
        close_connection(conn)
        raise HTTPException(
            status_code=409,
            detail={"code": 409, "message": f"当前状态「{current_status}」不允许编辑", "data": None}
        )

    # Build update fields
    allowed_fields = {
        "title", "category", "relation_type", "relation_label",
        "action_type", "emotion", "price_or_exchange", "condition_note",
        "city_blur", "is_anonymous", "short_story", "full_story"
    }
    updates = {}
    for key in allowed_fields:
        if key in payload:
            updates[key] = payload[key]

    if not updates:
        close_connection(conn)
        raise HTTPException(status_code=400, detail="没有提供可编辑的字段")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update gifts table
    gift_cols = [k for k in updates if k not in ("short_story", "full_story")]
    if gift_cols:
        set_clause = ", ".join([f"{c} = ?" for c in gift_cols])
        values = [updates[c] for c in gift_cols] + [now, gift_id]
        conn.execute(f"UPDATE gifts SET {set_clause}, updated_at = ? WHERE id = ?", values)

    # Update gift_stories if story fields changed
    story_cols = [k for k in updates if k in ("short_story", "full_story")]
    if story_cols:
        story_set = ", ".join([f"{c} = ?" for c in story_cols])
        story_values = [updates[c] for c in story_cols] + [gift_id]
        conn.execute(f"UPDATE gift_stories SET {story_set} WHERE gift_id = ?", story_values)

        # Re-run moderation review
        short_story = updates.get("short_story", "")
        full_story = updates.get("full_story", "")
        review_info = _review_and_log(gift_id, short_story, full_story, conn)

        # Update risk_level on gift_stories
        conn.execute(
            "UPDATE gift_stories SET risk_level = ? WHERE gift_id = ?",
            [review_info["risk_level"], gift_id]
        )
    else:
        review_info = None

    conn.commit()

    # Fetch updated gift
    cur = conn.execute("""
        SELECT g.*, u.anonymous_nickname,
               gs.short_story, gs.full_story,
               gs.risk_level, gs.story_quality_score,
               gs.created_at as story_created_at
        FROM gifts g
        JOIN users u ON g.user_id = u.id
        LEFT JOIN gift_stories gs ON g.id = gs.gift_id
        WHERE g.id = ?
    """, [gift_id])
    row = cur.fetchone()
    close_connection(conn)

    story = None
    if row and row["short_story"]:
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
        "relation_type": row["relation_type"],
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
        "updated_at": row["updated_at"],
        "review": review_info,
    })


@router.post("/me/gifts/{gift_id}/resubmit")
def resubmit_my_gift(gift_id: str, request: Request):
    """
    重新提交礼物审核。
    Phase 2H-1: 仅 draft / needs_edit 可重新提交。
    重新运行审核，状态变为 pending_review（保守策略）。
    """
    user_id = _require_auth(request)
    conn = get_connection()

    # Verify ownership
    owner_id = _get_gift_owner(gift_id, conn)
    if owner_id is None:
        close_connection(conn)
        raise HTTPException(status_code=404, detail="礼物不存在")
    if owner_id != user_id:
        close_connection(conn)
        raise HTTPException(status_code=404, detail="礼物不存在")

    # Check current status
    cur = conn.execute("SELECT status FROM gifts WHERE id = ?", [gift_id])
    current_status = cur.fetchone()["status"]
    if current_status not in _RESUBMITTABLE_STATUSES:
        close_connection(conn)
        raise HTTPException(
            status_code=409,
            detail={"code": 409, "message": f"当前状态「{current_status}」不允许重新提交", "data": None}
        )

    # Fetch story for re-review
    cur = conn.execute(
        "SELECT short_story, full_story FROM gift_stories WHERE gift_id = ?",
        [gift_id]
    )
    story_row = cur.fetchone()
    short_story = story_row["short_story"] if story_row else ""
    full_story = story_row["full_story"] if story_row else ""

    # Re-run review
    review_info = _review_and_log(gift_id, short_story, full_story, conn)
    risk_level = review_info["risk_level"]

    # Conservative: always pending_review after resubmit
    new_status = "pending_review"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute(
        "UPDATE gifts SET status = ?, updated_at = ? WHERE id = ?",
        [new_status, now, gift_id]
    )
    conn.commit()
    close_connection(conn)

    return wrap({
        "gift_id": gift_id,
        "previous_status": current_status,
        "new_status": new_status,
        "risk_level": risk_level,
        "review": review_info,
    }, message="已重新进入审核队列")


@router.post("/me/gifts/{gift_id}/archive")
def archive_my_gift(gift_id: str, request: Request):
    """
    撤回（归档）自己的礼物。
    Phase 2H-1: published / pending_review / needs_edit 可归档。
    状态变为 archived，普通列表不再返回。
    """
    user_id = _require_auth(request)
    conn = get_connection()

    # Verify ownership
    owner_id = _get_gift_owner(gift_id, conn)
    if owner_id is None:
        close_connection(conn)
        raise HTTPException(status_code=404, detail="礼物不存在")
    if owner_id != user_id:
        close_connection(conn)
        raise HTTPException(status_code=404, detail="礼物不存在")

    # Check current status
    cur = conn.execute("SELECT status FROM gifts WHERE id = ?", [gift_id])
    current_status = cur.fetchone()["status"]
    if current_status not in _ARCHIVABLE_STATUSES:
        close_connection(conn)
        raise HTTPException(
            status_code=409,
            detail={"code": 409, "message": f"当前状态「{current_status}」不允许归档", "data": None}
        )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE gifts SET status = ?, updated_at = ? WHERE id = ?",
        ["archived", now, gift_id]
    )

    # Log to admin_actions as user action (MVP temporary pattern)
    action_id = f"act-{uuid.uuid4().hex[:8]}"
    conn.execute("""
        INSERT INTO admin_actions (id, admin_id, target_type, target_id, action, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        action_id, f"self:{user_id}", "gift", gift_id, "take_action",
        f"用户自行归档礼物（原状态：{current_status}）", now
    ))

    conn.commit()
    close_connection(conn)

    return wrap({
        "gift_id": gift_id,
        "previous_status": current_status,
        "new_status": "archived",
    }, message="这件礼物已暂时收起")
