from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app import models

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures"
CAREERS_FIXTURE_DIR = FIXTURE_ROOT / "careers"
ATS_FIXTURE_DIR = FIXTURE_ROOT / "ats"
USER_AGENT = "JobScoutAI/1.0 portfolio demo (+https://github.com/portfolio-project)"


@dataclass
class ScrapeResult:
    records: list[dict]
    pages_discovered: int
    pages_processed: int
    failed_pages: int = 0


class ScraperAdapter(Protocol):
    async def extract(self, company: models.Company) -> ScrapeResult:
        ...


def fixture_path(url: str) -> Path:
    name = url.replace("fixture://", "")
    mapping = {
        "static": "static.html",
        "static-realistic": "static_realistic.html",
        "paginated-1": "paginated-1.html",
        "paginated-2": "paginated-2.html",
        "detail-list": "detail-list.html",
        "detail-301": "detail-301.html",
        "detail-302": "detail-302.html",
        "javascript": "javascript.html",
        "greenhouse": "greenhouse_jobs.json",
        "greenhouse_jobs": "greenhouse_jobs.json",
        "lever": "lever_postings.json",
        "lever_postings": "lever_postings.json",
        "ashby": "ashby_jobs.json",
        "ashby_jobs": "ashby_jobs.json",
    }
    filename = mapping.get(name, name)
    if filename.endswith(".json"):
        return ATS_FIXTURE_DIR / filename
    return CAREERS_FIXTURE_DIR / filename


async def read_source(url: str, timeout: int = 20) -> str:
    if url.startswith("fixture://"):
        return fixture_path(url).read_text(encoding="utf-8")
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json"}) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def read_json_source(url: str, timeout: int = 20) -> dict | list:
    if url.startswith("fixture://"):
        return json.loads(fixture_path(url).read_text(encoding="utf-8"))
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


def first_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("name", "value", "plain", "text", "label"):
            if value.get(key):
                return str(value[key])
    if isinstance(value, list):
        parts = [first_text(item) for item in value]
        return ", ".join(part for part in parts if part) or None
    return str(value)


def greenhouse_endpoint(company: models.Company) -> str:
    token = (company.selector_config or {}).get("board_token")
    if token:
        return f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    if company.career_url.startswith("fixture://"):
        return company.career_url
    if company.career_url.startswith(("fixture://", "http://", "https://")) and "boards-api.greenhouse.io" in company.career_url:
        return company.career_url
    return f"https://boards-api.greenhouse.io/v1/boards/{company.career_url.rstrip('/').split('/')[-1]}/jobs?content=true"


def lever_endpoint(company: models.Company) -> str:
    site = (company.selector_config or {}).get("site")
    if site:
        return f"https://api.lever.co/v0/postings/{site}?mode=json"
    if company.career_url.startswith("fixture://"):
        return company.career_url
    if company.career_url.startswith(("fixture://", "http://", "https://")) and "api.lever.co" in company.career_url:
        return company.career_url
    return f"https://api.lever.co/v0/postings/{company.career_url.rstrip('/').split('/')[-1]}?mode=json"


def ashby_endpoint(company: models.Company) -> str:
    board = (company.selector_config or {}).get("job_board_name")
    if board:
        return f"https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true"
    if company.career_url.startswith("fixture://"):
        return company.career_url
    if company.career_url.startswith(("fixture://", "http://", "https://")) and "api.ashbyhq.com" in company.career_url:
        return company.career_url
    return f"https://api.ashbyhq.com/posting-api/job-board/{company.career_url.rstrip('/').split('/')[-1]}?includeCompensation=true"


def parse_greenhouse_jobs(payload: dict | list, source_url: str) -> list[dict]:
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else payload
    records: list[dict] = []
    for job in jobs:
        metadata = {item.get("name"): item.get("value") for item in job.get("metadata", []) if isinstance(item, dict)}
        salary_text = first_text(metadata.get("Salary") or metadata.get("Compensation") or metadata.get("Pay Range"))
        location = first_text(job.get("location"))
        if not location:
            location = first_text(job.get("offices"))
        records.append(
            {
                "external_id": str(job.get("id")) if job.get("id") is not None else None,
                "title": job.get("title"),
                "location": location,
                "department": first_text(job.get("departments")),
                "employment_type": first_text(metadata.get("Employment Type") or metadata.get("Commitment")),
                "salary_text": salary_text,
                "description": job.get("content"),
                "application_url": job.get("absolute_url") or job.get("url"),
                "source_url": job.get("absolute_url") or source_url,
                "updated_at": job.get("updated_at"),
                "raw_data": job,
            }
        )
    return records


