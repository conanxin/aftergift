"""
Aftergift Backend - OpenAI Moderation Provider (Skeleton)
Phase 2E-2 | Moderation Provider Abstraction

This is a SKELETON. It does NOT call the real OpenAI API in this phase.
Real implementation is planned for Phase 2E-4.

Env requirements (for future implementation):
    AFTERGIFT_MODERATION_PROVIDER=openai
    AFTERGIFT_ENABLE_REAL_AI_REVIEW=true
    OPENAI_API_KEY=sk-...          # Required for real calls
    OPENAI_MODERATION_MODEL=text-moderation-latest

Safety constraints:
- Never call OpenAI unless ENABLE_REAL_AI_REVIEW=true AND OPENAI_API_KEY is set
- Never log or store the raw OpenAI response containing story text
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

_PROVIDER_NAME = "openai"


class OpenAIModerationProvider:
    """
    OpenAI-powered content moderation provider.

    NOT ENABLED by default. Requires:
        AFTERGIFT_MODERATION_PROVIDER=openai
        AFTERGIFT_ENABLE_REAL_AI_REVIEW=true
        OPENAI_API_KEY=sk-...

    This skeleton always falls back to mock behavior.
    Real OpenAI API calls will be implemented in Phase 2E-4.
    """

    name: str = _PROVIDER_NAME

    def __init__(self):
        self._enabled = False  # Set to True only when fully configured

    def review(self, short_story: str, full_story: str = "") -> ModerationResult:
        """
        Review a gift story using OpenAI Moderation API.

        Currently a skeleton — returns a mock result without calling OpenAI.
        Real implementation in Phase 2E-4 will:
        1. Call OpenAI Moderation API with short_story + full_story
        2. Map the response to risk_level / issues / suggestions
        3. NOT store raw API response (privacy)
        4. Fall back to mock if API call fails
        """
        if not self._enabled:
            # Skeleton mode: delegate to mock provider
            from app.services.moderation.mock_provider import MockModerationProvider
            logger.info(
                "[OpenAI Moderation Provider] Real AI review not enabled. "
                "Falling back to MockModerationProvider."
            )
            mock = MockModerationProvider()
            return mock.review(short_story, full_story)

        # TODO (Phase 2E-4): Real OpenAI API implementation
        #
        # Implementation plan:
        #
        #   from openai import OpenAI
        #   client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        #
        #   response = client.moderations.create(
        #       input=short_story + "\n" + full_story,
        #       model=os.getenv("OPENAI_MODERATION_MODEL", "text-moderation-latest"),
        #   )
        #
        #   # Map OpenAI categories to ModerationResult
        #   # Categories: hate, harassment, violence, sexual, self-harm, etc.
        #   # Map to: identity risk, attack risk
        #
        #   # DO NOT log response.input — it contains user story text
        #
        #   return ModerationResult(...)
        #
        raise NotImplementedError(
            "OpenAI Moderation Provider real implementation is planned for Phase 2E-4. "
            "Set AFTERGIFT_MODERATION_PROVIDER=openai and AFTERGIFT_ENABLE_REAL_AI_REVIEW=true "
            "to enable (Phase 2E-4+ only)."
        )
