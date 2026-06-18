"""Shared configuration for the EUC content relevance filter."""

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Positive keywords — specific to AWS EUC services (Requirement 1.1)
# ---------------------------------------------------------------------------
POSITIVE_KEYWORDS: list[str] = [
    "amazon workspaces",
    "workspaces web",
    "workspaces thin client",
    "appstream",
    "appstream 2.0",
    "end user computing",
    "euc",
    "workspaces pool",
    "workspaces personal",
    "workspaces core",
    "daas",
    "desktop as a service",
    "virtual desktop infrastructure",
    "vdi",
    "workspaces graphics",
    "workspaces streaming protocol",
    "wsp",
]

# ---------------------------------------------------------------------------
# Exclusion list — rejects post even if positive keywords match (Req 1.2, 1.3)
# ---------------------------------------------------------------------------
EXCLUSION_LIST: list[str] = [
    "end user messaging",
    "brio",
    "aideas jarvis",
    "jarvis desktop assistant",
    "kiro clean desktop",
    "desktop publishing",
    "desktop wallpaper",
    "desktop icon",
    "desktop shortcut",
    "desktop background",
    "desktop theme",
    "desktop widget",
]

# ---------------------------------------------------------------------------
# Context-dependent keywords — require a qualifier to count (Req 1.4-1.6)
# ---------------------------------------------------------------------------
CONTEXT_DEPENDENT_KEYWORDS: dict[str, list[str]] = {
    "desktop": [
        "workspaces",
        "appstream",
        "aws",
        "amazon",
        "virtual desktop infrastructure",
        "vdi",
    ],
    "end user": ["computing", "euc", "workspaces", "appstream"],
    "graphics": ["workspaces", "appstream"],
}

# ---------------------------------------------------------------------------
# Threshold configuration (Req 4.1, 4.2, 4.3)
# ---------------------------------------------------------------------------
DEFAULT_RELEVANCE_THRESHOLD: float = 0.7
THRESHOLD_ENV_VAR: str = "EUC_RELEVANCE_THRESHOLD"

# ---------------------------------------------------------------------------
# Retry / backoff constants for Bedrock calls
# ---------------------------------------------------------------------------
MAX_RETRIES: int = 5
BASE_DELAY_SECONDS: float = 2.0
BACKOFF_MULTIPLIER: float = 2.0
MAX_DELAY_SECONDS: float = 30.0
BEDROCK_TIMEOUT_SECONDS: float = 10.0

# ---------------------------------------------------------------------------
# AI prompt template (Req 3.6)
# ---------------------------------------------------------------------------
AI_PROMPT_TEMPLATE: str = """\
You are evaluating whether a blog post is PRIMARILY about Amazon WorkSpaces or AWS End User Computing (EUC) services.

AWS EUC services include:
- Amazon WorkSpaces (Personal, Pools, Core)
- Amazon WorkSpaces Web
- Amazon WorkSpaces Thin Client
- Amazon AppStream 2.0
- WorkSpaces Streaming Protocol (WSP)
- WorkSpaces Graphics bundles

SCORING RULES:
- Score 0.9-1.0: The post is primarily about configuring, deploying, managing, or using an EUC service. The EUC service is the MAIN TOPIC.
- Score 0.5-0.8: The post mentions an EUC service but the main topic is something else (e.g., a scientific workflow, a third-party tool, or a general AWS architecture that happens to use WorkSpaces).
- Score 0.1-0.4: The post only tangentially references EUC services, or uses EUC-related terms in a non-EUC context.
- Score 0.0: No connection to EUC services at all.

IMPORTANT: A post that uses WorkSpaces or AppStream as infrastructure for a NON-EUC purpose (e.g., scientific computing, video editing, game development) should score 0.5-0.6, NOT 0.9+. The post must be ABOUT the EUC service itself to score high.

A post is NOT EUC-relevant if it:
- Mentions "desktop" in a non-AWS context (desktop publishing, desktop wallpaper, desktop assistants)
- Discusses "end user" in a messaging or general IT context
- Is primarily about a different domain (neuroscience, gaming, etc.) that happens to run on WorkSpaces

Post Title: {title}
Post URL: {url}
Post Summary: {summary_text}
Content Snippet: {content_snippet}

Respond with ONLY a JSON object:
{{"score": <float 0.0-1.0>, "explanation": "<one sentence>"}}\
"""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FilterResult:
    """Result from Stage 1 keyword filter."""

    passed: bool
    reason: str  # e.g. "matched positive keyword: amazon workspaces"


@dataclass
class ValidationResult:
    """Result from Stage 2 AI validator."""

    score: Optional[float]  # 0.0-1.0, None on error
    explanation: str
    error: Optional[str] = None


@dataclass
class PostFilterResult:
    """Combined result from the full two-stage pipeline."""

    accepted: bool
    stage: str  # "keyword" or "ai"
    relevance_score: Optional[float]
    reason: str


# ---------------------------------------------------------------------------
# Threshold helper (Req 4.1, 4.2, 4.3)
# ---------------------------------------------------------------------------


def get_relevance_threshold() -> float:
    """Read threshold from EUC_RELEVANCE_THRESHOLD env var, default 0.7.

    Returns the parsed float when the value is a valid number in [0.0, 1.0].
    Falls back to 0.7 (with a warning log) for missing, empty, non-numeric,
    or out-of-range values.
    """
    raw = os.environ.get(THRESHOLD_ENV_VAR, "")
    try:
        val = float(raw)
        if 0.0 <= val <= 1.0:
            return val
        logger.warning(
            "%s=%s out of range [0.0, 1.0], using default %s",
            THRESHOLD_ENV_VAR,
            raw,
            DEFAULT_RELEVANCE_THRESHOLD,
        )
        return DEFAULT_RELEVANCE_THRESHOLD
    except (ValueError, TypeError):
        if raw:
            logger.warning(
                "%s=%s is not a valid number, using default %s",
                THRESHOLD_ENV_VAR,
                raw,
                DEFAULT_RELEVANCE_THRESHOLD,
            )
        return DEFAULT_RELEVANCE_THRESHOLD
