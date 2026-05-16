"""
Aftergift Backend - Review Service
Phase 2E-2 | Wraps ModerationProvider, keeps backward compatibility

Public API (unchanged):
- review_service.mock_review(short_story, full_story) -> dict
- review_service.get_publish_status(review_result) -> str

New (Phase 2E-2):
- review_service.review_story(short_story, full_story) -> dict
  Uses the active ModerationProvider (via factory), returns result with `provider` field.
"""

from app.services.moderation.factory import get_moderation_provider


def review_story(short_story: str, full_story: str = "") -> dict:
    """
    Review a gift story using the active ModerationProvider.

    This is the preferred entry point (Phase 2E-2+).
    Returns the same structure as mock_review() plus a `provider` field.

    Args:
        short_story: One-line story summary
        full_story:  Full story text (optional)

    Returns:
        dict with risk_level, issues, suggestions, quality_notes, overall_score, provider
    """
    provider = get_moderation_provider()
    result = provider.review(short_story, full_story)
    return result.to_dict()


def mock_review(short_story: str, full_story: str = "") -> dict:
    """
    Backward-compatible wrapper.

    Calls the active ModerationProvider (defaults to MockModerationProvider).
    Returns the same dict structure as before Phase 2E-2.
    Used directly by routers/gifts.py for backward compatibility.
    """
    return review_story(short_story, full_story)


def get_publish_status(review_result: dict) -> str:
    """
    Map review risk_level to publish status.

    Args:
        review_result: dict returned by mock_review() or review_story()

    Returns:
        "published" | "needs_edit" | "pending_review"
    """
    risk = review_result.get("risk_level", "safe")
    if risk == "safe":
        return "published"
    elif risk == "caution":
        return "needs_edit"
    else:  # high_risk
        return "pending_review"
