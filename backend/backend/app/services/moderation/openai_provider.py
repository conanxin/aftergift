"""
Aftergift Backend - OpenAI Moderation Provider (Sandbox)
Phase 2E-4 | OpenAI Provider Sandbox Implementation

Uses Python stdlib (urllib) to call OpenAI Moderation API.
Requires ALL of the following to make real API calls:
    AFTERGIFT_MODERATION_PROVIDER=openai
    AFTERGIFT_ENABLE_REAL_AI_REVIEW=true
    OPENAI_API_KEY=sk-... (non-empty)

Otherwise falls back to MockModerationProvider.

Safety constraints:
- NEVER send raw user story text to OpenAI — redact via Phase 2E-3 first
- NEVER log/store raw OpenAI response containing story text
- ALWAYS merge OpenAI result with Mock result (OpenAI doesn't cover identity exposure)
- ALL errors fallback to MockModerationProvider, never crash the API
"""

import json
import logging
import os
import socket
import ssl
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from app.services.moderation.base import (
    ModerationIssue,
    ModerationResult,
    ModerationSuggestion,
    ModerationProvider,
)
from app.services.moderation.mock_provider import MockModerationProvider
from app.services.anonymize_service import redact_sensitive_text

logger = logging.getLogger(__name__)

_PROVIDER_NAME = "openai"

# OpenAI Moderation API endpoint
# TODO: Update if OpenAI changes this endpoint
OPENAI_MODERATION_URL = "https://api.openai.com/v1/moderations"

# Categories that map to high_risk in Aftergift
_HIGH_RISK_CATEGORIES = {
    "hate", "hate/threatening",
    "harassment", "harassment/threatening",
    "violence", "violence/graphic",
    "self-harm", "self-harm/intent", "self-harm/instructions",
    "sexual", "sexual/minors",
}

# Categories that map to caution
_CAUTION_CATEGORIES = {
    "sexual",
}


def _is_enabled() -> bool:
    """Check if all conditions for real OpenAI calls are met."""
    try:
        from app.config import (
            MODERATION_PROVIDER,
            ENABLE_REAL_AI_REVIEW,
            OPENAI_API_KEY,
        )
        provider_ok = MODERATION_PROVIDER.strip().lower() == "openai"
        enable_ok = str(ENABLE_REAL_AI_REVIEW).strip().lower() in ("true", "1", "yes", "on")
        key_ok = bool(OPENAI_API_KEY and OPENAI_API_KEY.strip() and not OPENAI_API_KEY.strip().startswith("***"))
        return provider_ok and enable_ok and key_ok
    except Exception as e:
        logger.warning(f"[_is_enabled] Config check failed: {e}")
        return False


def _build_openai_payload(input_text: str, model: str) -> Dict[str, Any]:
    """Build the JSON payload for OpenAI Moderation API."""
    return {
        "input": input_text,
        "model": model,
    }


def _call_openai_moderation(input_text: str, api_key: str, model: str, timeout: float) -> Optional[Dict[str, Any]]:
    """
    Call OpenAI Moderation API using stdlib urllib.

    Returns parsed JSON dict on success, None on any error.
    Does NOT raise exceptions.
    """
    payload = _build_openai_payload(input_text, model)
    data = json.dumps(payload).encode("utf-8")

    req = Request(
        OPENAI_MODERATION_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        # Use custom timeout via socket (urllib default timeout)
        response = urlopen(req, timeout=timeout)
        raw_body = response.read().decode("utf-8")
        parsed = json.loads(raw_body)
        return parsed
    except HTTPError as e:
        status = e.code
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        if status == 401 or status == 403:
            logger.warning(f"[OpenAI Provider] Auth error {status}: {body[:200]}")
        elif status == 429:
            logger.warning(f"[OpenAI Provider] Rate limited (429): {body[:200]}")
        else:
            logger.warning(f"[OpenAI Provider] HTTP error {status}: {body[:200]}")
        return None
    except URLError as e:
        logger.warning(f"[OpenAI Provider] Network error: {e}")
        return None
    except socket.timeout:
        logger.warning("[OpenAI Provider] Socket timeout")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"[OpenAI Provider] JSON parse error: {e}")
        return None
    except Exception as e:
        logger.warning(f"[OpenAI Provider] Unexpected error: {e}")
        return None


