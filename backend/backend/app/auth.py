"""
Aftergift Backend - Authentication Dependency
Phase 2D | Minimal anonymous auth for local development

Design:
- No real phone/email collected.
- User requests anonymous session → server generates token.
- Token stored in localStorage on client side.
- All mutation endpoints (create/favorite/report) require Bearer token.
- Admin endpoints require separate X-Admin-Token (existing pattern).

Phase 2E/2F upgrade path:
- Replace secret-token auth with real JWT (PyJWT).
- Add real phone/email verification via SMS/email OTP.
- Add rate limiting per token.
- Add IP hash anti-abuse.
"""

import re
import secrets
import hmac
import hashlib
import base64
import json
from fastapi import HTTPException
from starlette.requests import Request
from typing import Optional

# ── Token format ──────────────────────────────────────────────────────────────
#
# Phase 2D dev token (NOT a real JWT):
#   "af2d_" + base64url(user_id + ":" +hmac_sha256(user_id, server_secret))
#
# This is a simple HMAC token — easy to verify, no external libs needed.
# NOT cryptographically secure for production (use PyJWT in Phase 2E).
#
# ─────────────────────────────────────────────────────────────────────────────

_TOKEN_PREFIX = "af2d_"
_HMAC_SECRET = b"aftergift-phase2d-dev-secret-do-not-use-in-prod"


def _make_token(user_id: str) -> str:
    """Generate a dev token for user_id."""
    mac = hmac.new(_HMAC_SECRET, user_id.encode(), hashlib.sha256).digest()
    token_str = f"{user_id}:{base64.b64encode(mac).decode()}"
    return _TOKEN_PREFIX + base64.urlsafe_b64encode(token_str.encode()).decode()


def _verify_token(token: str) -> Optional[str]:
    """
    Verify a dev token and return the user_id if valid, else None.
    """
    if not token or not token.startswith(_TOKEN_PREFIX):
        return None
    try:
        encoded = token[len(_TOKEN_PREFIX):]
        decoded = base64.urlsafe_b64decode(encoded.encode()).decode()
        user_id, expected_mac_b64 = decoded.split(":", 1)
        expected_mac = base64.b64decode(expected_mac_b64)
        actual_mac = hmac.new(_HMAC_SECRET, user_id.encode(), hashlib.sha256).digest()
        if hmac.compare_digest(actual_mac, expected_mac):
            return user_id
    except Exception:
        pass
    return None


def _require_auth(request: Request) -> str:
    """
    Extract and verify Bearer token from Authorization header via Request.

    Raises HTTPException 401 if missing or invalid.
    """
    authorization = request.headers.get("authorization")
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={
                "code": 401,
                "message": "缺少身份凭证，请先创建匿名身份",
                "data": None
            }
        )

    # Parse "Bearer <token>"
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail={
                "code": 401,
                "message": "无效的 Authorization 格式，请使用 Bearer <token>",
                "data": None
            }
        )

    user_id = _verify_token(parts[1])
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": 401,
                "message": "身份凭证无效或已过期，请重新创建匿名身份",
                "data": None
            }
        )

    return user_id


def _get_user_nickname(user_id: str) -> str:
    """Generate a consistent anonymous nickname for user_id (e.g. '匿名整理者 0421')."""
    # Use last 4 chars of user_id as seed for number
    seed = int(user_id[-4:], 16) % 10000
    return f"匿名整理者 {seed:04d}"
