from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import models
from app.database import Base, SessionLocal, engine
from app.services.normalization import content_hash, parse_date, parse_salary


COMPANIES = [
    {"name": "Northstar Systems", "website": "https://northstar.example", "career_url": "fixture://static", "source_type": "fixture", "extraction_method": "fixture"},
    {"name": "Lumen Cloud", "website": "https://lumen.example", "career_url": "fixture://paginated-1", "source_type": "fixture", "extraction_method": "paginated_fixture"},
    {"name": "QuietPath Labs", "website": "https://quietpath.example", "career_url": "fixture://detail-list", "source_type": "fixture", "extraction_method": "detail_fixture"},
    {"name": "BrightTable", "website": "https://brighttable.example", "career_url": "fixture://javascript", "source_type": "fixture", "extraction_method": "playwright"},
    {"name": "Static Careers Demo", "website": "https://static-careers.example", "career_url": "fixture://static-realistic", "source_type": "generic/html", "extraction_method": "generic_html"},
    {
        "name": "Tailscale",
        "website": "https://tailscale.com",
        "career_url": "https://boards-api.greenhouse.io/v1/boards/tailscale/jobs?content=true",
        "source_type": "greenhouse",
        "extraction_method": "greenhouse",
        "scrape_frequency": "weekly",
    },
    {
        "name": "PostHog",
        "website": "https://posthog.com",
        "career_url": "https://api.ashbyhq.com/posting-api/job-board/posthog?includeCompensation=true",
        "source_type": "ashby",
        "extraction_method": "ashby",
        "scrape_frequency": "weekly",
    },
    {
        "name": "Supabase",
        "website": "https://supabase.com",
        "career_url": "https://api.ashbyhq.com/posting-api/job-board/supabase?includeCompensation=true",
        "source_type": "ashby",
        "extraction_method": "ashby",
        "scrape_frequency": "weekly",
    },
    {
        "name": "Render",
        "website": "https://render.com",
        "career_url": "https://api.ashbyhq.com/posting-api/job-board/render?includeCompensation=true",
        "source_type": "ashby",
        "extraction_method": "ashby",
        "scrape_frequency": "weekly",
    },
    {"name": "Lever Demo Co", "website": "https://lever-demo.example", "career_url": "fixture://lever", "source_type": "lever", "extraction_method": "lever", "scrape_frequency": "weekly"},
    {"name": "Greenhouse Demo Co", "website": "https://greenhouse-demo.example", "career_url": "fixture://greenhouse", "source_type": "greenhouse", "extraction_method": "greenhouse", "scrape_frequency": "weekly"},
]


def make_job(company: models.Company, **values) -> models.Job:
    salary_min, salary_max, currency = parse_salary(values.get("salary_text"))
    posted_at = parse_date(values.get("posted_at"))
    payload = {
        "external_id": values.get("external_id"),
        "title": values["title"],
        "company_id": company.id,
        "location": values.get("location"),
        "work_arrangement": values.get("work_arrangement", "remote"),
        "salary_text": values.get("salary_text"),
        "salary_min": salary_min,
        "salary_max": salary_max,
        "currency": currency,
        "employment_type": values.get("employment_type", "full_time"),
        "experience_level": values.get("experience_level", "mid"),
        "description": values.get("description"),
        "requirements": values.get("requirements"),
        "application_url": values["application_url"],
        "source_url": values.get("source_url") or company.career_url,
        "source_type": company.source_type,
        "skills": values.get("skills", []),
        "posted_at": posted_at,
        "status": values.get("status", "active"),
        "match_score": values.get("match_score", 0),
        "extraction_confidence": values.get("extraction_confidence", 0.95),
        "raw_data": {"match_explanation": values.get("match_explanation", {})},
    }
    payload["content_hash"] = content_hash(payload)
    return models.Job(**payload)


