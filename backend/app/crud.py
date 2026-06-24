from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app import models, schemas
from app.models import utcnow
from app.services.matching import score_job
from app.services.scraping import run_scrape, upsert_job

EXPORT_DIR = Path(__file__).resolve().parents[1] / "exports"
EXPORT_DIR.mkdir(exist_ok=True)


def job_to_read(job: models.Job) -> schemas.JobRead:
    return schemas.JobRead(
        id=job.id,
        external_id=job.external_id,
        title=job.title,
        company_id=job.company_id,
        company_name=job.company.name if job.company else "Unknown",
        location=job.location,
        work_arrangement=job.work_arrangement,
        salary_text=job.salary_text,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        currency=job.currency,
        employment_type=job.employment_type,
        experience_level=job.experience_level,
        description=job.description,
        requirements=job.requirements,
        application_url=job.application_url,
        source_url=job.source_url,
        source_type=job.source_type,
        skills=job.skills or [],
        posted_at=job.posted_at,
        first_seen_at=job.first_seen_at,
        last_seen_at=job.last_seen_at,
        status=job.status,
        match_score=job.match_score,
        extraction_confidence=job.extraction_confidence,
        raw_data=job.raw_data or {},
        is_saved=job.saved is not None,
    )


def scrape_run_to_read(run: models.ScrapeRun) -> schemas.ScrapeRunRead:
    return schemas.ScrapeRunRead(
        id=run.id,
        company_id=run.company_id,
        company_name=run.company.name if run.company else None,
        status=run.status,
        extraction_method=run.extraction_method,
        pages_discovered=run.pages_discovered,
        pages_processed=run.pages_processed,
        records_extracted=run.records_extracted,
        valid_records=run.valid_records,
        invalid_records=run.invalid_records,
        review_records=run.review_records,
        failed_pages=run.failed_pages,
        retry_count=run.retry_count,
        success_rate=run.success_rate,
        started_at=run.started_at,
        finished_at=run.finished_at,
        duration=run.duration,
        cancellation_requested=run.cancellation_requested,
        created_at=run.created_at,
    )


def saved_to_read(saved: models.SavedJob) -> schemas.SavedJobRead:
    return schemas.SavedJobRead(id=saved.id, job=job_to_read(saved.job), saved_at=saved.saved_at)


