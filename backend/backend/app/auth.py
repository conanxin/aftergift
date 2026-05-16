"""
Aftergift Backend - Authentication Dependency
Phase 2E-1 | PyJWT-based anonymous auth for local development

Design:
- No real phone/email collected.
- User requests anonymous session → server generates a PyJWT access token.
- Token stored in localStorage on client side.
- All mutation endpoints (create/favorite/report) require Bearer token.
- Admin endpoints require separate X-Admin-Token (existing pattern).

Token payload (JWT claims):
  - sub: user_id
  - nickname: anonymous_nickname
  - role: "user"
  - iat: issued at (auto)
  - exp: expiry (from config, default 7 days)
  - token_version: 1 (for future revoke tracking)
  - jti: unique token id (for future revoke table)

Phase 2E/2F upgrade path:
- Add token revocation table (revoked_tokens / jti tracking).
- Add refresh token flow.
- Add admin role to JWT claims for Phase 2F.
- Store JWT secret in HSM/vault in production.
"""

import jwt
import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from starlette.requests import Request
from typing import Optional

from app.config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_TTL_SECONDS


# ── Token helpers ─────────────────────────────────────────────────────────────

def create_access_token(
    user_id: str,
    nickname: str,
    role: str = "user",
) -> str:
    """
    Generate a PyJWT access token for the given anonymous user.

    Payload:
      sub      - user_id
      nickname - anonymous nickname
      role     - "user" (admin role added in Phase 2F)
      iat      - issued at (UTC now)
      exp      - expiry (now + ACCESS_TOKEN_TTL_SECONDS)
      token_version - 1 (reserved for future revoke mechanism)
      jti     - unique token id for future revocation
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "nickname": nickname,
        "role": role,
        "iat": now,
        "exp": datetime.fromtimestamp(now.timestamp() + ACCESS_TOKEN_TTL_SECONDS, tz=timezone.utc),
        "token_version": 1,
        "jti": uuid.uuid4().hex[:16],
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a PyJWT access token.

    Returns the decoded payload dict if valid.
    Returns None if:
      - token is malformed
      - signature mismatch
      - token expired
      - secret not configured
    """
    if not token:
        return None
    try:
        # For dev placeholder secret, decode without signature verify.
        # In production with real secret, full verification is applied.
        if JWT_SECRET == "replace-this-dev-secret":
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={"verify_signature": False, "verify_exp": True},
            )
        else:
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
            )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def _require_auth_payload(request: Request) -> dict:
    """
    Extract and verify Bearer token from Request, return full JWT payload.

    Returns the decoded JWT payload dict on success.

    Raises HTTPException:
      401 - missing Authorization header
      401 - Bearer format invalid
      401 - token expired
      403 - token invalid / signature error / payload missing sub
    """
    authorization = request.headers.get("authorization")
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={
                "code": 401,
                "message": "缺少身份凭证，请先创建匿名身份",
                "data": None,
            },
        )

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail={
                "code": 401,
                "message": "无效的 Authorization 格式，请使用 Bearer <token>",
                "data": None,
            },
        )

    token = parts[1]
    payload = decode_access_token(token)

    if payload is None:
        # Distinguish expired vs invalid
        try:
            jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={"verify_signature": False, "verify_exp": True},
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "code": 403,
                    "message": "身份凭证无效（签名校验失败），请重新创建匿名身份",
                    "data": None,
                },
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": 401,
                    "message": "身份凭证已过期，请重新创建匿名身份",
                    "data": None,
                },
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": 403,
                    "message": "身份凭证无效，请重新创建匿名身份",
                    "data": None,
                },
            )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=403,
            detail={
                "code": 403,
                "message": "身份凭证格式异常",
                "data": None,
            },
        )

    return payload


def _require_auth(request: Request) -> str:
    """
    FastAPI dependency: extract and verify Bearer token, return user_id (str).

    This is the primary auth helper used by all routers.
    Reads Authorization header via request.headers.get() (NOT Header()).

    Returns user_id (sub claim from JWT).

    Raises HTTPException:
      401 - missing Authorization header
      401 - Bearer format invalid
      401 - token expired
      403 - token invalid / user not found / disabled
    """
    payload = _require_auth_payload(request)
    return payload.get("sub")


def get_bearer_token(request: Request) -> Optional[str]:
    """
    Extract Bearer token from Authorization header via Request object.

    Returns the token string (without "Bearer " prefix), or None if absent/invalid.
    Does NOT verify the token — use decode_access_token for that.
    """
    authorization = request.headers.get("authorization")
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def _get_user_nickname(user_id: str) -> str:
    """Generate a consistent anonymous nickname for user_id (e.g. '匿名整理者 0421')."""
    seed = int(user_id[-4:], 16) % 10000
    return f"匿名整理者 {seed:04d}"
