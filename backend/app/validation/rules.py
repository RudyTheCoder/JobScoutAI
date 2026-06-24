from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import models


@dataclass
class ValidationResult:
    confidence: float
    issues: list[str]
    likely_duplicate_id: int | None = None


RECOGNIZED_EMPLOYMENT = {"full_time", "part_time", "contract", "internship"}
RECOGNIZED_WORK = {"remote", "hybrid", "on_site"}


def find_duplicate(db: Session, record: dict) -> models.Job | None:
    external_id = record.get("external_id")
    application_url = record.get("application_url")
    content_hash = record.get("content_hash")
    company_id = record.get("company_id")
    title = (record.get("title") or "").strip().lower()
    stmt = select(models.Job)
    clauses = []
    if external_id:
        clauses.append(models.Job.external_id == external_id)
    if application_url:
        clauses.append(models.Job.application_url == application_url)
    if content_hash:
        clauses.append(models.Job.content_hash == content_hash)
    if title and company_id:
        clauses.append((models.Job.company_id == company_id) & (models.Job.title.ilike(title)))
    if not clauses:
        return None
    return db.scalars(stmt.where(or_(*clauses))).first()


def validate_record(db: Session, record: dict, meta: dict | None = None) -> ValidationResult:
    meta = meta or {}
    confidence = 1.0
    issues: list[str] = []

    def issue(name: str, penalty: float) -> None:
        nonlocal confidence
        issues.append(name)
        confidence -= penalty

    if not record.get("title"):
        issue("missing_title", 0.35)
    if not record.get("company_id"):
        issue("missing_company", 0.35)
    if not record.get("application_url"):
        issue("invalid_application_url", 0.25)
    if meta.get("invalid_date"):
        issue("invalid_date", 0.25)
    if record.get("salary_min") is not None and record.get("salary_max") is not None and record["salary_min"] > record["salary_max"]:
        issue("salary_min_greater_than_max", 0.3)
    if record.get("employment_type") not in RECOGNIZED_EMPLOYMENT:
        issue("unrecognized_employment_type", 0.15)
    if record.get("work_arrangement") and record.get("work_arrangement") not in RECOGNIZED_WORK:
        issue("unrecognized_work_arrangement", 0.15)
    if meta.get("ambiguous_location"):
        issue("ambiguous_location", 0.2)
    if not record.get("description"):
        issue("missing_description", 0.1)
    duplicate = find_duplicate(db, record)
    if duplicate:
        issue("likely_duplicate", 0.3)

    return ValidationResult(confidence=max(0.0, round(confidence, 2)), issues=issues, likely_duplicate_id=duplicate.id if duplicate else None)
