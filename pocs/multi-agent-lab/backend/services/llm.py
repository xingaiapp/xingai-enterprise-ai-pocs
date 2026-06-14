from __future__ import annotations

import json
from typing import Any, Optional

from openai import OpenAI

from config import settings


def _client() -> Optional[OpenAI]:
    if not settings.openai_configured:
        return None
    return OpenAI(api_key=settings.openai_api_key)


def chat_json(system: str, user: str) -> dict[str, Any]:
    client = _client()
    if not client:
        return {}

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)
