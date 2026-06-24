from __future__ import annotations

import os


def is_configured() -> bool:
    return bool(os.getenv("APIFY_API_TOKEN"))
