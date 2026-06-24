from __future__ import annotations

from sqlalchemy import select

from app import models
from app.scrapers.adapters import AshbyAdapter, DetailPageFixtureAdapter, GenericHtmlAdapter, GreenhouseAdapter, JavaScriptRenderedAdapter, LeverAdapter, PaginatedFixtureAdapter, StaticHtmlAdapter
from app.services.scraping import run_scrape
from app.validation.rules import find_duplicate


def test_static_html_extraction(db_session) -> None:
    company = db_session.scalars(select(models.Company).where(models.Company.name == "Northstar Systems")).one()
    result = StaticHtmlAdapter().extract
    import asyncio

    extracted = asyncio.run(result(company))
    assert extracted.records
    assert extracted.records[0]["title"] == "Senior Data Engineer"


def test_multi_page_extraction(db_session) -> None:
    company = db_session.scalars(select(models.Company).where(models.Company.name == "Lumen Cloud")).one()
    import asyncio

    extracted = asyncio.run(PaginatedFixtureAdapter().extract(company))
    assert extracted.pages_processed == 2
    assert len(extracted.records) == 2


def test_javascript_rendered_extraction(db_session) -> None:
    company = db_session.scalars(select(models.Company).where(models.Company.name == "BrightTable")).one()
    import asyncio

    extracted = asyncio.run(JavaScriptRenderedAdapter().extract(company))
    assert extracted.records[0]["external_id"] == "BT-401"


def test_greenhouse_adapter_parses_fixture_json() -> None:
    import asyncio

    company = models.Company(name="Greenhouse Fixture", website="https://example.com", career_url="fixture://greenhouse", source_type="greenhouse", extraction_method="greenhouse")
    extracted = asyncio.run(GreenhouseAdapter().extract(company))
    assert extracted.records[0]["external_id"] == "501001"
    assert extracted.records[0]["application_url"].startswith("https://boards.greenhouse.io/")
    assert extracted.records[0]["salary_text"] == "$160,000 - $190,000 USD"


def test_lever_adapter_parses_fixture_json() -> None:
    import asyncio

    company = models.Company(name="Lever Fixture", website="https://example.com", career_url="fixture://lever", source_type="lever", extraction_method="lever")
    extracted = asyncio.run(LeverAdapter().extract(company))
    assert extracted.records[0]["external_id"] == "lever-201"
    assert "TypeScript" in extracted.records[0]["description"]
    assert extracted.records[1]["employment_type"] == "Contract"


def test_ashby_adapter_parses_fixture_json() -> None:
    import asyncio

    company = models.Company(name="Ashby Fixture", website="https://example.com", career_url="fixture://ashby", source_type="ashby", extraction_method="ashby")
    extracted = asyncio.run(AshbyAdapter().extract(company))
    assert extracted.records[0]["external_id"] == "ashby-301"
    assert extracted.records[0]["location"] == "Remote, US"
    assert extracted.records[0]["salary_text"] == "$150k - $185k"


def test_generic_html_adapter_parses_static_fixture() -> None:
    import asyncio

    company = models.Company(name="Static Fixture", website="https://example.com", career_url="fixture://static-realistic", source_type="generic/html", extraction_method="generic_html")
    extracted = asyncio.run(GenericHtmlAdapter().extract(company))
    assert extracted.pages_processed == 1
    assert len(extracted.records) == 2
    assert extracted.records[0]["title"] == "Full Stack Scraping Engineer"
    assert extracted.records[1]["application_url"].endswith("/jobs/static-702/apply")


def test_review_queue_creation(db_session) -> None:
    company = db_session.scalars(select(models.Company).where(models.Company.name == "QuietPath Labs")).one()
    run = run_scrape(db_session, company)
    assert run.review_records >= 1
    assert db_session.scalars(select(models.ReviewRecord).where(models.ReviewRecord.status == "pending")).first()


def test_duplicate_detection(db_session) -> None:
    job = db_session.scalars(select(models.Job).limit(1)).one()
    duplicate = find_duplicate(db_session, {"external_id": job.external_id, "application_url": job.application_url, "content_hash": job.content_hash, "company_id": job.company_id, "title": job.title})
    assert duplicate and duplicate.id == job.id


def test_integration_scrape_api(client) -> None:
    companies = client.get("/api/companies").json()
    quietpath = next(company for company in companies if company["name"] == "QuietPath Labs")
    response = client.post(f"/api/companies/{quietpath['id']}/scrape")
    assert response.status_code == 201
    assert response.json()["records_extracted"] >= 2
    jobs = client.get("/api/jobs", params={"keyword": "Backend"}).json()
    assert jobs["total"] >= 1


def test_job_search_filters(client) -> None:
    response = client.get("/api/jobs", params={"arrangement": "remote", "minimum_salary": 120000})
    assert response.status_code == 200
    assert response.json()["items"]


def test_export_generation(client) -> None:
    response = client.post("/api/exports", json={"dataset": "jobs", "format": "xlsx"})
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["record_count"] > 0


def test_export_default_columns(client) -> None:
    from pathlib import Path

    response = client.post("/api/exports", json={"dataset": "jobs", "format": "csv"})
    assert response.status_code == 201
    payload = response.json()
    header = Path(payload["file_path"]).read_text(encoding="utf-8").splitlines()[0].split(",")
    assert header == [
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


def test_saved_jobs_endpoint(client) -> None:
    response = client.get("/api/saved-jobs")
    assert response.status_code == 200
    assert response.json()
