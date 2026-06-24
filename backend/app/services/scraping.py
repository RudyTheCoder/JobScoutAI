from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import models
from app.models import utcnow
from app.scrapers.adapters import extract_sync
from app.services.matching import score_job
from app.services.normalization import normalize_record
from app.validation.rules import validate_record


def log(db: Session, run: models.ScrapeRun, level: str, message: str, url: str | None = None, http_status: int | None = None, error_category: str | None = None) -> None:
    db.add(models.ScrapeLog(scrape_run_id=run.id, level=level, message=message, url=url, http_status=http_status, error_category=error_category))


def upsert_job(db: Session, record: dict, settings: models.UserSettings | None) -> models.Job:
    clauses = []
    if record.get("application_url"):
        clauses.append(models.Job.application_url == record["application_url"])
    if record.get("external_id"):
        clauses.append((models.Job.company_id == record["company_id"]) & (models.Job.external_id == record["external_id"]))
    if record.get("content_hash"):
        clauses.append(models.Job.content_hash == record["content_hash"])
    if record.get("title") and record.get("company_id"):
        clauses.append((models.Job.company_id == record["company_id"]) & (models.Job.title.ilike(record["title"])))
    existing = db.scalars(select(models.Job).where(or_(*clauses))).first() if clauses else None
    if existing:
        for key, value in record.items():
            if key not in {"company_id", "raw_data"}:
                setattr(existing, key, value)
        existing.last_seen_at = utcnow()
        job = existing
    else:
        job = models.Job(**record)
        db.add(job)
        db.flush()
    score, explanation = score_job(job, settings)
    job.match_score = score
    job.raw_data = {**(job.raw_data or {}), "match_explanation": explanation}
    return job


def create_review(db: Session, run: models.ScrapeRun, record: dict, issues: list[str], confidence: float, evidence: str | None = None) -> models.ReviewRecord:
    serializable_record = json.loads(json.dumps(record, default=str))
    review = models.ReviewRecord(
        scrape_run_id=run.id,
        issue_type=", ".join(issues),
        confidence=confidence,
        extracted_data=serializable_record,
        source_evidence=evidence or record.get("source_url"),
    )
    db.add(review)
    return review


def run_scrape(db: Session, company: models.Company, retry_count: int = 0) -> models.ScrapeRun:
    run = models.ScrapeRun(company_id=company.id, status="running", extraction_method=company.extraction_method, retry_count=retry_count, started_at=utcnow())
    db.add(run)
    db.commit()
    db.refresh(run)
    settings = db.get(models.UserSettings, 1)

    try:
        log(db, run, "info", f"Starting scrape for {company.name}", company.career_url)
        result = extract_sync(company)
        run.pages_discovered = result.pages_discovered
        run.pages_processed = result.pages_processed
        run.failed_pages = result.failed_pages
        run.records_extracted = len(result.records)

        for raw in result.records:
            record, meta = normalize_record(raw, company.id, company.source_type, company.career_url)
            validation = validate_record(db, record, meta)
            if validation.issues and (validation.confidence < 0.8 or "likely_duplicate" in validation.issues or "missing_title" in validation.issues):
                create_review(db, run, record, validation.issues, validation.confidence)
                run.review_records += 1
                if "likely_duplicate" in validation.issues:
                    log(db, run, "warning", f"Likely duplicate sent to review: {record.get('title')}", record.get("source_url"), error_category="duplicate")
                else:
                    run.invalid_records += 1
                    log(db, run, "warning", f"Record needs review: {', '.join(validation.issues)}", record.get("source_url"), error_category="validation")
                continue
            record["extraction_confidence"] = validation.confidence
            upsert_job(db, record, settings)
            run.valid_records += 1

        total_processed = max(1, run.records_extracted)
        run.success_rate = round((run.valid_records / total_processed) * 100, 1)
        run.status = "warning" if run.review_records or run.invalid_records else "completed"
        company.health_status = "warning" if run.status == "warning" else "healthy"
        company.last_scrape_at = utcnow()
        company.next_scrape_at = company.last_scrape_at + timedelta(days=1 if company.scrape_frequency == "daily" else 7)
        log(db, run, "info", f"Finished with {run.valid_records} valid records and {run.review_records} review records.")
    except Exception as exc:
        run.status = "failed"
        run.failed_pages += 1
        company.health_status = "error"
        log(db, run, "error", str(exc), company.career_url, error_category=exc.__class__.__name__)
    finally:
        run.finished_at = utcnow()
        if run.started_at:
            started_at = run.started_at.replace(tzinfo=run.finished_at.tzinfo) if run.started_at.tzinfo is None else run.started_at
            run.duration = (run.finished_at - started_at).total_seconds()
        db.add(models.ActivityEvent(label="Scrape finished", detail=f"{company.name}: {run.status} with {run.records_extracted} records.", level="warning" if run.status == "warning" else "info"))
        db.commit()
        db.refresh(run)
    return run
