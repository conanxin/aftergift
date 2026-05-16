"""
Aftergift Backend - Favorites Router
Phase 2B | POST/DELETE /api/gifts/{id}/favorite
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.database import get_connection, close_connection
from app.auth import _require_auth

router = APIRouter(prefix="/gifts", tags=["favorites"])


def wrap(data, code=200, message="success"):
    return JSONResponse(content={"code": code, "message": message, "data": data}, status_code=code)


@router.post("/{gift_id}/favorite")
def add_favorite(gift_id: str, request: Request):
    """
    收藏礼物。Phase 2J-1:
    - 需要 Bearer token，无 token → 401
    - 幂等：重复收藏返回 200（已收藏状态）
    - 返回 is_favorited + favorite_count
    - 不允许收藏 archived/rejected/pending_review/needs_edit/draft
    """
    user_id = _require_auth(request)
    conn = get_connection()

    # Check gift exists and status
    cur = conn.execute(
        "SELECT id, status FROM gifts WHERE id = ?", [gift_id]
    )
    row = cur.fetchone()
    if not row:
        close_connection(conn)
        raise HTTPException(status_code=404, detail="礼物不存在")

    BLOCKED_STATUSES = {"archived", "rejected", "pending_review", "needs_edit", "draft"}
    if row["status"] in BLOCKED_STATUSES:
        close_connection(conn)
        raise HTTPException(status_code=422, detail="该礼物当前无法被收藏")

    # Check already favorited — make idempotent
    cur = conn.execute(
        "SELECT id FROM favorites WHERE user_id = ? AND gift_id = ?",
        [user_id, gift_id]
    )
    existing = cur.fetchone()

    if existing:
        # Already favorited — return 200 idempotent
        # Query count BEFORE closing; never use conn after close
        fav_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM favorites WHERE gift_id = ?", [gift_id]
        ).fetchone()["cnt"]
        close_connection(conn)
        return wrap({
            "gift_id": gift_id,
            "is_favorited": True,
            "favorite_count": fav_count,
        }, code=200, message="已经收藏过了")

    # Insert favorite
    fav_id = f"fav-{uuid.uuid4().hex[:8]}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO favorites (id, user_id, gift_id, created_at) VALUES (?, ?, ?, ?)",
        [fav_id, user_id, gift_id, now]
    )
    conn.commit()

    # Get updated count
    fav_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM favorites WHERE gift_id = ?", [gift_id]
    ).fetchone()["cnt"]
    close_connection(conn)

    return wrap({
        "favorite_id": fav_id,
        "gift_id": gift_id,
        "is_favorited": True,
        "favorite_count": fav_count,
    }, code=201, message="已收藏这个故事")


@router.delete("/{gift_id}/favorite")
def remove_favorite(gift_id: str, request: Request):
    """
    取消收藏。Phase 2J-1:
    - 需要 Bearer token
    - 幂等：重复取消返回 200
    - 返回 is_favorited + favorite_count
    """
    user_id = _require_auth(request)
    conn = get_connection()

    cur = conn.execute(
        "DELETE FROM favorites WHERE user_id = ? AND gift_id = ?",
        [user_id, gift_id]
    )
    conn.commit()

    # Get updated count after delete
    fav_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM favorites WHERE gift_id = ?", [gift_id]
    ).fetchone()["cnt"]
    close_connection(conn)

    return wrap({
        "gift_id": gift_id,
        "is_favorited": False,
        "favorite_count": fav_count,
    }, message="已取消收藏")
