"""
Aftergift Backend - Moderation Provider Factory
Phase 2E-2 | Moderation Provider Abstraction

Factory pattern: selects the active moderation provider based on config.

Selection rules:
1. Default = mock (always safe)
2. provider=openai + ENABLE_REAL_AI_REVIEW=false → fallback mock
3. provider=openai + no OPENAI_API_KEY → fallback mock
4. provider=baidu + no BAIDU_API_KEY → fallback mock
5. provider=unknown → fallback mock
6. Never raises an exception that prevents server startup
"""

import logging
import os
from typing import Optional

from app.config import (
    MODERATION_PROVIDER,
    ENABLE_REAL_AI_REVIEW,
    OPENAI_API_KEY,
    BAIDU_CONTENT_REVIEW_API_KEY,
)

from app.services.moderation.base import ModerationProvider
from app.services.moderation.mock_provider import MockModerationProvider
from app.services.moderation.openai_provider import OpenAIModerationProvider
from app.services.moderation.baidu_provider import BaiduModerationProvider

logger = logging.getLogger(__name__)

# Singleton instance
_cached_provider: Optional[ModerationProvider] = None


def _parse_bool(value) -> bool:
    """Parse boolean from string env var (true/false/1/0/yes/no) or Python bool."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def get_moderation_provider() -> ModerationProvider:
    """
    Return the active ModerationProvider based on config.

    Uses a cached singleton to avoid repeated provider instantiation.
    Cache is based on MODERATION_PROVIDER + ENABLE_REAL_AI_REVIEW config values.

    Fallback chain:
        openai (without key/review flag) → mock
        baidu (without key) → mock
        unknown → mock
    """
    global _cached_provider

    provider_name = MODERATION_PROVIDER.strip().lower() if MODERATION_PROVIDER else "mock"
    real_ai = _parse_bool(ENABLE_REAL_AI_REVIEW)

    cache_key = f"{provider_name}:{real_ai}"

    if _cached_provider is not None:
        # Verify cache hasn't been invalidated by config change
        return _cached_provider

    selected: ModerationProvider

    if provider_name == "openai":
        if not real_ai:
            logger.info(
                "[ModerationFactory] AFTERGIFT_MODERATION_PROVIDER=openai but "
                "AFTERGIFT_ENABLE_REAL_AI_REVIEW=false. Falling back to mock."
            )
            selected = MockModerationProvider()
        elif not OPENAI_API_KEY:
            logger.info(
                "[ModerationFactory] AFTERGIFT_MODERATION_PROVIDER=openai but "
                "OPENAI_API_KEY not set. Falling back to mock."
            )
            selected = MockModerationProvider()
        else:
            # Phase 2E-4: Enable real OpenAI provider when credentials configured
            logger.info(
                "[ModerationFactory] OpenAI provider selected with real AI enabled."
            )
            selected = OpenAIModerationProvider()

    elif provider_name == "baidu":
        if not BAIDU_CONTENT_REVIEW_API_KEY:
            logger.info(
                "[ModerationFactory] AFTERGIFT_MODERATION_PROVIDER=baidu but "
                "BAIDU_CONTENT_REVIEW_API_KEY not set. Falling back to mock."
            )
            selected = MockModerationProvider()
        else:
            # TODO (future phase): Enable real Baidu provider when credentials configured
            logger.info(
                "[ModerationFactory] Baidu provider selected but not yet "
                "implemented. Falling back to mock."
            )
            selected = MockModerationProvider()

    elif provider_name == "mock":
        selected = MockModerationProvider()

    else:
        logger.warning(
            f"[ModerationFactory] Unknown AFTERGIFT_MODERATION_PROVIDER='{provider_name}'. "
            "Falling back to mock."
        )
        selected = MockModerationProvider()

    _cached_provider = selected
    logger.info(f"[ModerationFactory] Active provider: {selected.name}")
    return selected


def reset_provider_cache():
    """
    Reset the provider cache.

    Useful for testing or when config changes at runtime.
    """
    global _cached_provider
    _cached_provider = None
