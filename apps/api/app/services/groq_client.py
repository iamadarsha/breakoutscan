"""One place to call Groq chat completions with model fallback."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.config import Settings

logger = logging.getLogger(__name__)


def groq_model_chain(settings: Settings) -> list[str]:
    chain = [settings.groq_model, *settings.groq_fallback_models.split(",")]
    seen: set[str] = set()
    return [m.strip() for m in chain if m.strip() and not (m.strip() in seen or seen.add(m.strip()))]


async def groq_chat_text(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> str | None:
    """First non-empty JSON-mode reply from the configured model chain, else None.

    A model that is gone (404), rejects the request (400) or is rate-limited
    (429) moves on to the next model; a timeout or auth failure stops early
    since another model would fail the same way.
    """
    if not settings.groq_api_key:
        return None

    from groq import (
        APITimeoutError,
        AsyncGroq,
        AuthenticationError,
        BadRequestError,
        NotFoundError,
        RateLimitError,
    )

    client = AsyncGroq(api_key=settings.groq_api_key)
    for model in groq_model_chain(settings):
        try:
            response: Any = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                ),
                timeout=timeout,
            )
            text = response.choices[0].message.content or ""
            if text.strip():
                return text
            logger.warning("groq_empty_reply model=%s", model)
        except (NotFoundError, BadRequestError, RateLimitError) as exc:
            logger.warning("groq_model_unavailable model=%s error=%s", model, type(exc).__name__)
            continue
        except (asyncio.TimeoutError, APITimeoutError):
            logger.warning("groq_timeout model=%s", model)
            return None
        except AuthenticationError:
            logger.error("groq_auth_failed — check GROQ_API_KEY")
            return None
    return None