def parse_lever_postings(payload: dict | list, source_url: str) -> list[dict]:
    postings = payload.get("postings", []) if isinstance(payload, dict) else payload
    records: list[dict] = []
    for posting in postings:
        categories = posting.get("categories") or {}
        list_content = " ".join(item.get("content") or "" for item in posting.get("lists", []) if isinstance(item, dict))
        description = "\n".join(part for part in [posting.get("description"), list_content] if part)
        created_at = posting.get("createdAt")
        posted_at = str(created_at) if created_at else None
        records.append(
            {
                "external_id": posting.get("id"),
                "title": posting.get("text"),
                "location": categories.get("location"),
                "department": categories.get("team") or categories.get("department"),
                "employment_type": categories.get("commitment"),
                "description": description,
                "application_url": posting.get("applyUrl") or posting.get("hostedUrl"),
                "source_url": posting.get("hostedUrl") or source_url,
                "posted_at": posted_at,
                "raw_data": posting,
            }
        )
    return records


def parse_ashby_jobs(payload: dict | list, source_url: str) -> list[dict]:
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else payload
    records: list[dict] = []
    for job in jobs:
        compensation = job.get("compensation") or {}
        salary_text = (
            compensation.get("compensationTierSummary")
            or compensation.get("summary")
            or job.get("compensationTierSummary")
            or job.get("salary")
        )
        if not salary_text and compensation.get("minSalary") and compensation.get("maxSalary"):
            salary_text = f"{compensation.get('currencyCode') or ''} {compensation['minSalary']} - {compensation['maxSalary']}".strip()
        location = first_text(job.get("location"))
        records.append(
            {
                "external_id": job.get("id") or job.get("jobId"),
                "title": job.get("title"),
                "location": location,
                "department": first_text(job.get("department")),
                "employment_type": job.get("employmentType"),
                "salary_text": salary_text,
                "description": job.get("descriptionHtml") or job.get("descriptionPlain") or job.get("description"),
                "application_url": job.get("applyUrl") or job.get("jobUrl"),
                "source_url": job.get("jobUrl") or source_url,
                "posted_at": job.get("publishedAt") or job.get("postedAt"),
                "updated_at": job.get("updatedAt"),
                "raw_data": job,
            }
        )
    return records


def parse_job_article(article: BeautifulSoup, source_url: str) -> dict:
    def text(selector: str) -> str | None:
        node = article.select_one(selector)
        return node.get_text(" ", strip=True) if node else None

    apply = article.select_one(".apply, a[href]")
    return {
        "external_id": article.get("data-id"),
        "title": text(".title, h1, h2"),
        "location": text(".location"),
        "department": text(".department"),
        "salary_text": text(".salary"),
        "employment_type": text(".type"),
        "posted_at": text("time, .date"),
        "application_url": apply.get("href") if apply else None,
        "source_url": source_url,
        "description": text(".description, p, section"),
    }


