from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app import crud, models, schemas
from app.database import Base, engine, get_db
from app.seed import seed_database
from app.services.matching import score_job
from app.services.scraping import run_scrape

app = FastAPI(title="JobScout AI API", version="1.0.0")

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin, "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    from app.database import SessionLocal

    with SessionLocal() as db:
        seed_database(db, force=False)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "job-scout-ai"}


@app.get("/api/dashboard", response_model=schemas.DashboardData)
def get_dashboard(db: Session = Depends(get_db)) -> schemas.DashboardData:
    return crud.dashboard(db)


@app.get("/api/jobs", response_model=schemas.JobListResponse)
def list_jobs(
    keyword: str | None = None,
    location: str | None = None,
    arrangement: str | None = None,
    employment_type: str | None = None,
    experience_level: str | None = None,
    minimum_salary: float | None = None,
    date_posted: int | None = None,
    company_id: int | None = None,
    source: str | None = None,
    skills: str | None = None,
    sort: str | None = "match",
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
) -> schemas.JobListResponse:
    return crud.list_jobs(db, locals())


@app.get("/api/jobs/{job_id}", response_model=schemas.JobRead)
def retrieve_job(job_id: int, db: Session = Depends(get_db)) -> schemas.JobRead:
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return crud.job_to_read(job)


