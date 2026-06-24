from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

SKILLS = [
    "python",
    "typescript",
    "react",
    "next.js",
    "sql",
    "postgresql",
    "aws",
    "docker",
    "kubernetes",
    "fastapi",
    "machine learning",
    "nlp",
    "analytics",
    "etl",
    "celery",
    "redis",
    "beautifulsoup",
    "playwright",
]


def clean_text(value: str | None) -> str | None:
    if not value:
        return None
    text = BeautifulSoup(value, "html.parser").get_text(" ")
    text = unescape(re.sub(r"\s+", " ", text)).strip()
    return text or None


def html_to_text(value: str | None) -> str | None:
    return clean_text(value)


def parse_salary(value: str | None) -> tuple[float | None, float | None, str | None]:
    if not value:
        return None, None, None
    text = value.lower().replace(",", "")
    currency = None
    if "$" in text or "usd" in text:
        currency = "USD"
    elif "eur" in text or "€" in text:
        currency = "EUR"
    elif "gbp" in text or "£" in text:
        currency = "GBP"
    numbers = []
    for raw, suffix in re.findall(r"(\d+(?:\.\d+)?)\s*(k)?", text):
        number = float(raw)
        if suffix == "k" or number < 1000:
            number *= 1000
        numbers.append(number)
    if not numbers:
        return None, None, currency
    if len(numbers) == 1:
        return numbers[0], numbers[0], currency
    return min(numbers[:2]), max(numbers[:2]), currency


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().isdigit() and len(value.strip()) >= 10):
        raw = float(value)
        if raw > 10_000_000_000:
            raw /= 1000
        try:
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None
    try:
        parsed = date_parser.parse(str(value), fuzzy=True)
    except (ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def normalize_location(value: str | None) -> tuple[str | None, bool]:
    if not value:
        return None, False
    text = clean_text(value) or ""
    lowered = text.lower()
    ambiguous = lowered in {"usa", "united states", "multiple", "various", "global", "remote or hybrid"} or "/" in text
    replacements = {
        "sf": "San Francisco, CA",
        "nyc": "New York, NY",
        "remote - us": "Remote, US",
        "remote us": "Remote, US",
    }
    normalized = replacements.get(lowered, text)
    return normalized, ambiguous


def detect_work_arrangement(location: str | None, text: str | None = None) -> str | None:
    haystack = f"{location or ''} {text or ''}".lower()
    if "remote" in haystack:
        return "remote"
    if "hybrid" in haystack:
        return "hybrid"
    if "on-site" in haystack or "onsite" in haystack or "office" in haystack:
        return "on_site"
    return None


def normalize_employment_type(value: str | None) -> str | None:
    if not value:
        return None
    text = value.lower()
    if "contract" in text:
        return "contract"
    if "intern" in text:
        return "internship"
    if "part" in text:
        return "part_time"
    if "full" in text or "permanent" in text:
        return "full_time"
    return None


def infer_experience(title: str | None, description: str | None = None) -> str | None:
    text = f"{title or ''} {description or ''}".lower()
    if any(word in text for word in ["senior", "staff", "principal", "lead"]):
        return "senior"
    if any(word in text for word in ["intern", "junior", "entry"]):
        return "entry"
    if any(word in text for word in ["manager", "director"]):
        return "lead"
    return "mid"


def extract_skills(*values: str | None) -> list[str]:
    text = " ".join(value or "" for value in values).lower()
    found = [skill for skill in SKILLS if skill in text]
    return sorted(set(found))


def normalize_url(url: str | None, base_url: str | None = None) -> str | None:
    if not url:
        return None
    absolute = urljoin(base_url or "", url)
    parsed = urlparse(absolute)
    if not parsed.scheme or not parsed.netloc:
        return absolute if absolute.startswith("fixture://") else None
    return parsed._replace(fragment="").geturl()


def content_hash(record: dict) -> str:
    payload = "|".join(
        str(record.get(key) or "").strip().lower()
        for key in ["title", "company_id", "location", "application_url", "description", "requirements"]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_record(raw: dict, company_id: int, source_type: str, base_url: str | None = None) -> tuple[dict, dict]:
    title = clean_text(raw.get("title"))
    description = clean_text(raw.get("description"))
    requirements = clean_text(raw.get("requirements"))
    location, ambiguous_location = normalize_location(raw.get("location"))
    salary_min, salary_max, currency = parse_salary(raw.get("salary_text") or raw.get("salary") or raw.get("compensation"))
    posted_at = parse_date(raw.get("posted_at") or raw.get("date"))
    application_url = normalize_url(raw.get("application_url") or raw.get("apply_url") or raw.get("url"), base_url)
    work_arrangement = raw.get("work_arrangement") or detect_work_arrangement(location, f"{title} {description}")
    employment_type = normalize_employment_type(raw.get("employment_type") or raw.get("type")) or "full_time"
    experience_level = raw.get("experience_level") or infer_experience(title, description)
    skills = raw.get("skills") or extract_skills(title, description, requirements)
    normalized = {
        "external_id": raw.get("external_id") or raw.get("id"),
        "title": title,
        "company_id": company_id,
        "location": location,
        "work_arrangement": work_arrangement,
        "salary_text": clean_text(raw.get("salary_text") or raw.get("salary") or raw.get("compensation")),
        "salary_min": salary_min,
        "salary_max": salary_max,
        "currency": currency,
        "employment_type": employment_type,
        "experience_level": experience_level,
        "description": description,
        "requirements": requirements,
        "application_url": application_url,
        "source_url": normalize_url(raw.get("source_url") or raw.get("posting_url") or raw.get("url"), base_url),
        "source_type": source_type,
        "skills": skills,
        "posted_at": posted_at,
        "raw_data": raw,
    }
    meta = {
        "ambiguous_location": ambiguous_location,
        "invalid_date": bool((raw.get("posted_at") or raw.get("date")) and posted_at is None),
    }
    normalized["content_hash"] = content_hash(normalized)
    return normalized, meta
