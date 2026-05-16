"""
Aftergift Backend - Admin Router
Phase 2D  | GET /api/admin/reviews, POST /api/admin/reviews/{id}/decision
Phase 2E-3 | Admin queue shows redacted review data
Phase 2F   | Enhanced admin workflow: filters, pagination, reports, logs, actions
"""

import uuid
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Body, Query
from typing import Optional, Dict, List
from fastapi.responses import JSONResponse
from app.database import get_connection, close_connection
from app.config import ADMIN_TOKEN

router = APIRouter(prefix="/admin", tags=["admin"])


def wrap(data, code=200, message="success"):
    return JSONResponse(content={"code": code, "message": message, "data": data})


def _verify_admin_token(request: Request) -> str:
    """验证 admin token，失败则 raise 401/403"""
    token = request.headers.get("x-admin-token")
    if token is None:
        raise HTTPException(status_code=401, detail="缺少 X-Admin-Token")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="无效的 Admin Token")
    return token


# ── Phase 2F: Enhanced GET /api/admin/reviews ────────────────────────────────

VALID_STATUSES = {"pending_review", "needs_edit", "rejected", "published", "archived"}
VALID_RISK_LEVELS = {"safe", "caution", "high_risk"}
VALID_PROVIDERS = {"mock", "openai", "baidu", "openai+mock"}
VALID_SORT_FIELDS = {"created_at", "risk_level", "status"}
VALID_ORDERS = {"asc", "desc"}


@router.get("/reviews")
def list_reviews(
    request: Request,
    status: Optional[str] = Query(None, description="pending_review | needs_edit | rejected | published | archived"),
    risk_level: Optional[str] = Query(None, description="safe | caution | high_risk"),
    provider: Optional[str] = Query(None, description="mock | openai | baidu | openai+mock"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("created_at", description="created_at | risk_level | status"),
    order: str = Query("desc", description="asc | desc"),
):
    """
    获取审核队列，支持多维度筛选、分页、排序。
    Phase 2F 增强：兼容旧前端，新增 provider 筛选与完整分页信息。
    """
    _verify_admin_token(request)

    # Validate inputs
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"无效的 status: {status}")
    if risk_level and risk_level not in VALID_RISK_LEVELS:
        raise HTTPException(status_code=400, detail=f"无效的 risk_level: {risk_level}")
    if provider and provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"无效的 provider: {provider}")
    if sort not in VALID_SORT_FIELDS:
        raise HTTPException(status_code=400, detail=f"无效的 sort: {sort}")
    if order not in VALID_ORDERS:
        raise HTTPException(status_code=400, detail=f"无效的 order: {order}")

    conn = get_connection()
    offset = (page - 1) * limit

    # Build WHERE clauses safely
    where_clauses = []
    params: List = []

    if status:
        where_clauses.append("g.status = ?")
        params.append(status)
    else:
        # Default: pending_review + needs_edit (backward compat)
        where_clauses.append("g.status IN ('pending_review', 'needs_edit')")

    if risk_level:
        where_clauses.append("gs.risk_level = ?")
        params.append(risk_level)

    if provider:
        where_clauses.append("rl.reviewer_type = ?")
        params.append(provider)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Sort mapping
    sort_col = {
        "created_at": "g.created_at",
        "risk_level": "gs.risk_level",
        "status": "g.status",
    }[sort]
    order_sql = order.upper()

    sql = f"""
        SELECT g.id as gift_id, g.title, g.category,
               g.relation_type, g.relation_label,
               g.action_type, g.emotion,
               g.price_or_exchange, g.condition_note,
               g.status, g.is_anonymous,
               g.created_at, g.updated_at,
               gs.short_story, gs.full_story,
               gs.risk_level, gs.story_quality_score,
               rl.suggestions_json, rl.quality_notes,
               rl.identity_risk, rl.attack_risk, rl.identifiable_person_risk,
                rl.reviewer_type, rl.decision as ai_decision, rl.decided_at as ai_decided_at,
                COALESCE(rl.redaction_summary, '') as redaction_summary
        FROM gifts g
        LEFT JOIN gift_stories gs ON g.id = gs.gift_id
        LEFT JOIN review_logs rl ON g.id = rl.gift_id
        WHERE {where_sql}
        ORDER BY {sort_col} {order_sql}
        LIMIT ? OFFSET ?
    """

    count_sql = f"""
        SELECT COUNT(*)
        FROM gifts g
        LEFT JOIN gift_stories gs ON g.id = gs.gift_id
        LEFT JOIN review_logs rl ON g.id = rl.gift_id
        WHERE {where_sql}
    """

    # Total count
    cur = conn.execute(count_sql, params)
    total = cur.fetchone()[0]

    # Page items
    query_params = params + [limit, offset]
    cur = conn.execute(sql, query_params)
    rows = cur.fetchall()
    close_connection(conn)

    items = []
    for row in rows:
        suggestions = []
        redaction_summary = None
        if row["suggestions_json"]:
            try:
                parsed = json.loads(row["suggestions_json"])
                if isinstance(parsed, dict):
                    suggestions = parsed.get("suggestions", [])
                    redaction_summary = parsed.get("redaction_summary")
                else:
                    suggestions = parsed
            except Exception:
                suggestions = []

        issues = []
        quality_notes = {}
        if row["quality_notes"]:
            try:
                quality_notes = json.loads(row["quality_notes"])
            except Exception:
                quality_notes = {}

        items.append({
            "gift_id": row["gift_id"],
            "title": row["title"],
            "category": row["category"],
            "relation_type": row["relation_type"],
            "relation_label": row["relation_label"],
            "action_type": row["action_type"],
            "emotion": row["emotion"],
            "price_or_exchange": row["price_or_exchange"],
            "condition_note": row["condition_note"],
            "status": row["status"],
            "is_anonymous": bool(row["is_anonymous"]),
            "short_story": row["short_story"],
            "full_story": row["full_story"],
            "risk_level": row["risk_level"],
            "story_quality_score": row["story_quality_score"],
            "review_issues": issues,
            "review_suggestions": suggestions,
            "quality_notes": quality_notes,
            "redaction_summary": redaction_summary,
            "identity_risk": row["identity_risk"] or 0,
            "attack_risk": row["attack_risk"] or 0,
            "identifiable_person_risk": row["identifiable_person_risk"] or 0,
            "provider": row["reviewer_type"] or "mock",
            "ai_decision": row["ai_decision"],
            "ai_decided_at": row["ai_decided_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "ai_review_notes": (
                f"身份风险:{row['identity_risk'] or 0} | "
                f"攻击风险:{row['attack_risk'] or 0} | "
                f"可识别风险:{row['identifiable_person_risk'] or 0}"
            )
        })

    total_pages = (total + limit - 1) // limit

    return wrap({
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "filters": {
            "status": status,
            "risk_level": risk_level,
            "provider": provider,
            "sort": sort,
            "order": order,
        }
    })


