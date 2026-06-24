from __future__ import annotations

from app.services.normalization import normalize_location, normalize_record, parse_date, parse_salary


def test_salary_normalization() -> None:
    assert parse_salary("$120k - $150k") == (120000, 150000, "USD")
    assert parse_salary("USD 95000") == (95000, 95000, "USD")


def test_date_parsing() -> None:
    assert parse_date("2026-06-10") is not None
    assert parse_date("not a date") is None
    assert parse_date("1781894400000") is not None


def test_location_normalization() -> None:
    assert normalize_location("Remote - US") == ("Remote, US", False)
    assert normalize_location("USA / Canada")[1] is True


def test_ats_record_normalization() -> None:
    record, meta = normalize_record(
        {
            "external_id": "ats-123",
            "title": "Senior Data Engineer",
            "location": "Remote - US",
            "employment_type": "Full-time",
            "salary_text": "$140k - $165k USD",
            "description": "<p>Build Python, SQL, FastAPI, and PostgreSQL data workflows.</p>",
            "application_url": "/jobs/ats-123/apply",
            "source_url": "https://jobs.example.com/ats-123",
            "posted_at": "2026-06-20T12:00:00Z",
        },
        company_id=99,
        source_type="greenhouse",
        base_url="https://jobs.example.com",
    )
    assert record["application_url"] == "https://jobs.example.com/jobs/ats-123/apply"
    assert record["work_arrangement"] == "remote"
    assert record["employment_type"] == "full_time"
    assert record["salary_min"] == 140000
    assert "fastapi" in record["skills"]
    assert meta["invalid_date"] is False
