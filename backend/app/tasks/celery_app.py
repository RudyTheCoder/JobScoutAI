from __future__ import annotations

import os

from celery import Celery

celery_app = Celery(
    "job_scout_ai",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=["app.tasks.scrape_tasks"],
)

celery_app.conf.beat_schedule = {
    "scheduled-demo-scrapes": {
        "task": "app.tasks.scrape_tasks.run_scheduled_scrapes",
        "schedule": 60 * 60,
    }
}

from app.tasks import scrape_tasks  # noqa: E402,F401