# ── Phase 2F: Enhanced POST /api/admin/reviews/{gift_id}/decision ────────────

@router.post("/reviews/{gift_id}/decision")
def review_decision(gift_id: str, decision: Dict = Body(...), request: Request = None):
    """
    管理员对礼物做出审核决定。

    Request body:
        {"decision": "approve"|"reject"|"needs_edit", "note": "..."}

    - approve → published
    - reject → rejected
    - needs_edit → needs_edit
    """
    _verify_admin_token(request)

    conn = get_connection()

    cur = conn.execute("SELECT id, status FROM gifts WHERE id = ?", [gift_id])
    row = cur.fetchone()
    if not row:
        close_connection(conn)
        raise HTTPException(status_code=404, detail="礼物不存在")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    decision_value = decision.get("decision", "")
    status_map = {
        "approve": "published",
        "reject": "rejected",
        "needs_edit": "needs_edit"
    }
    new_status = status_map.get(decision_value)
    if new_status is None:
        close_connection(conn)
        raise HTTPException(status_code=400, detail="无效的审核决定")

    admin_note = decision.get("note", "") or ""

    # Update gift status
    conn.execute(
        "UPDATE gifts SET status = ?, updated_at = ? WHERE id = ?",
        [new_status, now, gift_id]
    )

    # Update review_logs decision
    conn.execute("""
        UPDATE review_logs
        SET decision = ?, decided_at = ?, decided_by = ?
        WHERE gift_id = ? AND decision IS NULL
    """, [decision_value, now, "dev-admin", gift_id])

    # Log admin action
    try:
        action_id = f"admin-{uuid.uuid4().hex[:8]}"
        conn.execute("""
            INSERT INTO admin_actions (id, admin_id, target_type, target_id, action, note, created_at)
            VALUES (?, ?, 'gift', ?, ?, ?, ?)
        """, (action_id, "dev-admin", gift_id, decision_value, admin_note, now))
    except Exception:
        pass

    conn.commit()
    close_connection(conn)

    return wrap({
        "gift_id": gift_id,
        "new_status": new_status,
        "decision": decision_value,
        "note": admin_note,
        "decided_at": now
    }, message="审核决定已记录")