def _map_openai_result(openai_response: Dict[str, Any]) -> ModerationResult:
    """
    Map OpenAI Moderation API response to Aftergift ModerationResult.

    OpenAI response format:
    {
        "id": "modr-...",
        "model": "omni-moderation-latest",
        "results": [
            {
                "flagged": true/false,
                "categories": {
                    "hate": false,
                    "harassment": true,
                    ...
                },
                "category_scores": {
                    "hate": 0.01,
                    "harassment": 0.95,
                    ...
                }
            }
        ]
    }
    """
    results = openai_response.get("results", [])
    if not results:
        # Empty response — treat as safe but with caution
        return ModerationResult(
            risk_level="caution",
            issues=[],
            suggestions=[],
            quality_notes={"openai_empty_response": True},
            provider=_PROVIDER_NAME,
            overall_score=0.5,
        )

    result = results[0]
    flagged = result.get("flagged", False)
    categories = result.get("categories", {})
    category_scores = result.get("category_scores", {})

    issues: List[ModerationIssue] = []
    suggestions: List[ModerationSuggestion] = []

    # Determine risk level from categories
    max_high_risk_score = 0.0
    max_caution_score = 0.0

    for cat, is_flagged in categories.items():
        score = category_scores.get(cat, 0.0)
        if cat in _HIGH_RISK_CATEGORIES and is_flagged:
            max_high_risk_score = max(max_high_risk_score, score)
            issues.append(ModerationIssue(
                category="attack",
                subtype=f"openai_{cat}",
                original=f"OpenAI flagged: {cat}",
                reason=f"OpenAI moderation detected '{cat}' (score: {score:.3f})",
                severity="high",
            ))
            suggestions.append(ModerationSuggestion(
                type=f"OpenAI: {cat}",
                original=f"分类: {cat}",
                reason=f"OpenAI moderation API 标记此内容含有 '{cat}' 风险",
                suggestion="请修改内容，避免攻击性、仇恨或暴力表达",
            ))
        elif cat in _CAUTION_CATEGORIES and is_flagged:
            max_caution_score = max(max_caution_score, score)
            issues.append(ModerationIssue(
                category="attack",
                subtype=f"openai_{cat}",
                original=f"OpenAI flagged: {cat}",
                reason=f"OpenAI moderation detected '{cat}' (score: {score:.3f})",
                severity="medium",
            ))

    if max_high_risk_score > 0:
        risk_level = "high_risk"
        overall_score = 0.2
    elif max_caution_score > 0 or flagged:
        risk_level = "caution"
        overall_score = 0.5
    else:
        risk_level = "safe"
        overall_score = 0.85

    # Build quality notes from scores
    quality_notes = {
        "openai_flagged": flagged,
        "openai_max_score": max(
            category_scores.values(), default=0.0
        ),
        "openai_categories_flagged": [
            cat for cat, val in categories.items() if val
        ],
    }

    return ModerationResult(
        risk_level=risk_level,
        issues=issues,
        suggestions=suggestions,
        quality_notes=quality_notes,
        provider=_PROVIDER_NAME,
        overall_score=round(overall_score, 2),
        # Do NOT store full raw response — only summary
        raw={"flagged": flagged, "model": openai_response.get("model", "unknown")},
    )


