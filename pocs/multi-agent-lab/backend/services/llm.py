from __future__ import annotations

import json
import logging
from typing import Any

from openai import APIConnectionError, OpenAI, OpenAIError, RateLimitError

from config import settings

logger = logging.getLogger(__name__)


def _client() -> OpenAI | None:
    if not settings.openai_configured:
        return None
    return OpenAI(api_key=settings.openai_api_key)


def chat_json(
    system: str,
    user: str,
    request_id: str = "",
    temperature: float = 0.4,
) -> dict[str, Any]:
    """Call OpenAI and return parsed JSON. Returns {} on any failure."""
    client = _client()
    if not client:
        logger.debug("[%s] OpenAI not configured — skipping LLM call", request_id)
        return {}

    log_ctx = request_id or "no-request-id"
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        content = response.choices[0].message.content or "{}"
        result = json.loads(content)
        logger.debug("[%s] LLM call succeeded, keys=%s", log_ctx, list(result.keys()))
        return result

    except RateLimitError:
        logger.warning("[%s] OpenAI rate limit hit", log_ctx)
        return {}
    except APIConnectionError:
        logger.warning("[%s] OpenAI connection error", log_ctx)
        return {}
    except json.JSONDecodeError as exc:
        logger.error("[%s] LLM returned non-JSON: %s", log_ctx, exc)
        return {}
    except OpenAIError as exc:
        logger.error("[%s] OpenAI error: %s", log_ctx, exc)
        return {}
