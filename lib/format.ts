import type { HealthStatus, ReviewStatus, ScrapeStatus } from "@/lib/types";

export function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatStatus(value: string) {
  return value.replace("_", " ");
}

export function statusClass(value: ScrapeStatus | HealthStatus | ReviewStatus | string) {
  if (["completed", "healthy", "approved", "active"].includes(value)) return "bg-emerald-50 text-emerald-700 ring-emerald-200";
  if (["failed", "error", "rejected"].includes(value)) return "bg-red-50 text-red-700 ring-red-200";
  if (["warning", "pending", "duplicate"].includes(value)) return "bg-amber-50 text-amber-700 ring-amber-200";
  if (["paused", "archived", "cancelled"].includes(value)) return "bg-slate-100 text-slate-700 ring-slate-200";
  return "bg-blue-50 text-blue-700 ring-blue-200";
}

export function formatMoney(value?: number | null, currency = "USD") {
  if (value == null) return "Not listed";
  return new Intl.NumberFormat("en", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
}

export function formatDate(value?: string | null) {
  if (!value) return "Unknown";
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}