@app.post("/api/jobs/{job_id}/save", response_model=schemas.SavedJobRead, status_code=201)
def save_job(job_id: int, db: Session = Depends(get_db)) -> schemas.SavedJobRead:
    if not crud.get_job(db, job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return crud.saved_to_read(crud.save_job(db, job_id))


@app.delete("/api/jobs/{job_id}/save", status_code=204, response_class=Response)
def unsave_job(job_id: int, db: Session = Depends(get_db)) -> Response:
    crud.unsave_job(db, job_id)
    return Response(status_code=204)


@app.post("/api/jobs/{job_id}/archive", response_model=schemas.JobRead)
def archive_job(job_id: int, db: Session = Depends(get_db)) -> schemas.JobRead:
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return crud.job_to_read(crud.archive_job(db, job))


@app.post("/api/jobs/{job_id}/apply", response_model=schemas.ApplicationRead, status_code=201)
def apply_to_job(job_id: int, db: Session = Depends(get_db)) -> schemas.ApplicationRead:
    if not crud.get_job(db, job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return crud.application_to_read(crud.mark_applied(db, job_id))


@app.get("/api/companies", response_model=list[schemas.CompanyRead])
def list_companies(db: Session = Depends(get_db)) -> list[models.Company]:
    return crud.list_companies(db)


@app.post("/api/companies", response_model=schemas.CompanyRead, status_code=201)
def create_company(payload: schemas.CompanyCreate, db: Session = Depends(get_db)) -> models.Company:
    return crud.create_company(db, payload)


@app.patch("/api/companies/{company_id}", response_model=schemas.CompanyRead)
def update_company(company_id: int, payload: schemas.CompanyUpdate, db: Session = Depends(get_db)) -> models.Company:
    company = db.get(models.Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return crud.update_company(db, company, payload)


@app.delete("/api/companies/{company_id}", status_code=204, response_class=Response)
def delete_company(company_id: int, db: Session = Depends(get_db)) -> Response:
    company = db.get(models.Company, company_id)
    if company:
        db.delete(company)
        db.commit()
    return Response(status_code=204)


@app.post("/api/companies/{company_id}/scrape", response_model=schemas.ScrapeRunRead, status_code=201)
def scrape_company(company_id: int, db: Session = Depends(get_db)) -> schemas.ScrapeRunRead:
    company = db.get(models.Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return crud.scrape_run_to_read(run_scrape(db, company))


@app.get("/api/companies/{company_id}/scrapes", response_model=list[schemas.ScrapeRunRead])
def company_history(company_id: int, db: Session = Depends(get_db)) -> list[schemas.ScrapeRunRead]:
    runs = db.scalars(select(models.ScrapeRun).where(models.ScrapeRun.company_id == company_id).options(joinedload(models.ScrapeRun.company)).order_by(models.ScrapeRun.created_at.desc())).all()
    return [crud.scrape_run_to_read(run) for run in runs]


@app.get("/api/scraping/runs", response_model=list[schemas.ScrapeRunRead])
def list_scrape_runs(db: Session = Depends(get_db)) -> list[schemas.ScrapeRunRead]:
    return crud.list_scrape_runs(db)


@app.post("/api/scraping/runs", response_model=schemas.ScrapeRunRead, status_code=201)
def start_scrape(payload: schemas.StartScrapeRequest, db: Session = Depends(get_db)) -> schemas.ScrapeRunRead:
    company = db.get(models.Company, payload.company_id) if payload.company_id else db.scalars(select(models.Company).where(models.Company.monitoring_enabled.is_(True)).limit(1)).first()
    if not company:
        raise HTTPException(status_code=404, detail="No company available to scrape")
    return crud.scrape_run_to_read(run_scrape(db, company))


@app.get("/api/scraping/runs/{run_id}", response_model=schemas.ScrapeRunRead)
def get_scrape_run(run_id: int, db: Session = Depends(get_db)) -> schemas.ScrapeRunRead:
    run = db.scalars(select(models.ScrapeRun).where(models.ScrapeRun.id == run_id).options(joinedload(models.ScrapeRun.company))).first()
    if not run:
        raise HTTPException(status_code=404, detail="Scrape run not found")
    return crud.scrape_run_to_read(run)


@app.get("/api/scraping/runs/{run_id}/logs", response_model=list[schemas.ScrapeLogRead])
def get_scrape_logs(run_id: int, db: Session = Depends(get_db)) -> list[models.ScrapeLog]:
    return list(db.scalars(select(models.ScrapeLog).where(models.ScrapeLog.scrape_run_id == run_id).order_by(models.ScrapeLog.created_at.asc())).all())


@app.post("/api/scraping/runs/{run_id}/retry", response_model=schemas.ScrapeRunRead)
def retry_scrape(run_id: int, db: Session = Depends(get_db)) -> schemas.ScrapeRunRead:
    original = db.get(models.ScrapeRun, run_id)
    if not original or not original.company_id:
        raise HTTPException(status_code=404, detail="Scrape run not found")
    company = db.get(models.Company, original.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return crud.scrape_run_to_read(run_scrape(db, company, retry_count=original.retry_count + 1))


@app.post("/api/scraping/runs/{run_id}/cancel", response_model=schemas.ScrapeRunRead)
def cancel_scrape(run_id: int, db: Session = Depends(get_db)) -> schemas.ScrapeRunRead:
    run = db.scalars(select(models.ScrapeRun).where(models.ScrapeRun.id == run_id).options(joinedload(models.ScrapeRun.company))).first()
    if not run:
        raise HTTPException(status_code=404, detail="Scrape run not found")
    run.cancellation_requested = True
    if run.status == "running":
        run.status = "cancelled"
    db.commit()
    db.refresh(run)
    return crud.scrape_run_to_read(run)


@app.get("/api/scraping/runs/{run_id}/failed-urls")
def failed_urls(run_id: int, db: Session = Depends(get_db)) -> list[str]:
    return list(db.scalars(select(models.ScrapeLog.url).where(models.ScrapeLog.scrape_run_id == run_id, models.ScrapeLog.level == "error", models.ScrapeLog.url.is_not(None))).all())


@app.get("/api/scraping/runs/{run_id}/download")
def download_run_results(run_id: int, db: Session = Depends(get_db)) -> FileResponse:
    run = db.get(models.ScrapeRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scrape run not found")
    export = crud.create_export(db, schemas.ExportCreate(dataset=f"scrape-run-{run_id}", format="csv"))
    if not export.file_path:
        raise HTTPException(status_code=500, detail="Export failed")
    return FileResponse(export.file_path, filename=Path(export.file_path).name)


@app.get("/api/review", response_model=list[schemas.ReviewRecordRead])
def list_reviews(status: str = Query(default="pending"), db: Session = Depends(get_db)) -> list[models.ReviewRecord]:
    stmt = select(models.ReviewRecord).order_by(models.ReviewRecord.created_at.desc())
    if status:
        stmt = stmt.where(models.ReviewRecord.status == status)
    return list(db.scalars(stmt).all())


@app.get("/api/review/{review_id}", response_model=schemas.ReviewRecordRead)
def get_review(review_id: int, db: Session = Depends(get_db)) -> models.ReviewRecord:
    review = db.get(models.ReviewRecord, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found")
    return review


@app.post("/api/review/{review_id}/approve", response_model=schemas.ReviewRecordRead)
def approve_review(review_id: int, payload: schemas.ReviewAction, db: Session = Depends(get_db)) -> models.ReviewRecord:
    review = db.get(models.ReviewRecord, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found")
    return crud.approve_review(db, review, payload.extracted_data)


@app.post("/api/review/{review_id}/reject", response_model=schemas.ReviewRecordRead)
def reject_review(review_id: int, payload: schemas.ReviewAction, db: Session = Depends(get_db)) -> models.ReviewRecord:
    review = db.get(models.ReviewRecord, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found")
    return crud.reject_review(db, review, "rejected", payload.reviewer_notes)


@app.post("/api/review/{review_id}/duplicate", response_model=schemas.ReviewRecordRead)
def mark_duplicate(review_id: int, payload: schemas.ReviewAction, db: Session = Depends(get_db)) -> models.ReviewRecord:
    review = db.get(models.ReviewRecord, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found")
    return crud.reject_review(db, review, "duplicate", payload.reviewer_notes)


@app.post("/api/review/{review_id}/rerun", response_model=schemas.ReviewRecordRead)
def rerun_extraction(review_id: int, db: Session = Depends(get_db)) -> models.ReviewRecord:
    review = db.get(models.ReviewRecord, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found")
    review.reviewer_notes = "Extraction rerun requested; deterministic parser returned the same fields."
    db.commit()
    return review


@app.get("/api/saved-jobs", response_model=list[schemas.SavedJobRead])
def list_saved_jobs(db: Session = Depends(get_db)) -> list[schemas.SavedJobRead]:
    saved = db.scalars(select(models.SavedJob).options(joinedload(models.SavedJob.job).joinedload(models.Job.company), joinedload(models.SavedJob.job).joinedload(models.Job.saved)).order_by(models.SavedJob.saved_at.desc())).unique().all()
    return [crud.saved_to_read(item) for item in saved]


@app.post("/api/saved-jobs/{job_id}", response_model=schemas.SavedJobRead, status_code=201)
def save_from_saved_page(job_id: int, db: Session = Depends(get_db)) -> schemas.SavedJobRead:
    return save_job(job_id, db)


@app.delete("/api/saved-jobs/{job_id}", status_code=204, response_class=Response)
def unsave_from_saved_page(job_id: int, db: Session = Depends(get_db)) -> Response:
    crud.unsave_job(db, job_id)
    return Response(status_code=204)


@app.get("/api/applications", response_model=list[schemas.ApplicationRead])
def list_applications(db: Session = Depends(get_db)) -> list[schemas.ApplicationRead]:
    applications = db.scalars(select(models.Application).options(joinedload(models.Application.job).joinedload(models.Job.company), joinedload(models.Application.job).joinedload(models.Job.saved)).order_by(models.Application.updated_at.desc())).unique().all()
    return [crud.application_to_read(item) for item in applications]


@app.post("/api/applications", response_model=schemas.ApplicationRead, status_code=201)
def create_application(payload: dict[str, Any], db: Session = Depends(get_db)) -> schemas.ApplicationRead:
    job_id = int(payload["job_id"])
    return crud.application_to_read(crud.mark_applied(db, job_id))


@app.patch("/api/applications/{application_id}", response_model=schemas.ApplicationRead)
def update_application(application_id: int, payload: schemas.ApplicationUpdate, db: Session = Depends(get_db)) -> schemas.ApplicationRead:
    application = db.scalars(select(models.Application).where(models.Application.id == application_id).options(joinedload(models.Application.job).joinedload(models.Job.company), joinedload(models.Application.job).joinedload(models.Job.saved))).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(application, key, value)
    db.commit()
    db.refresh(application)
    return crud.application_to_read(application)


@app.delete("/api/applications/{application_id}", status_code=204, response_class=Response)
def delete_application(application_id: int, db: Session = Depends(get_db)) -> Response:
    application = db.get(models.Application, application_id)
    if application:
        db.delete(application)
        db.commit()
    return Response(status_code=204)


@app.get("/api/exports", response_model=list[schemas.ExportRecordRead])
def list_exports(db: Session = Depends(get_db)) -> list[models.ExportRecord]:
    return list(db.scalars(select(models.ExportRecord).order_by(models.ExportRecord.created_at.desc())).all())


@app.post("/api/exports", response_model=schemas.ExportRecordRead, status_code=201)
def create_export(payload: schemas.ExportCreate, db: Session = Depends(get_db)) -> models.ExportRecord:
    return crud.create_export(db, payload)


@app.get("/api/exports/{export_id}/download")
def download_export(export_id: int, db: Session = Depends(get_db)) -> FileResponse:
    export = db.get(models.ExportRecord, export_id)
    if not export or not export.file_path or not Path(export.file_path).exists():
        raise HTTPException(status_code=404, detail="Export file not found")
    return FileResponse(export.file_path, filename=Path(export.file_path).name)


@app.get("/api/settings", response_model=schemas.UserSettingsRead)
def get_settings(db: Session = Depends(get_db)) -> models.UserSettings:
    return crud.get_settings(db)


@app.patch("/api/settings", response_model=schemas.UserSettingsRead)
def update_settings(payload: schemas.UserSettingsUpdate, db: Session = Depends(get_db)) -> models.UserSettings:
    settings = crud.get_settings(db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    jobs = db.scalars(select(models.Job).options(joinedload(models.Job.company))).all()
    for job in jobs:
        score, explanation = score_job(job, settings)
        job.match_score = score
        job.raw_data = {**(job.raw_data or {}), "match_explanation": explanation}
    db.commit()
    return settings


@app.get("/api/settings/integrations", response_model=schemas.IntegrationStatus)
def integrations() -> schemas.IntegrationStatus:
    return schemas.IntegrationStatus(
        openrouter="configured" if os.getenv("OPENROUTER_API_KEY") else "not_configured",
        apify="configured" if os.getenv("APIFY_API_TOKEN") else "not_configured",
        google_sheets="configured" if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") else "not_configured",
    )
