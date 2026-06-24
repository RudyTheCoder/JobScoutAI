# JobScoutAI

JobScoutAI is a full-stack portfolio project for public job data extraction. It monitors configured career sources, extracts listings from supported public ATS APIs or static careers pages, normalizes the records into one schema, validates confidence, routes uncertain records to review, and exports clean job datasets as CSV, JSON, or XLSX.

```mermaid
flowchart LR
  UI["Next.js / React UI"] --> API["FastAPI REST API"]
  API --> DB["PostgreSQL"]
  API --> Redis["Redis"]
  Redis --> Worker["Celery worker"]
  API --> Scrapers["HTTPX + BeautifulSoup adapters"]
  Scrapers --> ATS["Greenhouse, Lever, Ashby public APIs"]
  Scrapers --> HTML["Static careers-page HTML"]
  API --> Review["Validation + review queue"]
  API --> Exports["Pandas CSV / JSON / XLSX exports"]
```

## What It Demonstrates

- Public ATS/API extraction for Greenhouse, Lever, and Ashby.
- Static HTML careers-page scraping with BeautifulSoup and configurable selectors.
- Normalization into one job schema: title, company, location, work arrangement, salary, employment type, experience level, source URLs, skills, timestamps, and raw data.
- Validation and duplicate detection using external IDs, application URLs, content hashes, and company/title checks.
- Scrape run metrics, logs, failed page counts, review records, and success rates.
- Human review workflow for duplicates, missing fields, invalid dates, ambiguous locations, and low-confidence records.
- CSV, JSON, and Excel exports with portfolio-friendly clean columns.

## Real vs Fixture Sources

Fixtures remain part of the project on purpose. They make tests deterministic and let the demo run without hitting public websites. Fixture companies use `fixture://...` URLs and read files from `backend/fixtures/`.

Real-source configurations are also seeded for demonstration:

- Tailscale via Greenhouse public Job Board API.
- PostHog via Ashby public Job Posting API.
- Supabase via Ashby public Job Posting API.
- Render via Ashby public Job Posting API.
- A static realistic careers-page fixture for Generic HTML scraping.

No LinkedIn, Indeed, Glassdoor, Google Careers, login-only pages, CAPTCHA bypassing, private APIs, or aggressive scraping are used.

## Supported Extraction Methods

- Greenhouse: `https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`
- Lever: `https://api.lever.co/v0/postings/{site}?mode=json`
- Ashby: `https://api.ashbyhq.com/posting-api/job-board/{job_board_name}?includeCompensation=true`
- Generic HTML: BeautifulSoup selectors for job cards, title, location, department, employment type, salary, posted date, description, apply URL, source URL, and simple pagination.

## Stack

Frontend: Next.js App Router, React, TypeScript, Tailwind CSS, Recharts, lucide-react.

Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis/Celery, HTTPX, BeautifulSoup, Pandas, openpyxl, pytest.

## Local Setup

```bash
pnpm install
docker compose up -d postgres redis
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg://job_scout:job_scout_password@localhost:55432/job_scout_ai alembic -c alembic.ini upgrade head
DATABASE_URL=postgresql+psycopg://job_scout:job_scout_password@localhost:55432/job_scout_ai python -m app.seed
DATABASE_URL=postgresql+psycopg://job_scout:job_scout_password@localhost:55432/job_scout_ai REDIS_URL=redis://localhost:6379/0 uvicorn app.main:app --reload
```

In a second backend terminal:

```bash
cd backend
source .venv/bin/activate
DATABASE_URL=postgresql+psycopg://job_scout:job_scout_password@localhost:55432/job_scout_ai REDIS_URL=redis://localhost:6379/0 celery -A app.tasks.celery_app worker --loglevel=info
```

In a frontend terminal:

```bash
pnpm dev
```

The frontend defaults to `http://localhost:8000` for the API. Override with `NEXT_PUBLIC_API_URL` if needed.

## Demo Flow

1. Start Docker Postgres and Redis: `docker compose up -d postgres redis`.
2. Run migrations and seed data from `backend/`.
3. Start FastAPI with `uvicorn app.main:app --reload`.
4. Start the Celery worker.
5. Start the frontend with `pnpm dev`.
6. Open Companies and run a fixture scrape first.
7. Run an approved real public ATS scrape only if you want to hit the public endpoint.
8. Open Scraping to inspect pages discovered, pages processed, extracted records, valid records, review records, invalid records, failed pages, status, success rate, and logs.
9. Open Review to approve, reject, or mark duplicate records.
10. Open Exports and generate CSV, JSON, or XLSX.

## Tests

Backend tests do not require live internet. They parse saved Greenhouse, Lever, Ashby, and static HTML samples.

```bash
cd backend
pytest
```

Frontend checks:

```bash
pnpm typecheck
pnpm build
```

## Ethical Scraping Notes

JobScoutAI is intentionally conservative:

- Prefer public JSON APIs when available.
- Keep request volume low.
- Send clear `User-Agent` headers and request timeouts.
- Skip sources that block requests or appear unsuitable.
- Do not bypass CAPTCHAs, login walls, paywalls, anti-bot systems, or private APIs.
- Do not scrape LinkedIn, Indeed, Glassdoor, or Google Careers.

## Generated Files

Exports are written to `backend/exports/` and ignored by git. Local secrets, virtual environments, build output, caches, screenshots, snapshots, and SQLite files are also ignored.
