"""
Aftergift Backend - Reviews Router
Phase 2B | POST /api/review/mock
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.services import review_service

router = APIRouter(tags=["reviews"])


def wrap(data, code=200, message="success"):
    return JSONResponse(content={"code": code, "message": message, "data": data})


@router.post("/review/mock")
def mock_review_endpoint(req: dict):
    """
    Mock AI 审核接口（Phase 2B 使用本地规则引擎）。

    输入 short_story 和 full_story，返回风险等级、问题和建议。
    不上传任何数据到外部 API。

    Phase 2D 应替换为真实 AI 审核：
    - OpenAI Moderation API
    - 百度文本审核
    - 或其他合规 AI 服务
    """
    short_story = req.get("short_story", "")
    full_story = req.get("full_story", "")
    result = review_service.mock_review(short_story, full_story)
    return wrap(result)
