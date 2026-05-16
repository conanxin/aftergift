"""
Aftergift Backend - Moderation Provider Package
Phase 2E-2 | Moderation Provider Abstraction

Architecture:
    factory.py       → get_moderation_provider() → ModerationProvider
    base.py          → ModerationResult, ModerationIssue, ModerationSuggestion dataclasses + Protocol
    mock_provider.py → MockModerationProvider (current rule-based logic)
    openai_provider.py → OpenAIModerationProvider (skeleton, not enabled by default)
    baidu_provider.py  → BaiduModerationProvider (skeleton, not enabled by default)
"""

from app.services.moderation.base import (
    ModerationResult,
    ModerationIssue,
    ModerationSuggestion,
    ModerationProvider,
)
from app.services.moderation.factory import get_moderation_provider

__all__ = [
    "ModerationResult",
    "ModerationIssue",
    "ModerationSuggestion",
    "ModerationProvider",
    "get_moderation_provider",
]
