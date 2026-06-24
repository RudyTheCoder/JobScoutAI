from __future__ import annotations

import os


def is_configured() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY"))


async def summarize_match(deterministic_result: dict) -> str:
    if not is_configured():
        return "OpenRouter is not configured; deterministic match details are shown instead."
    return "OpenRouter is configured; AI summaries must validate against Pydantic before display."