def application_to_read(application: models.Application) -> schemas.ApplicationRead:
    return schemas.ApplicationRead(
        id=application.id,
        job=job_to_read(application.job),
        stage=application.stage,
        applied_at=application.applied_at,
        next_action=application.next_action,
        notes=application.notes,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


def get_settings(db: Session) -> models.UserSettings:
    settings = db.get(models.UserSettings, 1)
    if settings:
        return settings
    settings = models.UserSettings(
        id=1,
        target_titles=["Data Engineer", "Backend Engineer", "Product Analyst"],
        preferred_locations=["Remote", "New York", "San Francisco"],
        work_arrangement="remote",
        minimum_salary=120000,
        experience_level="senior",
        required_skills=["python", "sql", "typescript", "fastapi"],
        excluded_companies=[],
        resume_text="Python data engineer with FastAPI, PostgreSQL, analytics, and TypeScript experience.",
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def list_jobs(db: Session, filters: dict[str, Any]) -> schemas.JobListResponse:
    page = max(1, int(filters.get("page") or 1))
    page_size = min(50, max(1, int(filters.get("page_size") or 10)))
    stmt = select(models.Job).options(joinedload(models.Job.company), selectinload(models.Job.saved)).where(models.Job.status != "deleted")

    keyword = filters.get("keyword")
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(or_(models.Job.title.ilike(pattern), models.Job.description.ilike(pattern), models.Job.location.ilike(pattern)))
    location = filters.get("location")
    if location:
        stmt = stmt.where(models.Job.location.ilike(f"%{location}%"))
    if filters.get("arrangement"):
        stmt = stmt.where(models.Job.work_arrangement == filters["arrangement"])
    if filters.get("employment_type"):
        stmt = stmt.where(models.Job.employment_type == filters["employment_type"])
    if filters.get("experience_level"):
        stmt = stmt.where(models.Job.experience_level == filters["experience_level"])
    if filters.get("company_id"):
        stmt = stmt.where(models.Job.company_id == int(filters["company_id"]))
    if filters.get("source"):
        stmt = stmt.where(models.Job.source_type == filters["source"])
    if filters.get("minimum_salary"):
        stmt = stmt.where(models.Job.salary_max >= float(filters["minimum_salary"]))
    if filters.get("skills"):
        skills = [item.strip().lower() for item in str(filters["skills"]).split(",") if item.strip()]
        for skill in skills:
            stmt = stmt.where(models.Job.skills.cast(str).ilike(f"%{skill}%"))
    if filters.get("date_posted"):
        days = int(filters["date_posted"])
        stmt = stmt.where(models.Job.posted_at >= datetime.now(timezone.utc) - timedelta(days=days))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(db.scalar(count_stmt) or 0)
    sort = filters.get("sort") or "match"
    if sort == "newest":
        stmt = stmt.order_by(models.Job.posted_at.desc().nullslast(), models.Job.created_at.desc())
    elif sort == "salary":
        stmt = stmt.order_by(models.Job.salary_max.desc().nullslast())
    elif sort == "company":
        stmt = stmt.join(models.Company).order_by(models.Company.name.asc(), models.Job.title.asc())
    else:
        stmt = stmt.order_by(models.Job.match_score.desc(), models.Job.posted_at.desc().nullslast())
    jobs = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return schemas.JobListResponse(items=[job_to_read(job) for job in jobs], total=total, page=page, page_size=page_size)


def get_job(db: Session, job_id: int) -> models.Job | None:
    return db.scalars(
        select(models.Job).where(models.Job.id == job_id).options(joinedload(models.Job.company), selectinload(models.Job.saved))
    ).first()


def save_job(db: Session, job_id: int) -> models.SavedJob:
    saved = db.scalars(select(models.SavedJob).where(models.SavedJob.job_id == job_id).options(joinedload(models.SavedJob.job).joinedload(models.Job.company))).first()
    if saved:
        return saved
    saved = models.SavedJob(job_id=job_id)
    db.add(saved)
    db.add(models.ActivityEvent(label="Job saved", detail=f"Saved job #{job_id}", level="info"))
    db.commit()
    return db.scalars(select(models.SavedJob).where(models.SavedJob.job_id == job_id).options(joinedload(models.SavedJob.job).joinedload(models.Job.company))).one()


def unsave_job(db: Session, job_id: int) -> None:
    saved = db.scalars(select(models.SavedJob).where(models.SavedJob.job_id == job_id)).first()
    if saved:
        db.delete(saved)
        db.add(models.ActivityEvent(label="Job unsaved", detail=f"Removed saved job #{job_id}", level="info"))
        db.commit()


def archive_job(db: Session, job: models.Job) -> models.Job:
    job.status = "archived"
    db.add(models.ActivityEvent(label="Job archived", detail=job.title, level="info"))
    db.commit()
    db.refresh(job)
    return job


def mark_applied(db: Session, job_id: int) -> models.Application:
    app = db.scalars(select(models.Application).where(models.Application.job_id == job_id).options(joinedload(models.Application.job).joinedload(models.Job.company))).first()
    if not app:
        app = models.Application(job_id=job_id, stage="applied", applied_at=utcnow(), next_action="Follow up in one week")
        db.add(app)
    else:
        app.stage = "applied"
        app.applied_at = app.applied_at or utcnow()
    db.add(models.ActivityEvent(label="Application updated", detail=f"Marked job #{job_id} as applied.", level="info"))
    db.commit()
    return db.scalars(select(models.Application).where(models.Application.job_id == job_id).options(joinedload(models.Application.job).joinedload(models.Job.company), joinedload(models.Application.job).joinedload(models.Job.saved))).one()


def dashboard(db: Session) -> schemas.DashboardData:
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    summary = schemas.DashboardSummary(
        active_jobs=int(db.scalar(select(func.count()).select_from(models.Job).where(models.Job.status == "active")) or 0),
        new_jobs_this_week=int(db.scalar(select(func.count()).select_from(models.Job).where(models.Job.first_seen_at >= week_ago)) or 0),
        companies_monitored=int(db.scalar(select(func.count()).select_from(models.Company).where(models.Company.monitoring_enabled.is_(True))) or 0),
        applications_in_progress=int(db.scalar(select(func.count()).select_from(models.Application).where(models.Application.stage.in_(["applied", "interview", "offer"]))) or 0),
        review_queue_count=int(db.scalar(select(func.count()).select_from(models.ReviewRecord).where(models.ReviewRecord.status == "pending")) or 0),
        last_success_rate=float(db.scalar(select(models.ScrapeRun.success_rate).order_by(models.ScrapeRun.created_at.desc()).limit(1)) or 0),
    )
    discovery_rows = db.execute(
        select(func.date(models.Job.first_seen_at), func.count()).group_by(func.date(models.Job.first_seen_at)).order_by(func.date(models.Job.first_seen_at))
    ).all()
    arrangement_rows = db.execute(select(models.Job.work_arrangement, func.count()).group_by(models.Job.work_arrangement)).all()
    top_jobs = db.scalars(
        select(models.Job).options(joinedload(models.Job.company), selectinload(models.Job.saved)).where(models.Job.status == "active").order_by(models.Job.match_score.desc()).limit(5)
    ).all()
    companies = db.scalars(select(models.Company).order_by(models.Company.name.asc()).limit(5)).all()
    activity = db.scalars(select(models.ActivityEvent).order_by(models.ActivityEvent.created_at.desc()).limit(8)).all()
    return schemas.DashboardData(
        summary=summary,
        job_discovery=[schemas.ChartPoint(label=str(day), value=int(count)) for day, count in discovery_rows],
        work_arrangement=[schemas.ChartPoint(label=label or "unknown", value=int(count)) for label, count in arrangement_rows],
        top_matches=[job_to_read(job) for job in top_jobs],
        scraping_health=companies,
        recent_activity=activity,
    )


def list_companies(db: Session) -> list[models.Company]:
    return list(db.scalars(select(models.Company).order_by(models.Company.name.asc())).all())


def create_company(db: Session, payload: schemas.CompanyCreate) -> models.Company:
    company = models.Company(**payload.model_dump())
    db.add(company)
    db.add(models.ActivityEvent(label="Company added", detail=company.name, level="info"))
    db.commit()
    db.refresh(company)
    return company


def update_company(db: Session, company: models.Company, payload: schemas.CompanyUpdate) -> models.Company:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, key, value)
    db.commit()
    db.refresh(company)
    return company


def list_scrape_runs(db: Session) -> list[schemas.ScrapeRunRead]:
    runs = db.scalars(select(models.ScrapeRun).options(joinedload(models.ScrapeRun.company)).order_by(models.ScrapeRun.created_at.desc())).all()
    return [scrape_run_to_read(run) for run in runs]


def create_export(db: Session, payload: schemas.ExportCreate) -> models.ExportRecord:
    jobs = db.scalars(select(models.Job).options(joinedload(models.Job.company)).where(models.Job.status != "deleted").order_by(models.Job.created_at.desc())).all()
    rows = []
    default_fields = [
        "company_name",
        "title",
        "location",
        "work_arrangement",
        "employment_type",
        "salary_text",
        "salary_min",
        "salary_max",
        "currency",
        "match_score",
        "source_type",
        "source_url",
        "application_url",
        "first_seen_at",
        "last_seen_at",
    ]
    fields = payload.fields or default_fields
    for job in jobs:
        read = job_to_read(job).model_dump(mode="json")
        rows.append({field: read.get(field) for field in fields})

    record = models.ExportRecord(name=f"{payload.dataset}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}", dataset=payload.dataset, format=payload.format, record_count=len(rows), status="processing")
    db.add(record)
    db.commit()
    db.refresh(record)
    path = EXPORT_DIR / f"{record.name}.{payload.format}"
    try:
        if payload.format == "json":
            path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        elif payload.format == "xlsx":
            pd.DataFrame(rows).to_excel(path, index=False)
        else:
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        record.status = "completed"
        record.file_path = str(path)
        db.add(models.ActivityEvent(label="Export ready", detail=f"{record.name}.{payload.format}", level="info"))
    except Exception as exc:
        record.status = "failed"
        record.file_path = None
        db.add(models.ActivityEvent(label="Export failed", detail=str(exc), level="error"))
    db.commit()
    db.refresh(record)
    return record


def approve_review(db: Session, review: models.ReviewRecord, data: dict | None = None) -> models.ReviewRecord:
    payload = data or review.extracted_data
    company_id = payload.get("company_id")
    if company_id and payload.get("title") and payload.get("application_url"):
        payload.setdefault("content_hash", f"manual-{review.id}-{payload['application_url']}")
        payload["extraction_confidence"] = max(float(review.confidence), 0.8)
        upsert_job(db, payload, get_settings(db))
    review.status = "approved"
    review.reviewed_at = utcnow()
    db.add(models.ActivityEvent(label="Review approved", detail=review.issue_type, level="info"))
    db.commit()
    db.refresh(review)
    return review


def reject_review(db: Session, review: models.ReviewRecord, status: str, notes: str | None = None) -> models.ReviewRecord:
    review.status = status
    review.reviewer_notes = notes
    review.reviewed_at = utcnow()
    db.add(models.ActivityEvent(label=f"Review {status}", detail=review.issue_type, level="warning"))
    db.commit()
    db.refresh(review)
    return review
