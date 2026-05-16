"""
Aftergift Backend - Me Router (User Self-Service)
Phase 2H-2 | Clean API alias for personal gift management

Paths:
  GET    /api/me/gifts/{gift_id}
  PATCH  /api/me/gifts/{gift_id}
  POST   /api/me/gifts/{gift_id}/resubmit
  POST   /api/me/gifts/{gift_id}/archive
  POST   /api/me/gifts/{gift_id}/restore
  GET    /api/me/actions

Legacy paths (still available):
  /api/gifts/me/gifts/{gift_id}  (from gifts router)
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.database import get_connection, close_connection
from app.auth import _require_auth
from app.routers.gifts import (
    _get_gift_owner,
    _get_last_review_note,
    _review_and_log,
    _EDITABLE_STATUSES,
    _RESUBMITTABLE_STATUSES,
    _ARCHIVABLE_STATUSES,
    wrap,
    _build_action_label,
)

router = APIRouter(prefix="/me", tags=["me"])

# ── Restore status ───────────────────────────────────────────────────────────
_RESTORABLE_STATUSES = {"archived"}


def _record_user_action(conn, user_id: str, gift_id: str | None, action: str, note: str | None = None):
    """Write a user-initiated action to user_actions table."""
    conn.execute(
        "INSERT INTO user_actions (user_id, gift_id, action, note, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, gift_id, action, note, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )


def _require_owner(gift_id: str, user_id: str, conn):
    """Verify gift exists and belongs to user. Raises 404 on failure."""
    owner_id = _get_gift_owner(gift_id, conn)
    if owner_id is None or owner_id != user_id:
        raise HTTPException(status_code=404, detail="礼物不存在")


def _fetch_gift_detail(gift_id: str, conn):
    """Fetch gift + story + nickname for response building."""
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
    return cur.fetchone()


def _build_gift_response(row, review_note=None, review_info=None):
    """Build standard gift detail response dict from a DB row."""
    story = None
    if row and row["short_story"]:
        story = {
            "short_story": row["short_story"],
            "full_story": row["full_story"],
            "risk_level": row["risk_level"],
            "quality_score": row["story_quality_score"],
            "created_at": row["story_created_at"]
        }
    resp = {
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
    }
    if review_info:
        resp["review"] = review_info
    return resp


# ── GET /api/me/gifts/{gift_id} ─────────────────────────────────────────────

@router.get("/gifts/{gift_id}")
def get_my_gift(gift_id: str, request: Request):
    """Get current user's gift detail (alias of legacy path)."""
    user_id = _require_auth(request)
    conn = get_connection()
    try:
        _require_owner(gift_id, user_id, conn)
        row = _fetch_gift_detail(gift_id, conn)
        if not row:
            raise HTTPException(status_code=404, detail="礼物不存在")
        review_note = _get_last_review_note(gift_id, conn)
        return wrap(_build_gift_response(row, review_note))
    finally:
        close_connection(conn)


# ── PATCH /api/me/gifts/{gift_id} ───────────────────────────────────────────

@router.patch("/gifts/{gift_id}")
def update_my_gift(gift_id: str, payload: dict, request: Request):
    """Edit current user's gift."""
    user_id = _require_auth(request)
    conn = get_connection()
    try:
        _require_owner(gift_id, user_id, conn)

        cur = conn.execute("SELECT status FROM gifts WHERE id = ?", [gift_id])
        current_status = cur.fetchone()["status"]
        if current_status not in _EDITABLE_STATUSES:
            raise HTTPException(
                status_code=409,
                detail={"code": 409, "message": f"当前状态「{current_status}」不允许编辑", "data": None}
            )

        allowed_fields = {
            "title", "category", "relation_type", "relation_label",
            "action_type", "emotion", "price_or_exchange", "condition_note",
            "city_blur", "is_anonymous", "short_story", "full_story"
        }
        updates = {k: v for k, v in payload.items() if k in allowed_fields}
        if not updates:
            raise HTTPException(status_code=400, detail="没有提供可编辑的字段")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        gift_cols = [k for k in updates if k not in ("short_story", "full_story")]
        if gift_cols:
            set_clause = ", ".join([f"{c} = ?" for c in gift_cols])
            values = [updates[c] for c in gift_cols] + [now, gift_id]
            conn.execute(f"UPDATE gifts SET {set_clause}, updated_at = ? WHERE id = ?", values)

        review_info = None
        story_cols = [k for k in updates if k in ("short_story", "full_story")]
        if story_cols:
            story_set = ", ".join([f"{c} = ?" for c in story_cols])
            story_values = [updates[c] for c in story_cols] + [gift_id]
            conn.execute(f"UPDATE gift_stories SET {story_set} WHERE gift_id = ?", story_values)

            short_story = updates.get("short_story", "")
            full_story = updates.get("full_story", "")
            review_info = _review_and_log(gift_id, short_story, full_story, conn)
            conn.execute(
                "UPDATE gift_stories SET risk_level = ? WHERE gift_id = ?",
                [review_info["risk_level"], gift_id]
            )

        _record_user_action(conn, user_id, gift_id, "edit", f"编辑礼物（状态：{current_status}）")
        conn.commit()

        row = _fetch_gift_detail(gift_id, conn)
        return wrap(_build_gift_response(row, review_info=review_info))
    finally:
        close_connection(conn)


# ── POST /api/me/gifts/{gift_id}/resubmit ───────────────────────────────────

