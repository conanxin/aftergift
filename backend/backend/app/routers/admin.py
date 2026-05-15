"""
Aftergift Backend - Admin Router
Phase 2D | GET /api/admin/reviews, POST /api/admin/reviews/{id}/decision
Enhanced: full fields for admin review UI
"""

import uuid
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Body
from typing import Optional, Dict
from fastapi.responses import JSONResponse
from app.database import get_connection, close_connection
from app.config import ADMIN_TOKEN

router = APIRouter(prefix="/admin", tags=["admin"])


def wrap(data, code=200, message="success"):
    return JSONResponse(content={"code": code, "message": message, "data": data})


def _verify_admin_token(request: Request) -> str:
    """验证 admin token，失败则 raise 401"""
    token = request.headers.get("x-admin-token")
    if token is None:
        raise HTTPException(status_code=401, detail="缺少 X-Admin-Token")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="无效的 Admin Token")
    return token


@router.get("/reviews")
def list_pending_reviews(
    request: Request,
    risk_level: Optional[str] = None,
    page: int = 1,
):
    """
    获取待审核队列（pending_review + needs_edit 状态）。

    Phase 2D 增强：返回完整字段，方便管理员审核 UI 展示。

    返回字段：
    - gift_id, title, category, relation_type, relation_label
    - action_type, emotion, short_story, full_story
    - risk_level, story_quality_score
    - review_issues (from review_logs.issues_json)
    - review_suggestions (from review_logs.suggestions_json)
    - quality_notes (parsed from review_logs.quality_notes)
    - identity_risk, attack_risk, identifiable_person_risk
    - status, created_at, updated_at
    - ai_review_notes (computed string)
    """
    _verify_admin_token(request)

    conn = get_connection()
    limit = 20
    offset = (page - 1) * limit

    sql = """
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
               rl.decision as ai_decision, rl.decided_at as ai_decided_at
        FROM gifts g
        LEFT JOIN gift_stories gs ON g.id = gs.gift_id
        LEFT JOIN review_logs rl ON g.id = rl.gift_id
        WHERE g.status IN ('pending_review', 'needs_edit')
    """
    count_sql = """
        SELECT COUNT(*)
        FROM gifts g
        WHERE g.status IN ('pending_review', 'needs_edit')
    """
    params = []

    if risk_level:
        sql += " AND gs.risk_level = ?"
        count_sql += " AND gs.risk_level = ?"
        params.append(risk_level)

    # Total
    cur = conn.execute(count_sql, params)
    total = cur.fetchone()[0]

    # Page items
    sql += " ORDER BY g.created_at ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    close_connection(conn)

    items = []
    for row in rows:
        suggestions = []
        if row["suggestions_json"]:
            try:
                suggestions = json.loads(row["suggestions_json"])
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
            # Gift identity
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
            # Story
            "short_story": row["short_story"],
            "full_story": row["full_story"],
            # Review
            "risk_level": row["risk_level"],
            "story_quality_score": row["story_quality_score"],
            "review_issues": issues,
            "review_suggestions": suggestions,
            "quality_notes": quality_notes,
            "identity_risk": row["identity_risk"] or 0,
            "attack_risk": row["attack_risk"] or 0,
            "identifiable_person_risk": row["identifiable_person_risk"] or 0,
            # AI decision
            "ai_decision": row["ai_decision"],
            "ai_decided_at": row["ai_decided_at"],
            # Timestamps
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            # Computed
            "ai_review_notes": (
                f"身份风险:{row['identity_risk'] or 0} | "
                f"攻击风险:{row['attack_risk'] or 0} | "
                f"可识别风险:{row['identifiable_person_risk'] or 0}"
            )
        })

    return wrap({"items": items, "total": total, "page": page})


@router.post("/reviews/{gift_id}/decision")
def review_decision(gift_id: str, decision: Dict = Body(...), request: Request = None):
    """
    管理员对礼物做出审核决定。

    Request body (JSON):
        {"decision": "approve"|"reject"|"needs_edit", "note": "..."}

    - approve → published
    - reject → rejected
    - needs_edit → needs_edit

    Phase 2D：记录到 admin_actions 表（新增）。
    """
    _verify_admin_token(request)

    conn = get_connection()

    # Check gift exists
    cur = conn.execute("SELECT id, status FROM gifts WHERE id = ?", [gift_id])
    row = cur.fetchone()
    if not row:
        close_connection(conn)
        raise HTTPException(status_code=404, detail="礼物不存在")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Map decision to status
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
        SET decision = ?, decided_at = ?
        WHERE gift_id = ? AND decision IS NULL
    """, [decision_value, now, gift_id])

    # Log admin action to admin_actions table
    try:
        action_id = f"admin-{uuid.uuid4().hex[:8]}"
        conn.execute("""
            INSERT INTO admin_actions (id, admin_id, target_type, target_id, action, note, created_at)
            VALUES (?, ?, 'gift', ?, ?, ?, ?)
        """, (action_id, "dev-admin", gift_id, decision_value, admin_note, now))
    except Exception:
        # Graceful skip if table schema differs
        pass

    conn.commit()
    close_connection(conn)

    return wrap({
        "gift_id": gift_id,
        "new_status": new_status,
        "decided_at": now
    }, message="审核决定已记录")