# ── Phase 2F: GET /api/admin/reports ─────────────────────────────────────────

VALID_REPORT_STATUSES = {"pending", "reviewing", "resolved_dismissed", "resolved_action_taken"}
VALID_REPORT_REASONS = {"privacy", "attack", "fake", "other"}


@router.get("/reports")
def list_reports(
    request: Request,
    status: Optional[str] = Query(None, description="pending | reviewing | resolved_dismissed | resolved_action_taken"),
    reason: Optional[str] = Query(None, description="privacy | attack | fake | other"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("created_at", description="created_at"),
    order: str = Query("desc", description="asc | desc"),
):
    """获取举报队列。"""
    _verify_admin_token(request)

    if status and status not in VALID_REPORT_STATUSES:
        raise HTTPException(status_code=400, detail=f"无效的 status: {status}")
    if reason and reason not in VALID_REPORT_REASONS:
        raise HTTPException(status_code=400, detail=f"无效的 reason: {reason}")
    if sort not in {"created_at"}:
        raise HTTPException(status_code=400, detail=f"无效的 sort: {sort}")
    if order not in VALID_ORDERS:
        raise HTTPException(status_code=400, detail=f"无效的 order: {order}")

    conn = get_connection()
    offset = (page - 1) * limit

    where_clauses = []
    params: List = []

    if status:
        where_clauses.append("r.status = ?")
        params.append(status)
    if reason:
        where_clauses.append("r.reason = ?")
        params.append(reason)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    order_sql = order.upper()

    sql = f"""
        SELECT r.id as report_id, r.gift_id, r.reporter_user_id, r.reason, r.detail,
               r.status, r.created_at, r.resolved_at, r.resolution_note,
               g.title as gift_title, g.status as current_gift_status
        FROM reports r
        LEFT JOIN gifts g ON r.gift_id = g.id
        WHERE {where_sql}
        ORDER BY r.created_at {order_sql}
        LIMIT ? OFFSET ?
    """

    count_sql = f"""
        SELECT COUNT(*)
        FROM reports r
        LEFT JOIN gifts g ON r.gift_id = g.id
        WHERE {where_sql}
    """

    cur = conn.execute(count_sql, params)
    total = cur.fetchone()[0]

    cur = conn.execute(sql, params + [limit, offset])
    rows = cur.fetchall()
    close_connection(conn)

    items = []
    for row in rows:
        items.append({
            "report_id": row["report_id"],
            "gift_id": row["gift_id"],
            "gift_title": row["gift_title"] or "",
            "reporter_user_id": row["reporter_user_id"] or "",
            "reason": row["reason"],
            "detail": row["detail"] or "",
            "status": row["status"],
            "created_at": row["created_at"],
            "resolved_at": row["resolved_at"],
            "resolution_note": row["resolution_note"] or "",
            "current_gift_status": row["current_gift_status"] or "",
        })

    total_pages = (total + limit - 1) // limit

    return wrap({
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "filters": {"status": status, "reason": reason, "sort": sort, "order": order}
    })


# ── Phase 2F: POST /api/admin/reports/{report_id}/decision ───────────────────

@router.post("/reports/{report_id}/decision")
def report_decision(report_id: str, decision: Dict = Body(...), request: Request = None):
    """
    处理举报。

    Request body:
        {"decision": "dismiss"|"take_action"|"needs_review", "note": "..."}
    """
    _verify_admin_token(request)

    conn = get_connection()

    cur = conn.execute("SELECT id, gift_id, status FROM reports WHERE id = ?", [report_id])
    row = cur.fetchone()
    if not row:
        close_connection(conn)
        raise HTTPException(status_code=404, detail="举报不存在")

    decision_value = decision.get("decision", "")
    status_map = {
        "dismiss": "resolved_dismissed",
        "take_action": "resolved_action_taken",
        "needs_review": "reviewing"
    }
    new_status = status_map.get(decision_value)
    if new_status is None:
        close_connection(conn)
        raise HTTPException(status_code=400, detail="无效的处理决定")

    admin_note = decision.get("note", "") or ""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update report
    conn.execute("""
        UPDATE reports
        SET status = ?, resolution_note = ?, resolved_at = ?
        WHERE id = ?
    """, [new_status, admin_note, now, report_id])

    # If take_action, set gift to pending_review for re-review
    if decision_value == "take_action":
        conn.execute("""
            UPDATE gifts SET status = 'pending_review', updated_at = ? WHERE id = ?
        """, [now, row["gift_id"]])

    # Log admin action
    try:
        action_id = f"admin-{uuid.uuid4().hex[:8]}"
        conn.execute("""
            INSERT INTO admin_actions (id, admin_id, target_type, target_id, action, note, created_at)
            VALUES (?, ?, 'report', ?, ?, ?, ?)
        """, (action_id, "dev-admin", report_id, decision_value, admin_note, now))
    except Exception:
        pass

    conn.commit()
    close_connection(conn)

    return wrap({
        "report_id": report_id,
        "new_status": new_status,
        "decision": decision_value,
        "note": admin_note,
        "resolved_at": now
    }, message="举报处理已记录")


# ── Phase 2F: GET /api/admin/reviews/{gift_id}/logs ──────────────────────────

@router.get("/reviews/{gift_id}/logs")
def get_review_logs(gift_id: str, request: Request):
    """获取指定礼物的审核日志。"""
    _verify_admin_token(request)

    conn = get_connection()
    cur = conn.execute("""
        SELECT id, gift_id, risk_level, identity_risk, attack_risk,
               identifiable_person_risk, quality_notes, suggestions_json,
               reviewer_type, created_at, COALESCE(redaction_summary, '') as redaction_summary
        FROM review_logs
        WHERE gift_id = ?
        ORDER BY created_at DESC
    """, [gift_id])
    rows = cur.fetchall()
    close_connection(conn)

    items = []
    for row in rows:
        suggestions = []
        if row["suggestions_json"]:
            try:
                parsed = json.loads(row["suggestions_json"])
                if isinstance(parsed, dict):
                    suggestions = parsed.get("suggestions", [])
                else:
                    suggestions = parsed
            except Exception:
                suggestions = []

        quality_notes = {}
        if row["quality_notes"]:
            try:
                quality_notes = json.loads(row["quality_notes"])
            except Exception:
                quality_notes = {}

        items.append({
            "id": row["id"],
            "gift_id": row["gift_id"],
            "risk_level": row["risk_level"],
            "identity_risk": row["identity_risk"] or 0,
            "attack_risk": row["attack_risk"] or 0,
            "identifiable_person_risk": row["identifiable_person_risk"] or 0,
            "quality_notes": quality_notes,
            "suggestions": suggestions,
            "reviewer_type": row["reviewer_type"],
            "created_at": row["created_at"],
            "redaction_summary": row["redaction_summary"] or None,
        })

    return wrap({"items": items, "total": len(items)})


# ── Phase 2F: GET /api/admin/actions ─────────────────────────────────────────

VALID_TARGET_TYPES = {"gift", "report", "user"}
VALID_ACTIONS = {"approve", "reject", "needs_edit", "suspend_user", "dismiss_report", "take_action"}


@router.get("/actions")
def list_admin_actions(
    request: Request,
    target_type: Optional[str] = Query(None, description="gift | report | user"),
    target_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None, description="approve | reject | needs_edit | suspend_user | dismiss_report | take_action"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """获取管理员操作历史。"""
    _verify_admin_token(request)

    if target_type and target_type not in VALID_TARGET_TYPES:
        raise HTTPException(status_code=400, detail=f"无效的 target_type: {target_type}")
    if action and action not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"无效的 action: {action}")

    conn = get_connection()
    offset = (page - 1) * limit

    where_clauses = []
    params: List = []

    if target_type:
        where_clauses.append("target_type = ?")
        params.append(target_type)
    if target_id:
        where_clauses.append("target_id = ?")
        params.append(target_id)
    if action:
        where_clauses.append("action = ?")
        params.append(action)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    sql = f"""
        SELECT id, admin_id, target_type, target_id, action, note, created_at
        FROM admin_actions
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """

    count_sql = f"""
        SELECT COUNT(*)
        FROM admin_actions
        WHERE {where_sql}
    """

    cur = conn.execute(count_sql, params)
    total = cur.fetchone()[0]

    cur = conn.execute(sql, params + [limit, offset])
    rows = cur.fetchall()
    close_connection(conn)

    items = []
    for row in rows:
        items.append({
            "id": row["id"],
            "admin_id": row["admin_id"],
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "action": row["action"],
            "note": row["note"] or "",
            "created_at": row["created_at"],
        })

    total_pages = (total + limit - 1) // limit

    return wrap({
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "filters": {"target_type": target_type, "target_id": target_id, "action": action}
    })
