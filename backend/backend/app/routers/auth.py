"""
Aftergift Backend - Auth Router
Phase 2D | POST /api/auth/anonymous, GET /api/auth/me

No real identity collected. Purely for binding mutations to a session.
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.database import get_connection, close_connection
from app.auth import _make_token, _verify_token, _get_user_nickname

router = APIRouter(prefix="/auth", tags=["auth"])


def wrap(data, code=200, message="success"):
    return JSONResponse(content={"code": code, "message": message, "data": data})


@router.post("/anonymous")
def create_anonymous_user():
    """
    创建或返回一个匿名用户身份。

    Phase 2D 实现：
    - 不要求手机号、邮箱。
    - 每次调用生成一个新 user_id。
    - 返回 user_id + access_token。
    - Phase 2E 改为：传入 phone_hash → 查找已有或创建新用户 → 返回 JWT。
    """
    conn = get_connection()

    # Generate new anonymous user
    user_id = f"user-{uuid.uuid4().hex[:12]}"
    anonymous_nickname = _get_user_nickname(user_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Insert into DB
    conn.execute("""
        INSERT INTO users (id, anonymous_nickname, created_at, status)
        VALUES (?, ?, ?, 'active')
    """, (user_id, anonymous_nickname, now))
    conn.commit()
    close_connection(conn)

    token = _make_token(user_id)

    return wrap({
        "user_id": user_id,
        "anonymous_nickname": anonymous_nickname,
        "access_token": token,
        "token_type": "Bearer"
    }, code=201, message="匿名身份创建成功")


@router.get("/me")
def get_current_user(request: Request):
    """
    返回当前登录用户信息。

    读取 Authorization: Bearer ***
    - 无 token → 401
    - token 无效 → 401
    - 有效 → 返回 user_id + anonymous_nickname
    """
    # Import here to avoid circular issues
    from app.auth import _require_auth
    user_id = _require_auth(request)

    conn = get_connection()
    cur = conn.execute(
        "SELECT id, anonymous_nickname, status, created_at FROM users WHERE id = ?",
        [user_id]
    )
    row = cur.fetchone()
    close_connection(conn)

    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    return wrap({
        "user_id": row["id"],
        "anonymous_nickname": row["anonymous_nickname"],
        "status": row["status"],
        "created_at": row["created_at"]
    })
