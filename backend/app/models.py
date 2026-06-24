from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    website: Mapped[str] = mapped_column(String(500))
    career_url: Mapped[str] = mapped_column(String(1000))
    source_type: Mapped[str] = mapped_column(String(80), default="fixture")
    extraction_method: Mapped[str] = mapped_column(String(80), default="fixture")
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    scrape_frequency: Mapped[str] = mapped_column(String(40), default="daily")
    health_status: Mapped[str] = mapped_column(String(40), default="healthy")
    last_scrape_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_scrape_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    selector_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    jobs: Mapped[list["Job"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    scrape_runs: Mapped[list["ScrapeRun"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(240), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(240), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    location: Mapped[str | None] = mapped_column(String(240), nullable=True, index=True)
    work_arrangement: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    salary_text: Mapped[str | None] = mapped_column(String(240), nullable=True)
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    experience_level: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_url: Mapped[str] = mapped_column(String(1200), index=True)
    source_url: Mapped[str | None] = mapped_column(String(1200), nullable=True)
    source_type: Mapped[str] = mapped_column(String(80), default="fixture")
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    match_score: Mapped[float] = mapped_column(Float, default=0)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    content_hash: Mapped[str] = mapped_column(String(128), index=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)

    company: Mapped[Company] = relationship(back_populates="jobs")
    saved: Mapped["SavedJob | None"] = relationship(back_populates="job", cascade="all, delete-orphan", uselist=False)
    applications: Mapped[list["Application"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    extraction_method: Mapped[str] = mapped_column(String(80), default="fixture")
    pages_discovered: Mapped[int] = mapped_column(Integer, default=0)
    pages_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_extracted: Mapped[int] = mapped_column(Integer, default=0)
    valid_records: Mapped[int] = mapped_column(Integer, default=0)
    invalid_records: Mapped[int] = mapped_column(Integer, default=0)
    review_records: Mapped[int] = mapped_column(Integer, default=0)
    failed_pages: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(Float, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    cancellation_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    company: Mapped[Company | None] = relationship(back_populates="scrape_runs")
    logs: Mapped[list["ScrapeLog"]] = relationship(back_populates="scrape_run", cascade="all, delete-orphan")
    review_records_rel: Mapped[list["ReviewRecord"]] = relationship(back_populates="scrape_run")


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scrape_run_id: Mapped[int] = mapped_column(ForeignKey("scrape_runs.id", ondelete="CASCADE"), index=True)
    level: Mapped[str] = mapped_column(String(20), default="info")
    message: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(1200), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    scrape_run: Mapped[ScrapeRun] = relationship(back_populates="logs")


class ReviewRecord(Base):
    __tablename__ = "review_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    scrape_run_id: Mapped[int | None] = mapped_column(ForeignKey("scrape_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    issue_type: Mapped[str] = mapped_column(String(120), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    extracted_data: Mapped[dict] = mapped_column(JSON, default=dict)
    source_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    job: Mapped[Job | None] = relationship()
    scrape_run: Mapped[ScrapeRun | None] = relationship(back_populates="review_records_rel")


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, index=True)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    job: Mapped[Job] = relationship(back_populates="saved")


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, index=True)
    stage: Mapped[str] = mapped_column(String(40), default="applied", index=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_action: Mapped[str | None] = mapped_column(String(240), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[Job] = relationship(back_populates="applications")


class ExportRecord(Base):
    __tablename__ = "export_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180))
    dataset: Mapped[str] = mapped_column(String(80), default="jobs")
    format: Mapped[str] = mapped_column(String(20), default="csv")
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="processing")
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_titles: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_locations: Mapped[list[str]] = mapped_column(JSON, default=list)
    work_arrangement: Mapped[str] = mapped_column(String(80), default="remote")
    minimum_salary: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience_level: Mapped[str] = mapped_column(String(80), default="mid")
    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    excluded_companies: Mapped[list[str]] = mapped_column(JSON, default=list)
    default_scrape_frequency: Mapped[str] = mapped_column(String(40), default="daily")
    concurrency: Mapped[int] = mapped_column(Integer, default=4)
    retry_limit: Mapped[int] = mapped_column(Integer, default=2)
    request_timeout: Mapped[int] = mapped_column(Integer, default=20)
    browser_automation: Mapped[str] = mapped_column(String(80), default="auto")
    save_snapshots: Mapped[bool] = mapped_column(Boolean, default=True)
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(160))
    detail: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(20), default="info")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
