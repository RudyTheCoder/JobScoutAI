import type {
  Application,
  ApplicationStage,
  Company,
  DashboardData,
  ExportFormat,
  ExportRecord,
  IntegrationStatus,
  Job,
  JobListResponse,
  ReviewRecord,
  SavedJob,
  ScrapeLog,
  ScrapeRun,
  UserSettings,
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type JsonRecord = Record<string, unknown>;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function query(params: Record<string, string | number | boolean | undefined | null>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  });
  const value = search.toString();
  return value ? `?${value}` : "";
}

export const apiBaseUrl = API_BASE_URL;

export function getDashboard() {
  return request<DashboardData>("/api/dashboard");
}

export function getJobs(filters: JsonRecord = {}) {
  return request<JobListResponse>(`/api/jobs${query(filters as Record<string, string | number | boolean>)}`);
}

export function getJob(id: string | number) {
  return request<Job>(`/api/jobs/${id}`);
}

export function saveJob(id: number) {
  return request<SavedJob>(`/api/jobs/${id}/save`, { method: "POST" });
}

export function unsaveJob(id: number) {
  return request<void>(`/api/jobs/${id}/save`, { method: "DELETE" });
}

export function archiveJob(id: number) {
  return request<Job>(`/api/jobs/${id}/archive`, { method: "POST" });
}

export function markApplied(id: number) {
  return request<Application>(`/api/jobs/${id}/apply`, { method: "POST" });
}

export function getCompanies() {
  return request<Company[]>("/api/companies");
}

export function createCompany(payload: Partial<Company>) {
  return request<Company>("/api/companies", { method: "POST", body: JSON.stringify(payload) });
}

export function updateCompany(id: number, payload: Partial<Company>) {
  return request<Company>(`/api/companies/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function deleteCompany(id: number) {
  return request<void>(`/api/companies/${id}`, { method: "DELETE" });
}

export function runCompanyScrape(id: number) {
  return request<ScrapeRun>(`/api/companies/${id}/scrape`, { method: "POST" });
}

export function getScrapeRuns() {
  return request<ScrapeRun[]>("/api/scraping/runs");
}

export function getScrapeLogs(id: number) {
  return request<ScrapeLog[]>(`/api/scraping/runs/${id}/logs`);
}

export function startScrape(companyId?: number) {
  return request<ScrapeRun>("/api/scraping/runs", { method: "POST", body: JSON.stringify({ company_id: companyId }) });
}

export function retryScrape(id: number) {
  return request<ScrapeRun>(`/api/scraping/runs/${id}/retry`, { method: "POST" });
}

export function cancelScrape(id: number) {
  return request<ScrapeRun>(`/api/scraping/runs/${id}/cancel`, { method: "POST" });
}

export function getReviews() {
  return request<ReviewRecord[]>("/api/review");
}

export function approveReview(id: number, extractedData?: JsonRecord) {
  return request<ReviewRecord>(`/api/review/${id}/approve`, { method: "POST", body: JSON.stringify({ extracted_data: extractedData }) });
}

export function rejectReview(id: number, notes?: string) {
  return request<ReviewRecord>(`/api/review/${id}/reject`, { method: "POST", body: JSON.stringify({ reviewer_notes: notes }) });
}

export function duplicateReview(id: number, notes?: string) {
  return request<ReviewRecord>(`/api/review/${id}/duplicate`, { method: "POST", body: JSON.stringify({ reviewer_notes: notes }) });
}

export function getSavedJobs() {
  return request<SavedJob[]>("/api/saved-jobs");
}

export function getApplications() {
  return request<Application[]>("/api/applications");
}

export function updateApplication(id: number, payload: { stage?: ApplicationStage; notes?: string; next_action?: string }) {
  return request<Application>(`/api/applications/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function deleteApplication(id: number) {
  return request<void>(`/api/applications/${id}`, { method: "DELETE" });
}

export function getExports() {
  return request<ExportRecord[]>("/api/exports");
}

export function createExport(payload: { dataset: string; format: ExportFormat; fields?: string[] }) {
  return request<ExportRecord>("/api/exports", { method: "POST", body: JSON.stringify(payload) });
}

export function getSettings() {
  return request<UserSettings>("/api/settings");
}

export function updateSettings(payload: Partial<UserSettings>) {
  return request<UserSettings>("/api/settings", { method: "PATCH", body: JSON.stringify(payload) });
}

export function getIntegrations() {
  return request<IntegrationStatus>("/api/settings/integrations");
}
