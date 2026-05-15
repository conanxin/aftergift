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
    return JSONResponse(content={"code": code, "message": message, "data": data})


@router.post("/{gift_id}/favorite")
def add_favorite(gift_id: str, request: Request):
    """
    收藏礼物。

    Phase 2D：
    - 需要 Bearer token
    - 无 token → 401
    """
    user_id = _require_auth(request)
    conn = get_connection()

    # Check gift exists
    cur = conn.execute("SELECT id FROM gifts WHERE id = ?", [gift_id])
    if not cur.fetchone():
        close_connection(conn)
        raise HTTPException(status_code=404, detail="礼物不存在")

    # Check already favorited
    cur = conn.execute(
        "SELECT id FROM favorites WHERE user_id = ? AND gift_id = ?",
        [user_id, gift_id]
    )
    if cur.fetchone():
        close_connection(conn)
        raise HTTPException(status_code=409, detail="已经收藏过了")

    # Insert favorite
    fav_id = f"fav-{uuid.uuid4().hex[:8]}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO favorites (id, user_id, gift_id, created_at) VALUES (?, ?, ?, ?)",
        [fav_id, user_id, gift_id, now]
    )
    conn.commit()
    close_connection(conn)

    return wrap({"favorite_id": fav_id, "gift_id": gift_id}, code=201, message="已收藏这个故事")


@router.delete("/{gift_id}/favorite")
def remove_favorite(gift_id: str, request: Request):
    """取消收藏。Phase 2D：需要 Bearer token。"""
    user_id = _require_auth(request)
    conn = get_connection()
    cur = conn.execute(
        "DELETE FROM favorites WHERE user_id = ? AND gift_id = ?",
        [user_id, gift_id]
    )
    deleted = cur.rowcount
    conn.commit()
    close_connection(conn)

    if deleted == 0:
        raise HTTPException(status_code=404, detail="收藏记录不存在")

    return wrap(None, message="已取消收藏")
