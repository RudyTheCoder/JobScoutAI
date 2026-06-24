from __future__ import annotations

from sqlalchemy import select

from app import models
from app.database import SessionLocal
from app.services.scraping import run_scrape
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.scrape_tasks.scrape_company")
def scrape_company(company_id: int) -> int:
    with SessionLocal() as db:
        company = db.get(models.Company, company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")
        return run_scrape(db, company).id


@celery_app.task(name="app.tasks.scrape_tasks.run_scheduled_scrapes")
def run_scheduled_scrapes() -> list[int]:
    run_ids: list[int] = []
    with SessionLocal() as db:
        companies = db.scalars(select(models.Company).where(models.Company.monitoring_enabled.is_(True))).all()
        for company in companies:
            run_ids.append(run_scrape(db, company).id)
    return run_ids
