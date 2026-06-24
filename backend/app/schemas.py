from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

HealthStatus = Literal["healthy", "warning", "error", "paused"]
ScrapeStatus = Literal["queued", "running", "completed", "warning", "failed", "cancelled"]
ReviewStatus = Literal["pending", "approved", "rejected", "duplicate"]
ApplicationStage = Literal["wishlist", "applied", "interview", "offer", "rejected"]
ExportFormat = Literal["csv", "json", "xlsx"]


class CompanyBase(BaseModel):
    name: str
    website: str
    career_url: str
    source_type: str = "fixture"
    extraction_method: str = "fixture"
    monitoring_enabled: bool = True
    scrape_frequency: str = "daily"

    @field_validator("website", "career_url")
    @classmethod
    def valid_urlish(cls, value: str) -> str:
        if value.startswith(("http://", "https://", "fixture://")):
            return value
        raise ValueError("URL must start with http://, https://, or fixture://")


class CompanyCreate(CompanyBase):
    selector_config: dict[str, Any] | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    website: str | None = None
    career_url: str | None = None
    source_type: str | None = None
    extraction_method: str | None = None
    monitoring_enabled: bool | None = None
    scrape_frequency: str | None = None
    health_status: str | None = None
    selector_config: dict[str, Any] | None = None


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    health_status: HealthStatus
    last_scrape_at: datetime | None
    next_scrape_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JobBase(BaseModel):
    external_id: str | None = None
    title: str
    location: str | None = None
    work_arrangement: str | None = None
    salary_text: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    employment_type: str | None = None
    experience_level: str | None = None
    description: str | None = None
    requirements: str | None = None
    application_url: str
    source_url: str | None = None
    source_type: str = "fixture"
    skills: list[str] = Field(default_factory=list)
    posted_at: datetime | None = None
    status: str = "active"
    match_score: float = 0
    extraction_confidence: float = 0
    raw_data: dict[str, Any] = Field(default_factory=dict)


class JobRead(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    company_name: str
    first_seen_at: datetime
    last_seen_at: datetime
    is_saved: bool = False


class JobListResponse(BaseModel):
    items: list[JobRead]
    total: int
    page: int
    page_size: int


class ScrapeRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int | None
    company_name: str | None
    status: ScrapeStatus
    extraction_method: str
    pages_discovered: int
    pages_processed: int
    records_extracted: int
    valid_records: int
    invalid_records: int
    review_records: int
    failed_pages: int
    retry_count: int
    success_rate: float
    started_at: datetime | None
    finished_at: datetime | None
    duration: float | None
    cancellation_requested: bool
    created_at: datetime


class ScrapeLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scrape_run_id: int
    level: Literal["info", "warning", "error"]
    message: str
    url: str | None
    http_status: int | None
    error_category: str | None
    created_at: datetime


class ReviewRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int | None
    scrape_run_id: int | None
    issue_type: str
    confidence: float
    extracted_data: dict[str, Any]
    source_evidence: str | None
    status: ReviewStatus
    reviewer_notes: str | None
    reviewed_at: datetime | None
    created_at: datetime


class ReviewAction(BaseModel):
    extracted_data: dict[str, Any] | None = None
    reviewer_notes: str | None = None


class SavedJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job: JobRead
    saved_at: datetime


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job: JobRead
    stage: ApplicationStage
    applied_at: datetime | None
    next_action: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ApplicationUpdate(BaseModel):
    stage: ApplicationStage | None = None
    notes: str | None = None
    next_action: str | None = None


class ExportCreate(BaseModel):
    dataset: str = "jobs"
    format: ExportFormat = "csv"
    fields: list[str] | None = None


class ExportRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    dataset: str
    format: ExportFormat
    record_count: int
    status: Literal["processing", "completed", "failed"]
    file_path: str | None
    created_at: datetime


class UserSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_titles: list[str]
    preferred_locations: list[str]
    work_arrangement: str
    minimum_salary: float | None
    experience_level: str
    required_skills: list[str]
    excluded_companies: list[str]
    default_scrape_frequency: str
    concurrency: int
    retry_limit: int
    request_timeout: int
    browser_automation: str
    save_snapshots: bool
    resume_text: str | None


class UserSettingsUpdate(BaseModel):
    target_titles: list[str] | None = None
    preferred_locations: list[str] | None = None
    work_arrangement: str | None = None
    minimum_salary: float | None = None
    experience_level: str | None = None
    required_skills: list[str] | None = None
    excluded_companies: list[str] | None = None
    default_scrape_frequency: str | None = None
    concurrency: int | None = None
    retry_limit: int | None = None
    request_timeout: int | None = None
    browser_automation: str | None = None
    save_snapshots: bool | None = None
    resume_text: str | None = None


class DashboardSummary(BaseModel):
    active_jobs: int
    new_jobs_this_week: int
    companies_monitored: int
    applications_in_progress: int
    review_queue_count: int
    last_success_rate: float


class ChartPoint(BaseModel):
    label: str
    value: int


class ActivityEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    detail: str
    level: Literal["info", "warning", "error"]
    created_at: datetime


class DashboardData(BaseModel):
    summary: DashboardSummary
    job_discovery: list[ChartPoint]
    work_arrangement: list[ChartPoint]
    top_matches: list[JobRead]
    scraping_health: list[CompanyRead]
    recent_activity: list[ActivityEventRead]


class IntegrationStatus(BaseModel):
    openrouter: Literal["configured", "not_configured"]
    apify: Literal["configured", "not_configured"]
    google_sheets: Literal["configured", "not_configured"]


class StartScrapeRequest(BaseModel):
    company_id: int | None = None
