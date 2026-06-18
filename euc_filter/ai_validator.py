"""Stage 2 AI validator — scores post relevance using AWS Bedrock (Claude Haiku)."""

import json
import logging
import time
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from euc_filter.config import (
    AI_PROMPT_TEMPLATE,
    BACKOFF_MULTIPLIER,
    BASE_DELAY_SECONDS,
    BEDROCK_TIMEOUT_SECONDS,
    MAX_DELAY_SECONDS,
    MAX_RETRIES,
    ValidationResult,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

_RETRYABLE_ERRORS = frozenset(
    {
        "ThrottlingException",
        "TooManyRequestsException",
        "ServiceUnavailableException",
        "InternalServerError",
    }
)

_bedrock_client = None


def _get_bedrock_client():
    """Lazily create and cache the Bedrock runtime client."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name="us-east-1",
            config=BotoConfig(
                read_timeout=int(BEDROCK_TIMEOUT_SECONDS),
                connect_timeout=int(BEDROCK_TIMEOUT_SECONDS),
                retries={"max_attempts": 0},
            ),
        )
    return _bedrock_client


def _call_bedrock_with_retry(prompt: str) -> dict[str, Any] | None:
    """Call Bedrock with exponential backoff on transient errors.

    Retry schedule: 1s, 2s, 4s (max 3 attempts).
    Only retries on ThrottlingException, TooManyRequestsException,
    ServiceUnavailableException, and InternalServerError.

    Returns the parsed response body dict, or *None* when all retries are
    exhausted or a non-retryable error occurs.
    """
    client = _get_bedrock_client()
    delay = BASE_DELAY_SECONDS
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            body = json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 256,
                    "messages": [{"role": "user", "content": prompt}],
                }
            )
            response = client.invoke_model(modelId=MODEL_ID, body=body)
            response_body = json.loads(response["body"].read())
            return response_body
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code in _RETRYABLE_ERRORS:
                last_error = exc
                if attempt < MAX_RETRIES - 1:
                    sleep_time = min(delay, MAX_DELAY_SECONDS)
                    print(
                        f"[EUC Filter] Bedrock {error_code}, retry {attempt + 1}/{MAX_RETRIES} after {sleep_time:.1f}s"
                    )
                    time.sleep(sleep_time)
                    delay *= BACKOFF_MULTIPLIER
                continue
            # Non-retryable ClientError — propagate as None with logging
            print(f"[EUC Filter] Bedrock non-retryable error: {exc}")
            return None
        except Exception as exc:  # noqa: BLE001
            print(f"[EUC Filter] Unexpected error calling Bedrock: {exc}")
            return None

    print(
        f"[EUC Filter] Bedrock call failed after {MAX_RETRIES} retries: {last_error}"
    )
    return None


def _parse_ai_response(response_body: dict[str, Any]) -> ValidationResult:
    """Extract score and explanation from a Bedrock Claude Messages API response.

    Clamps score to [0.0, 1.0] if the model returns an out-of-range value.
    """
    try:
        # Claude Messages API returns content as a list of blocks
        text = response_body["content"][0]["text"]
        parsed = json.loads(text)
        raw_score = float(parsed["score"])
        explanation = str(parsed.get("explanation", ""))

        # Clamp score to valid range
        if raw_score < 0.0 or raw_score > 1.0:
            logger.warning(
                "AI returned out-of-range score %.4f, clamping to [0.0, 1.0]",
                raw_score,
            )
            raw_score = max(0.0, min(1.0, raw_score))

        return ValidationResult(score=raw_score, explanation=explanation)
    except (KeyError, IndexError, json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.error("Failed to parse AI response: %s", exc)
        return ValidationResult(score=None, explanation="", error="parse_error")


def ai_validate(title: str, url: str, content_snippet: str, summary_text: str = "") -> ValidationResult:
    """Run Stage 2 AI validation using Bedrock Claude Haiku.

    Args:
        title: Post title.
        url: Post URL.
        content_snippet: First ~500 characters of post content.
        summary_text: AI-generated summary (primary input for scoring).

    Returns:
        ValidationResult with score in [0.0, 1.0] on success, or
        score=None and error set on failure.
    """
    prompt = AI_PROMPT_TEMPLATE.format(
        title=title, url=url, content_snippet=content_snippet, summary_text=summary_text
    )

    response_body = _call_bedrock_with_retry(prompt)
    if response_body is None:
        return ValidationResult(score=None, explanation="", error="bedrock_call_failed")

    return _parse_ai_response(response_body)
