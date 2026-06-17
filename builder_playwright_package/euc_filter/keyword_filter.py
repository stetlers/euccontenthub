"""Stage 1: Keyword-based content relevance filter for AWS EUC posts."""

import logging

from euc_filter.config import (
    CONTEXT_DEPENDENT_KEYWORDS,
    EXCLUSION_LIST,
    POSITIVE_KEYWORDS,
    FilterResult,
)

logger = logging.getLogger(__name__)


def keyword_filter(url: str, title: str, content_snippet: str = "") -> FilterResult:
    """Stage 1 filter. Returns FilterResult with pass/fail and reason.

    Logic order:
    1. Check exclusion list — reject immediately if any exclusion term found.
    2. Check positive keywords — pass if a specific AWS EUC keyword matches.
    3. Check context-dependent keywords — require a qualifier to pass.
    4. If nothing matched — reject.

    Args:
        url: Post URL.
        title: Post title.
        content_snippet: Optional first 500 chars of content.

    Returns:
        FilterResult(passed=bool, reason=str)
    """
    text = f"{url} {title}".lower()

    # 1. Exclusion list check — rejects even if positive keywords present
    for term in EXCLUSION_LIST:
        if term in text:
            return FilterResult(
                passed=False,
                reason=f"excluded: {term}",
            )

    # 2. Positive keyword check — specific AWS EUC keywords
    for keyword in POSITIVE_KEYWORDS:
        if keyword in text:
            return FilterResult(
                passed=True,
                reason=f"matched positive keyword: {keyword}",
            )

    # 3. Context-dependent keyword check — need a qualifier to pass
    for keyword, qualifiers in CONTEXT_DEPENDENT_KEYWORDS.items():
        if keyword in text:
            for qualifier in qualifiers:
                if qualifier in text:
                    return FilterResult(
                        passed=True,
                        reason=f"matched context keyword '{keyword}' with qualifier '{qualifier}'",
                    )
            # Keyword present but no qualifier found
            return FilterResult(
                passed=False,
                reason=f"context keyword '{keyword}' without required qualifier",
            )

    # 4. No keyword matched at all
    return FilterResult(passed=False, reason="no matching keyword found")
