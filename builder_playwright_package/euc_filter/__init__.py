"""EUC Content Relevance Filter — shared module for all crawlers."""

import logging

from euc_filter.ai_validator import ai_validate
from euc_filter.config import (
    AI_PROMPT_TEMPLATE,
    BACKOFF_MULTIPLIER,
    BASE_DELAY_SECONDS,
    BEDROCK_TIMEOUT_SECONDS,
    CONTEXT_DEPENDENT_KEYWORDS,
    DEFAULT_RELEVANCE_THRESHOLD,
    EXCLUSION_LIST,
    MAX_DELAY_SECONDS,
    MAX_RETRIES,
    POSITIVE_KEYWORDS,
    THRESHOLD_ENV_VAR,
    FilterResult,
    PostFilterResult,
    ValidationResult,
    get_relevance_threshold,
)
from euc_filter.keyword_filter import keyword_filter

logger = logging.getLogger(__name__)


def filter_post(url: str, title: str, content_snippet: str = "") -> PostFilterResult:
    """Run keyword-only filtering at crawl time.

    AI validation is now handled by summary_lambda.py after summary generation.

    Args:
        url: Post URL.
        title: Post title.
        content_snippet: Optional first ~500 characters of post content.

    Returns:
        PostFilterResult with accepted flag, stage="keyword", and reason.
    """
    kf_result = keyword_filter(url, title, content_snippet)
    return PostFilterResult(
        accepted=kf_result.passed,
        stage="keyword",
        relevance_score=None,
        reason=kf_result.reason,
    )


__all__ = [
    "POSITIVE_KEYWORDS",
    "EXCLUSION_LIST",
    "CONTEXT_DEPENDENT_KEYWORDS",
    "DEFAULT_RELEVANCE_THRESHOLD",
    "THRESHOLD_ENV_VAR",
    "MAX_RETRIES",
    "BASE_DELAY_SECONDS",
    "BACKOFF_MULTIPLIER",
    "MAX_DELAY_SECONDS",
    "BEDROCK_TIMEOUT_SECONDS",
    "AI_PROMPT_TEMPLATE",
    "FilterResult",
    "ValidationResult",
    "PostFilterResult",
    "get_relevance_threshold",
    "keyword_filter",
    "ai_validate",
    "filter_post",
]