def parse_articles(html: str, source_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    return [parse_job_article(article, source_url) for article in soup.select(".job, article")]


def parse_generic_html(html: str, source_url: str, config: dict | None = None) -> tuple[list[dict], list[str]]:
    config = config or {}
    soup = BeautifulSoup(html, "html.parser")
    row_selector = config.get("row") or config.get("card") or ".job, article, [data-job-id]"
    fields = config.get("fields") or {}
    fallback_fields = {
        "external_id": "[data-id], [data-job-id]",
        "title": ".title, h1, h2, h3, [data-field='title']",
        "location": ".location, [data-field='location']",
        "department": ".department, [data-field='department']",
        "employment_type": ".type, .employment-type, [data-field='employment_type']",
        "salary_text": ".salary, .compensation, [data-field='salary']",
        "posted_at": "time, .date, [data-field='posted_at']",
        "description": ".description, [data-field='description'], p",
        "application_url": ".apply[href], a[href*='apply'], a[href]",
        "source_url": "a[href]",
    }
    records: list[dict] = []
    for row in soup.select(row_selector):
        record: dict = {}
        for field, selector in {**fallback_fields, **fields}.items():
            node = row.select_one(selector)
            if not node:
                continue
            if field == "external_id":
                record[field] = node.get("data-id") or node.get("data-job-id") or node.get_text(" ", strip=True)
            elif field.endswith("url"):
                href = node.get("href")
                record[field] = urljoin(source_url, href) if href else node.get_text(" ", strip=True)
            else:
                record[field] = node.get("datetime") if node.name == "time" and node.get("datetime") else node.get_text(" ", strip=True)
        if row.get("data-id") or row.get("data-job-id"):
            record.setdefault("external_id", row.get("data-id") or row.get("data-job-id"))
        record.setdefault("source_url", source_url)
        records.append(record or parse_job_article(row, source_url))
    pagination_selector = config.get("next") or config.get("pagination_next") or "a.next[href], a[rel='next'][href]"
    next_urls = [urljoin(source_url, node["href"]) for node in soup.select(pagination_selector) if node.get("href")]
    return records, next_urls


class StaticHtmlAdapter:
    async def extract(self, company: models.Company) -> ScrapeResult:
        html = await read_source(company.career_url)
        return ScrapeResult(records=parse_articles(html, company.career_url), pages_discovered=1, pages_processed=1)


class GenericSelectorAdapter:
    async def extract(self, company: models.Company) -> ScrapeResult:
        config = company.selector_config or {}
        max_pages = int(config.get("max_pages") or 3)
        urls = [company.career_url]
        seen: set[str] = set()
        records: list[dict] = []
        processed = 0
        failed = 0
        while urls and processed < max_pages:
            url = urls.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                html = await read_source(url)
                page_records, next_urls = parse_generic_html(html, url, config)
                records.extend(page_records)
                urls.extend(next_url for next_url in next_urls if next_url not in seen)
                processed += 1
            except httpx.HTTPError:
                failed += 1
                processed += 1
        return ScrapeResult(records=records, pages_discovered=len(seen) + len(urls), pages_processed=processed, failed_pages=failed)


GenericHtmlAdapter = GenericSelectorAdapter


class PaginatedFixtureAdapter:
    async def extract(self, company: models.Company) -> ScrapeResult:
        urls = [company.career_url]
        records: list[dict] = []
        processed = 0
        while urls:
            url = urls.pop(0)
            html = await read_source(url)
            processed += 1
            records.extend(parse_articles(html, url))
            soup = BeautifulSoup(html, "html.parser")
            next_link = soup.select_one("a.next")
            if next_link and next_link.get("href"):
                urls.append(next_link["href"])
        return ScrapeResult(records=records, pages_discovered=processed, pages_processed=processed)


class DetailPageFixtureAdapter:
    async def extract(self, company: models.Company) -> ScrapeResult:
        list_html = await read_source(company.career_url)
        soup = BeautifulSoup(list_html, "html.parser")
        links = [node["href"] for node in soup.select("a.job-link[href]")]
        records = []
        for link in links:
            detail_html = await read_source(link)
            records.extend(parse_articles(detail_html, link))
        return ScrapeResult(records=records, pages_discovered=1 + len(links), pages_processed=1 + len(links))


class JavaScriptRenderedAdapter:
    async def extract(self, company: models.Company) -> ScrapeResult:
        html = await read_source(company.career_url)
        soup = BeautifulSoup(html, "html.parser")
        payload = soup.select_one("#job-data")
        records = json.loads(payload.get_text()) if payload else []
        for record in records:
            record.setdefault("source_url", company.career_url)
        return ScrapeResult(records=records, pages_discovered=1, pages_processed=1)


class GreenhouseAdapter:
    async def extract(self, company: models.Company) -> ScrapeResult:
        url = greenhouse_endpoint(company)
        payload = await read_json_source(url)
        return ScrapeResult(records=parse_greenhouse_jobs(payload, url), pages_discovered=1, pages_processed=1)


class LeverAdapter:
    async def extract(self, company: models.Company) -> ScrapeResult:
        url = lever_endpoint(company)
        payload = await read_json_source(url)
        return ScrapeResult(records=parse_lever_postings(payload, url), pages_discovered=1, pages_processed=1)


class AshbyAdapter:
    async def extract(self, company: models.Company) -> ScrapeResult:
        url = ashby_endpoint(company)
        payload = await read_json_source(url)
        return ScrapeResult(records=parse_ashby_jobs(payload, url), pages_discovered=1, pages_processed=1)


class ApifyAdapter(StaticHtmlAdapter):
    pass


def get_adapter(company: models.Company) -> ScraperAdapter:
    method = company.extraction_method
    if method == "paginated_fixture":
        return PaginatedFixtureAdapter()
    if method == "detail_fixture":
        return DetailPageFixtureAdapter()
    if method == "playwright":
        return JavaScriptRenderedAdapter()
    if method == "greenhouse":
        return GreenhouseAdapter()
    if method == "lever":
        return LeverAdapter()
    if method == "ashby":
        return AshbyAdapter()
    if method == "generic":
        return GenericSelectorAdapter()
    if method == "generic_html":
        return GenericHtmlAdapter()
    if method == "apify":
        return ApifyAdapter()
    return StaticHtmlAdapter()


def extract_sync(company: models.Company) -> ScrapeResult:
    return asyncio.run(get_adapter(company).extract(company))
