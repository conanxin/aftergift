"""
Aftergift Backend - Baidu Content Review Provider (Skeleton)
Phase 2E-2 | Moderation Provider Abstraction

This is a SKELETON. It does NOT call the real Baidu API in this phase.
Real implementation is planned for a future phase.

Env requirements (for future implementation):
    AFTERGIFT_MODERATION_PROVIDER=baidu
    BAIDU_CONTENT_REVIEW_API_KEY=...    # Baidu API Key
    BAIDU_CONTENT_REVIEW_SECRET_KEY=...  # Baidu Secret Key

Safety constraints:
- Never call Baidu unless BAIDU_CONTENT_REVIEW_API_KEY is set
- Never log or store the raw Baidu response containing story text
- Always return ModerationResult compatible with mock_provider structure
"""

import logging
from typing import Any, Dict, List, Optional

from app.services.moderation.base import (
    ModerationIssue,
    ModerationResult,
    ModerationSuggestion,
    ModerationProvider,
)

logger = logging.getLogger(__name__)

_PROVIDER_NAME = "baidu"


class BaiduModerationProvider:
    """
    Baidu Content Review API-powered moderation provider.

    NOT ENABLED by default. Requires:
        AFTERGIFT_MODERATION_PROVIDER=baidu
        BAIDU_CONTENT_REVIEW_API_KEY=...
        BAIDU_CONTENT_REVIEW_SECRET_KEY=...

    This skeleton always falls back to mock behavior.
    Real Baidu API calls will be implemented in a future phase.
    """

    name: str = _PROVIDER_NAME

    def __init__(self):
        self._enabled = False  # Set to True only when fully configured

    def review(self, short_story: str, full_story: str = "") -> ModerationResult:
        """
        Review a gift story using Baidu Content Review API.

        Currently a skeleton — returns a mock result without calling Baidu.
        Real implementation in a future phase will:
        1. Call Baidu Content Review API with short_story + full_story
        2. Map the response to risk_level / issues / suggestions
        3. NOT store raw API response (privacy)
        4. Fall back to mock if API call fails
        """
        if not self._enabled:
            from app.services.moderation.mock_provider import MockModerationProvider
            logger.info(
                "[Baidu Moderation Provider] Real AI review not enabled. "
                "Falling back to MockModerationProvider."
            )
            mock = MockModerationProvider()
            return mock.review(short_story, full_story)

        # TODO (future phase): Real Baidu API implementation
        #
        # Baidu Content Review API integration points:
        # - Text moderation: POST https://aip.baidubce.com/rpc/2.0/ai_custom/v1/text_censor_v2
        # - Requires access_token from https://aip.baidubce.com/oauth/2.0/token
        #
        # DO NOT log response — it contains user story text
        #
        raise NotImplementedError(
            "Baidu Moderation Provider is not yet implemented. "
            "Set AFTERGIFT_MODERATION_PROVIDER=baidu and configure BAIDU_API_KEY "
            "to enable (future phase only)."
        )