@router.post("/gifts/{gift_id}/resubmit")
def resubmit_my_gift(gift_id: str, request: Request):
    """Resubmit gift for review."""
    user_id = _require_auth(request)
    conn = get_connection()
    try:
        _require_owner(gift_id, user_id, conn)

        cur = conn.execute("SELECT status FROM gifts WHERE id = ?", [gift_id])
        current_status = cur.fetchone()["status"]
        if current_status not in _RESUBMITTABLE_STATUSES:
            raise HTTPException(
                status_code=409,
                detail={"code": 409, "message": f"当前状态「{current_status}」不允许重新提交", "data": None}
            )

        cur = conn.execute("SELECT short_story, full_story FROM gift_stories WHERE gift_id = ?", [gift_id])
        story_row = cur.fetchone()
        short_story = story_row["short_story"] if story_row else ""
        full_story = story_row["full_story"] if story_row else ""

        review_info = _review_and_log(gift_id, short_story, full_story, conn)
        new_status = "pending_review"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute(
            "UPDATE gifts SET status = ?, updated_at = ? WHERE id = ?",
            [new_status, now, gift_id]
        )
        _record_user_action(conn, user_id, gift_id, "resubmit", f"重新提交审核（原状态：{current_status}）")
        conn.commit()

        return wrap({
            "gift_id": gift_id,
            "previous_status": current_status,
            "new_status": new_status,
            "risk_level": review_info["risk_level"],
            "review": review_info,
        }, message="已重新进入审核队列")
    finally:
        close_connection(conn)


# ── POST /api/me/gifts/{gift_id}/archive ────────────────────────────────────

@router.post("/gifts/{gift_id}/archive")
def archive_my_gift(gift_id: str, request: Request):
    """Archive (withdraw) current user's gift."""
    user_id = _require_auth(request)
    conn = get_connection()
    try:
        _require_owner(gift_id, user_id, conn)

        cur = conn.execute("SELECT status FROM gifts WHERE id = ?", [gift_id])
        current_status = cur.fetchone()["status"]
        if current_status not in _ARCHIVABLE_STATUSES:
            raise HTTPException(
                status_code=409,
                detail={"code": 409, "message": f"当前状态「{current_status}」不允许归档", "data": None}
            )

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE gifts SET status = ?, updated_at = ? WHERE id = ?",
            ["archived", now, gift_id]
        )
        _record_user_action(conn, user_id, gift_id, "archive", f"归档礼物（原状态：{current_status}）")
        conn.commit()

        return wrap({
            "gift_id": gift_id,
            "previous_status": current_status,
            "new_status": "archived",
        }, message="这件礼物已暂时收起")
    finally:
        close_connection(conn)


# ── POST /api/me/gifts/{gift_id}/restore ────────────────────────────────────

@router.post("/gifts/{gift_id}/restore")
def restore_my_gift(gift_id: str, request: Request):
    """Restore an archived gift back to pending_review."""
    user_id = _require_auth(request)
    conn = get_connection()
    try:
        _require_owner(gift_id, user_id, conn)

        cur = conn.execute("SELECT status FROM gifts WHERE id = ?", [gift_id])
        current_status = cur.fetchone()["status"]
        if current_status not in _RESTORABLE_STATUSES:
            raise HTTPException(
                status_code=409,
                detail={"code": 409, "message": f"当前状态「{current_status}」不允许恢复", "data": None}
            )

        cur = conn.execute("SELECT short_story, full_story FROM gift_stories WHERE gift_id = ?", [gift_id])
        story_row = cur.fetchone()
        short_story = story_row["short_story"] if story_row else ""
        full_story = story_row["full_story"] if story_row else ""

        review_info = _review_and_log(gift_id, short_story, full_story, conn)
        new_status = "pending_review"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute(
            "UPDATE gifts SET status = ?, updated_at = ? WHERE id = ?",
            [new_status, now, gift_id]
        )
        _record_user_action(conn, user_id, gift_id, "restore", "用户恢复归档礼物并重新进入审核")
        conn.commit()

        return wrap({
            "gift_id": gift_id,
            "previous_status": current_status,
            "new_status": new_status,
            "risk_level": review_info["risk_level"],
            "review": review_info,
        }, message="这件礼物已重新进入审核")
    finally:
        close_connection(conn)


# ── GET /api/me/actions ─────────────────────────────────────────────────────

@router.get("/actions")
def get_my_actions(
    request: Request,
    gift_id: str | None = Query(None),
    action: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get current user's action history."""
    user_id = _require_auth(request)
    conn = get_connection()
    try:
        where_clauses = ["ua.user_id = ?"]
        params = [user_id]

        if gift_id:
            where_clauses.append("ua.gift_id = ?")
            params.append(gift_id)
        if action:
            where_clauses.append("ua.action = ?")
            params.append(action)

        where_sql = " AND ".join(where_clauses)

        # Count total
        count_sql = f"SELECT COUNT(*) as cnt FROM user_actions ua WHERE {where_sql}"
        total = conn.execute(count_sql, params).fetchone()["cnt"]

        # Fetch items with gift title
        offset = (page - 1) * limit
        items_sql = f"""
            SELECT ua.*, g.title as gift_title
            FROM user_actions ua
            LEFT JOIN gifts g ON ua.gift_id = g.id
            WHERE {where_sql}
            ORDER BY ua.created_at DESC
            LIMIT ? OFFSET ?
        """
        items_params = params + [limit, offset]
        cur = conn.execute(items_sql, items_params)

        items = []
        for row in cur.fetchall():
            items.append({
                "id": row["id"],
                "user_id": row["user_id"],
                "gift_id": row["gift_id"],
                "gift_title": row["gift_title"],
                "action": row["action"],
                "note": row["note"],
                "created_at": row["created_at"],
            })

        total_pages = (total + limit - 1) // limit
        return wrap({
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        })
    finally:
        close_connection(conn)