def _merge_results(openai_result: ModerationResult, mock_result: ModerationResult) -> ModerationResult:
    """
    Merge OpenAI and Mock moderation results.

    Strategy:
    - risk_level: take the HIGHER of the two (safe < caution < high_risk)
    - issues: combine both lists
    - suggestions: combine both lists
    - quality_notes: merge dicts (OpenAI + Mock)
    - overall_score: take the LOWER (more conservative)
    - provider: "openai+mock" to indicate merged
    """
    risk_priority = {"safe": 0, "caution": 1, "high_risk": 2}

    openai_priority = risk_priority.get(openai_result.risk_level, 0)
    mock_priority = risk_priority.get(mock_result.risk_level, 0)

    merged_risk = openai_result.risk_level if openai_priority >= mock_priority else mock_result.risk_level
    merged_score = min(openai_result.overall_score, mock_result.overall_score)

    merged_issues = openai_result.issues + mock_result.issues
    merged_suggestions = openai_result.suggestions + mock_result.suggestions

    merged_quality = dict(mock_result.quality_notes)
    merged_quality.update(openai_result.quality_notes)
    merged_quality["local_rules_applied"] = True

    return ModerationResult(
        risk_level=merged_risk,
        issues=merged_issues,
        suggestions=merged_suggestions,
        quality_notes=merged_quality,
        provider="openai+mock",
        overall_score=round(merged_score, 2),
        raw={
            "openai_flagged": openai_result.quality_notes.get("openai_flagged", False),
            "local_rules_applied": True,
        },
    )


class OpenAIModerationProvider:
    """
    OpenAI-powered content moderation provider.

    NOT ENABLED by default. Requires:
        AFTERGIFT_MODERATION_PROVIDER=openai
        AFTERGIFT_ENABLE_REAL_AI_REVIEW=true
        OPENAI_API_KEY=sk-...

    When enabled:
    1. Redacts input text via Phase 2E-3 redact_sensitive_text()
    2. Calls OpenAI Moderation API via stdlib urllib
    3. Maps OpenAI categories to Aftergift risk_level
    4. Merges with MockModerationProvider result (OpenAI misses identity exposure)
    5. On ANY error, falls back to MockModerationProvider
    """

    name: str = _PROVIDER_NAME

    def __init__(self):
        self._mock = MockModerationProvider()

    def review(self, short_story: str, full_story: str = "") -> ModerationResult:
        """
        Review a gift story using OpenAI Moderation API + Mock rules.

        Args:
            short_story: One-line story summary
            full_story: Full story text (optional)

        Returns:
            ModerationResult (merged OpenAI + Mock, or Mock-only on fallback)
        """
        # Step 1: Always run mock review (for identity/attack detection)
        mock_result = self._mock.review(short_story, full_story)

        # Step 2: Check if real OpenAI is enabled
        if not _is_enabled():
            logger.info(
                "[OpenAI Provider] Real AI review not enabled. "
                "Returning mock result."
            )
            return mock_result

        # Step 3: Redact input before sending to OpenAI
        redacted_short = redact_sensitive_text(short_story)
        redacted_full = redact_sensitive_text(full_story)
        input_text = f"{redacted_short}\n{redacted_full}".strip()

        # Step 4: Get config
        try:
            from app.config import (
                OPENAI_API_KEY,
                OPENAI_MODERATION_MODEL,
                OPENAI_TIMEOUT_SECONDS,
            )
            api_key = OPENAI_API_KEY.strip()
            model = OPENAI_MODERATION_MODEL
            timeout = OPENAI_TIMEOUT_SECONDS
        except Exception as e:
            logger.warning(f"[OpenAI Provider] Config read error: {e}")
            return mock_result

        # Step 5: Call OpenAI API
        openai_response = _call_openai_moderation(input_text, api_key, model, timeout)

        if openai_response is None:
            logger.warning("[OpenAI Provider] API call failed, falling back to mock")
            # Add a fallback issue note
            fallback_issue = ModerationIssue(
                category="provider_error",
                subtype="openai_fallback",
                original="OpenAI API unavailable",
                reason="OpenAI Moderation API 调用失败，已回退到本地规则审核",
                severity="low",
            )
            mock_result.issues.append(fallback_issue)
            mock_result.quality_notes["openai_fallback"] = True
            return mock_result

        # Step 6: Map OpenAI response
        try:
            openai_result = _map_openai_result(openai_response)
        except Exception as e:
            logger.warning(f"[OpenAI Provider] Result mapping error: {e}")
            return mock_result

        # Step 7: Merge with mock result
        merged = _merge_results(openai_result, mock_result)
        logger.info(
            f"[OpenAI Provider] Merged result: risk={merged.risk_level}, "
            f"issues={len(merged.issues)}, provider={merged.provider}"
        )
        return merged
