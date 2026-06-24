export type HealthStatus = "healthy" | "warning" | "error" | "paused";
export type ScrapeStatus = "queued" | "running" | "completed" | "warning" | "failed" | "cancelled";
export type ReviewStatus = "pending" | "approved" | "rejected" | "duplicate";
export type ExportFormat = "csv" | "json" | "xlsx";
export type ExportStatus = "processing" | "completed" | "failed";
export type ApplicationStage = "wishlist" | "applied" | "interview" | "offer" | "rejected";

export interface Company {
  id: number;
  name: string;
  website: string;
  career_url: string;
  source_type: string;
  extraction_method: string;
  monitoring_enabled: boolean;
  scrape_frequency: string;
  health_status: HealthStatus;
  last_scrape_at: string | null;
  next_scrape_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: number;
  external_id: string | null;
  title: string;
  company_id: number;
  company_name: string;
  location: string | null;
  work_arrangement: string | null;
  salary_text: string | null;
  salary_min: number | null;
  salary_max: number | null;
  currency: string | null;
  employment_type: string | null;
  experience_level: string | null;
  description: string | null;
  requirements: string | null;
  application_url: string;
  source_url: string | null;
  source_type: string;
  skills: string[];
  posted_at: string | null;
  first_seen_at: string;
  last_seen_at: string;
  status: string;
  match_score: number;
  extraction_confidence: number;
  raw_data: Record<string, unknown>;
  is_saved?: boolean;
}

export interface ScrapeRun {
  id: number;
  company_id: number | null;
  company_name: string | null;
  status: ScrapeStatus;
  extraction_method: string;
  pages_discovered: number;
  pages_processed: number;
  records_extracted: number;
  valid_records: number;
  invalid_records: number;
  review_records: number;
  failed_pages: number;
  retry_count: number;
  success_rate: number;
  started_at: string | null;
  finished_at: string | null;
  duration: number | null;
  cancellation_requested: boolean;
  created_at: string;
}

export interface ScrapeLog {
  id: number;
  scrape_run_id: number;
  level: "info" | "warning" | "error";
  message: string;
  url: string | null;
  http_status: number | null;
  error_category: string | null;
  created_at: string;
}

export interface ReviewRecord {
  id: number;
  job_id: number | null;
  scrape_run_id: number | null;
  issue_type: string;
  confidence: number;
  extracted_data: Record<string, unknown>;
  source_evidence: string | null;
  status: ReviewStatus;
  reviewer_notes: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface SavedJob {
  id: number;
  job: Job;
  saved_at: string;
}

export interface Application {
  id: number;
  job: Job;
  stage: ApplicationStage;
  applied_at: string | null;
  next_action: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExportRecord {
  id: number;
  name: string;
  dataset: string;
  format: ExportFormat;
  record_count: number;
  status: ExportStatus;
  file_path: string | null;
  created_at: string;
}

export interface UserSettings {
  id: number;
  target_titles: string[];
  preferred_locations: string[];
  work_arrangement: string;
  minimum_salary: number | null;
  experience_level: string;
  required_skills: string[];
  excluded_companies: string[];
  default_scrape_frequency: string;
  concurrency: number;
  retry_limit: number;
  request_timeout: number;
  browser_automation: string;
  save_snapshots: boolean;
  resume_text: string | null;
}

export interface DashboardSummary {
  active_jobs: number;
  new_jobs_this_week: number;
  companies_monitored: number;
  applications_in_progress: number;
  review_queue_count: number;
  last_success_rate: number;
}

export interface ChartPoint {
  label: string;
  value: number;
}

export interface ActivityEvent {
  id: number;
  label: string;
  detail: string;
  level: "info" | "warning" | "error";
  created_at: string;
}

export interface DashboardData {
  summary: DashboardSummary;
  job_discovery: ChartPoint[];
  work_arrangement: ChartPoint[];
  top_matches: Job[];
  scraping_health: Company[];
  recent_activity: ActivityEvent[];
}

export interface IntegrationStatus {
  openrouter: "configured" | "not_configured";
  apify: "configured" | "not_configured";
  google_sheets: "configured" | "not_configured";
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}
