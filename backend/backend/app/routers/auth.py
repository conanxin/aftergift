"""
Aftergift Backend - Auth Router
Phase 2E-1 | POST /api/auth/anonymous, GET /api/auth/me

No real identity collected. Purely for binding mutations to a session.
Token: PyJWT HS256 (Phase 2E upgrade from HMAC).
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.database import get_connection, close_connection
from app.auth import (
    create_access_token,
    decode_access_token,
    get_bearer_token,
    _require_auth,
    _require_auth_payload,
    _get_user_nickname,
)
from app.config import ACCESS_TOKEN_TTL_SECONDS

router = APIRouter(prefix="/auth", tags=["auth"])


def wrap(data, code=200, message="success"):
    return JSONResponse(
        content={"code": code, "message": message, "data": data},
        status_code=code,
    )


@router.post("/anonymous")
def create_anonymous_user():
    """
    创建或返回一个匿名用户身份。

    Phase 2E-1 实现：
    - 不要求手机号、邮箱。
    - 每次调用生成一个新的匿名 user_id。
    - 签发 PyJWT access_token（HS256，有效期 7 天）。
    - 返回 user_id + access_token + expires_in。
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

    # Generate PyJWT token
    access_token = create_access_token(user_id, anonymous_nickname, role="user")

    return wrap({
        "user_id": user_id,
        "anonymous_nickname": anonymous_nickname,
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_TTL_SECONDS,
    }, code=201, message="匿名身份创建成功")


@router.get("/me")
def get_current_user(request: Request):
    """
    返回当前登录用户信息。

    读取 Authorization: Bearer <token>
    - 无 token → 401
    - token 无效/过期 → 401 / 403
    - 有效 → 返回 user_id + anonymous_nickname + role + token_version
    """
    # Import here to avoid circular import
    from app.auth import _require_auth_payload
    payload = _require_auth_payload(request)

    user_id = payload.get("sub")
    conn = get_connection()
    cur = conn.execute(
        "SELECT id, anonymous_nickname, status, created_at FROM users WHERE id = ?",
        [user_id]
    )
    row = cur.fetchone()
    close_connection(conn)

    if not row:
        raise HTTPException(status_code=403, detail="用户不存在或已禁用")

    return wrap({
        "user_id": row["id"],
        "anonymous_nickname": row["anonymous_nickname"],
        "role": payload.get("role", "user"),
        "token_version": payload.get("token_version", 1),
        "status": row["status"],
        "created_at": row["created_at"],
    })