def seed_database(db: Session, force: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    has_companies = db.scalars(select(models.Company.id).limit(1)).first()
    if has_companies and not force:
        existing_names = set(db.scalars(select(models.Company.name)).all())
        now = datetime.now(timezone.utc)
        for index, item in enumerate(COMPANIES):
            if item["name"] in existing_names:
                continue
            db.add(
                models.Company(
                    name=item["name"],
                    website=item["website"],
                    career_url=item["career_url"],
                    source_type=item["source_type"],
                    extraction_method=item["extraction_method"],
                    monitoring_enabled=True,
                    scrape_frequency=item.get("scrape_frequency", "daily" if index < 5 else "weekly"),
                    health_status="healthy",
                    next_scrape_at=now + timedelta(days=1),
                    selector_config=item.get("selector_config"),
                )
            )
            db.add(models.ActivityEvent(label="Company added", detail=f"Seeded {item['name']} source configuration.", level="info"))
        db.commit()
        return

    if force:
        for table in [
            models.ActivityEvent,
            models.ExportRecord,
            models.Application,
            models.SavedJob,
            models.ReviewRecord,
            models.ScrapeLog,
            models.ScrapeRun,
            models.Job,
            models.Company,
            models.UserSettings,
        ]:
            db.execute(delete(table))
        db.commit()

    settings = models.UserSettings(
        id=1,
        target_titles=["Senior Data Engineer", "Backend API Engineer", "Product Analyst"],
        preferred_locations=["Remote", "New York", "San Francisco"],
        work_arrangement="remote",
        minimum_salary=120000,
        experience_level="senior",
        required_skills=["python", "sql", "fastapi", "typescript"],
        excluded_companies=[],
        default_scrape_frequency="daily",
        concurrency=4,
        retry_limit=2,
        request_timeout=20,
        browser_automation="auto",
        save_snapshots=True,
        resume_text="Senior data engineer with Python, FastAPI, SQL, PostgreSQL, TypeScript, and analytics experience.",
    )
    db.add(settings)

    companies: list[models.Company] = []
    now = datetime.now(timezone.utc)
    for index, item in enumerate(COMPANIES):
        company = models.Company(
            name=item["name"],
            website=item["website"],
            career_url=item["career_url"],
            source_type=item["source_type"],
            extraction_method=item["extraction_method"],
            monitoring_enabled=True,
            scrape_frequency=item.get("scrape_frequency", "daily" if index < 5 else "weekly"),
            health_status="healthy" if index != 2 else "warning",
            last_scrape_at=now - timedelta(days=index + 1),
            next_scrape_at=now + timedelta(days=1),
            selector_config=item.get("selector_config"),
        )
        db.add(company)
        companies.append(company)
    db.flush()

    jobs = [
        make_job(companies[0], external_id="NS-101", title="Senior Data Engineer", location="Remote, US", work_arrangement="remote", salary_text="$145k - $175k", employment_type="full_time", experience_level="senior", description="Build Python and PostgreSQL data pipelines with FastAPI, Docker, and analytics workflows.", application_url="https://northstar.example/jobs/NS-101", posted_at="2026-06-10", skills=["python", "postgresql", "fastapi", "docker", "analytics"], match_score=96),
        make_job(companies[0], external_id="NS-102", title="Product Analyst", location="New York, NY", work_arrangement="on_site", salary_text="$105k - $125k", employment_type="full_time", experience_level="mid", description="Use SQL and analytics to improve marketplace decisions.", application_url="https://northstar.example/jobs/NS-102", posted_at="2026-06-12", skills=["sql", "analytics"], match_score=76),
        make_job(companies[1], external_id="LC-201", title="Frontend Platform Engineer", location="Hybrid - Austin, TX", work_arrangement="hybrid", salary_text="$130k - $160k", employment_type="full_time", experience_level="senior", description="Own React, Next.js, TypeScript, design systems, and accessibility.", application_url="https://lumen.example/jobs/LC-201", posted_at="2026-06-08", skills=["react", "next.js", "typescript"], match_score=72),
        make_job(companies[1], external_id="LC-202", title="Machine Learning Engineer", location="San Francisco, CA", work_arrangement="on_site", salary_text=None, employment_type="full_time", experience_level="mid", description="Deploy ML and NLP services with Python, Docker, Kubernetes, and AWS.", application_url="https://lumen.example/jobs/LC-202", posted_at="2026-06-09", skills=["python", "machine learning", "nlp", "docker", "kubernetes", "aws"], match_score=68),
        make_job(companies[2], external_id="QP-301", title="Backend API Engineer", location="Remote, US", work_arrangement="remote", salary_text="$125k-$150k", employment_type="full_time", experience_level="mid", description="Build FastAPI services, Celery jobs, Redis queues, and SQLAlchemy models.", application_url="https://quietpath.example/jobs/QP-301", posted_at="2026-06-11", skills=["fastapi", "celery", "redis", "sql"], match_score=88),
        make_job(companies[3], external_id="BT-401", title="Data Platform Lead", location="Remote or hybrid", work_arrangement="remote", salary_text="$170k - $210k", employment_type="full_time", experience_level="lead", description="Lead Python, PostgreSQL, ETL, and analytics platform work.", application_url="https://brighttable.example/jobs/BT-401", posted_at="2026-06-13", skills=["python", "postgresql", "etl", "analytics"], match_score=90),
    ]
    db.add_all(jobs)
    db.flush()

    db.add(models.SavedJob(job_id=jobs[0].id))
    db.add(models.SavedJob(job_id=jobs[4].id))
    db.add(models.Application(job_id=jobs[1].id, stage="applied", applied_at=now - timedelta(days=2), next_action="Send portfolio link", notes="Applied through company site."))
    db.add(models.Application(job_id=jobs[4].id, stage="interview", applied_at=now - timedelta(days=8), next_action="Prepare FastAPI scraper walkthrough", notes="Recruiter screen complete."))

    db.add(models.ReviewRecord(issue_type="ambiguous_location, invalid_date", confidence=0.52, extracted_data={"title": "Growth Data Analyst", "company_id": companies[2].id, "location": "USA / Canada", "application_url": "", "posted_at": "last someday"}, source_evidence="fixture://detail-302", status="pending"))
    db.add(models.ReviewRecord(issue_type="likely_duplicate", confidence=0.7, extracted_data={"title": "Senior Data Engineer", "company_id": companies[0].id, "location": "Remote - US", "application_url": "https://northstar.example/jobs/NS-101"}, source_evidence="fixture://static", status="pending"))

    run = models.ScrapeRun(company_id=companies[0].id, status="completed", extraction_method="fixture", pages_discovered=1, pages_processed=1, records_extracted=3, valid_records=2, invalid_records=0, review_records=1, failed_pages=0, success_rate=66.7, started_at=now - timedelta(hours=3), finished_at=now - timedelta(hours=3, minutes=-1), duration=22.0)
    db.add(run)
    db.flush()
    db.add(models.ScrapeLog(scrape_run_id=run.id, level="info", message="Loaded local fixture static.html", url="fixture://static", http_status=200))
    db.add(models.ScrapeLog(scrape_run_id=run.id, level="warning", message="Duplicate record sent to review", url="fixture://static", error_category="duplicate"))

    db.add(models.ExportRecord(name="jobs-seed-snapshot", dataset="jobs", format="csv", record_count=len(jobs), status="completed", file_path=None))
    for label, detail, level in [
        ("Seed data loaded", "Fictional companies and fixture jobs are ready.", "info"),
        ("Review item created", "Ambiguous fixture record needs human review.", "warning"),
        ("Application updated", "Backend API Engineer moved to interview.", "info"),
    ]:
        db.add(models.ActivityEvent(label=label, detail=detail, level=level))

    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed_database(db, force=False)
    print("Ensured JobScout AI demo companies, jobs, reviews, runs, and applications are seeded.")


if __name__ == "__main__":
    main()
