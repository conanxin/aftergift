"""
Aftergift Backend - Moderation Provider Base
Phase 2E-2 | Moderation Provider Abstraction

Defines:
- ModerationIssue: a detected risk item
- ModerationSuggestion: a rewrite suggestion
- ModerationResult: the final review result container
- ModerationProvider: abstract protocol (interface)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class ModerationIssue:
    """A detected risk or problem in the story."""
    category: str           # e.g. "identity", "attack", "identifiable"
    subtype: str            # e.g. "phone", "revenge_words", "name_pattern"
    original: str           # what was matched, e.g. "手机号码"
    reason: str            # human-readable explanation
    severity: str = "high" # "high" | "medium" | "low" — derived from category

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.category,
            "subtype": self.subtype,
            "original": self.original,
            "reason": self.reason,
        }


@dataclass
class ModerationSuggestion:
    """A rewrite suggestion for a detected issue."""
    type: str                          # e.g. "手机号码", "报复性词汇"
    original: str                      # what was matched
    reason: str                        # why this is a concern
    suggestion: str                    # recommended replacement
    replacement: Optional[str] = None  # optional pre-filled replacement text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "original": self.original,
            "reason": self.reason,
            "suggestion": self.suggestion,
        }


@dataclass
class ModerationResult:
    """
    The complete moderation review result.

    Fields:
        risk_level:   "safe" | "caution" | "high_risk"
        issues:       List of detected risk items
        suggestions:  List of rewrite suggestions
        quality_notes: Dict of quality check results
        provider:     Which provider produced this result ("mock", "openai", "baidu")
        overall_score: Float 0.0-1.0 (higher = safer/better quality)
        raw:          Optional raw response from external API (for debugging only)
    """
    risk_level: str
    issues: List[ModerationIssue]
    suggestions: List[ModerationSuggestion]
    quality_notes: Dict[str, Any]
    provider: str
    overall_score: float = 0.5
    raw: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "issues": [i.to_dict() for i in self.issues],
            "suggestions": [s.to_dict() for s in self.suggestions],
            "quality_notes": self.quality_notes,
            "overall_score": self.overall_score,
            "provider": self.provider,
        }


@runtime_checkable
class ModerationProvider(Protocol):
    """
    Abstract protocol for all moderation providers.

    Implement this to add a new provider:
        class MyProvider(ModerationProvider):
            name: str = "my_provider"

            def review(self, short_story: str, full_story: str) -> ModerationResult:
                ...
    """

    name: str

    def review(self, short_story: str, full_story: str) -> ModerationResult:
        """
        Review a gift story for safety and quality.

        Args:
            short_story: The one-line story summary (required)
            full_story:  The complete story text (optional)

        Returns:
            ModerationResult with risk_level, issues, suggestions, quality_notes, provider
        """
        ...
