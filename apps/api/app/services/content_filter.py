"""
Content moderation guard for user-supplied text.

Uses the OpenAI Moderation API (free endpoint) to detect policy violations
before any text reaches the main LLM pipeline.  When OPENAI_API_KEY is
unset the check is skipped silently so development works without keys.

Raises `ContentPolicyViolation` when the text is flagged; callers should
translate this into a 400 response.
"""

from app.core.config import settings
from app.observability import get_logger

logger = get_logger(__name__)


class ContentPolicyViolation(Exception):
    """Raised when user input is flagged by the moderation endpoint."""

    def __init__(self, categories: list[str]) -> None:
        self.categories = categories
        super().__init__(f"Content flagged: {', '.join(categories)}")


async def check(text: str) -> None:
    """
    Moderate *text* via the OpenAI Moderation API.

    No-op when OPENAI_API_KEY is not configured.
    Raises ContentPolicyViolation if the text is flagged.
    """
    if not settings.OPENAI_API_KEY or not text:
        return

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        response = await client.moderations.create(input=text)
        result = response.results[0]

        if result.flagged:
            flagged_cats = [
                cat for cat, active in result.categories.model_dump().items() if active
            ]
            logger.warning(
                "content_moderation_flagged",
                extra={"categories": flagged_cats},
            )
            raise ContentPolicyViolation(flagged_cats)

    except ContentPolicyViolation:
        raise
    except Exception as exc:
        # Moderation errors must not block legitimate requests.
        logger.warning("content_moderation_error", extra={"error": str(exc)})
