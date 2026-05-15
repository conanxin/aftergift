"""
Aftergift Backend - Reports Router
Phase 2D | POST /api/gifts/{id}/report
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.database import get_connection, close_connection
from app.auth import _require_auth

router = APIRouter(prefix="/gifts", tags=["reports"])


def wrap(data, code=200, message="success"):
    return JSONResponse(content={"code": code, "message": message, "data": data})


@router.post("/{gift_id}/report")
def create_report(gift_id: str, report: dict, request: Request):
    """
    举报礼物。

    Phase 2D：需要 Bearer token。
    无 token → 401
    """
    user_id = _require_auth(request)

    conn = get_connection()

    # Check gift exists
    cur = conn.execute("SELECT id FROM gifts WHERE id = ?", [gift_id])
    if not cur.fetchone():
        close_connection(conn)
        raise HTTPException(status_code=404, detail="礼物不存在")

    # Create report
    report_id = f"rep-{uuid.uuid4().hex[:8]}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # reason enum: API uses privacy_risk, DB uses privacy
    reason_raw = report.get("reason", "other")
    _reason_map = {
        "privacy_risk": "privacy",
        "privacy": "privacy",
        "attack": "attack",
        "fake": "fake",
        "other": "other"
    }
    db_reason = _reason_map.get(reason_raw, "other")
    detail = report.get("detail", "")

    conn.execute("""
        INSERT INTO reports (id, gift_id, reporter_user_id, reporter_ip_hash,
                            reason, detail, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        report_id, gift_id, user_id, "",
        db_reason, detail, "pending", now
    ))
    conn.commit()
    close_connection(conn)

    return wrap(
        {"report_id": report_id, "status": "pending"},
        code=201,
        message="感谢你的反馈，我们会尽快处理"
    )
