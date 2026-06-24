"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, BriefcaseBusiness, Building2, Clock, TrendingUp } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getDashboard } from "@/lib/api";
import type { DashboardData } from "@/lib/types";
import { formatDateTime } from "@/lib/format";
import { ErrorPanel, LoadingPanel, Panel, PanelHeader, StatusBadge } from "@/components/ui";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const cards = useMemo(() => {
    if (!data) return [];
    return [
      { label: "Active Jobs", value: data.summary.active_jobs, detail: "Normalized listings", icon: BriefcaseBusiness },
      { label: "New This Week", value: data.summary.new_jobs_this_week, detail: "First seen recently", icon: TrendingUp },
      { label: "Companies", value: data.summary.companies_monitored, detail: "Monitoring enabled", icon: Building2 },
      { label: "Applications", value: data.summary.applications_in_progress, detail: "In progress", icon: Clock },
    ];
  }, [data]);

  if (loading) return <LoadingPanel label="Loading overview" />;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-brand">Job-market intelligence</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-normal">Overview</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted">
          Monitor career pages, normalize public listings, route uncertain records to review, and track applications from one simple workspace.
        </p>
      </div>

      {error ? <ErrorPanel message={error} /> : null}

      {data ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {cards.map((card) => (
              <Panel key={card.label} className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm text-muted">{card.label}</p>
                    <p className="mt-2 text-2xl font-semibold">{card.value.toLocaleString()}</p>
                    <p className="mt-2 text-xs text-muted">{card.detail}</p>
                  </div>
                  <span className="grid h-10 w-10 place-items-center rounded-md bg-surface text-ink">
                    <card.icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                </div>
              </Panel>
            ))}
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
            <Panel>
              <PanelHeader title="Job Discovery" subtitle="Listings first seen by day" />
              <div className="h-80 p-4">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.job_discovery}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
                    <Tooltip />
                    <Line type="monotone" dataKey="value" stroke="#0f766e" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Panel>

            <Panel>
              <PanelHeader title="Work Arrangement" subtitle="Current active jobs" />
              <div className="h-80 p-4">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.work_arrangement}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#2563eb" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          </div>

          <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
            <Panel>
              <PanelHeader title="Top Matches" subtitle="Deterministic preference score, not hiring probability" />
              <div className="divide-y divide-border">
                {data.top_matches.map((job) => (
                  <Link key={job.id} href={`/jobs/${job.id}`} className="block px-5 py-4 hover:bg-surface/70">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="font-medium">{job.title}</p>
                        <p className="mt-1 text-sm text-muted">{job.company_name} · {job.location ?? "Unknown location"}</p>
                      </div>
                      <span className="text-sm font-semibold text-brand">{job.match_score}%</span>
                    </div>
                  </Link>
                ))}
              </div>
            </Panel>

            <Panel>
              <PanelHeader title="Scraping Health" subtitle={`${data.summary.review_queue_count} pending review records`} />
              <div className="divide-y divide-border">
                {data.scraping_health.map((company) => (
                  <div key={company.id} className="flex items-center justify-between gap-4 px-5 py-4">
                    <div>
                      <p className="font-medium">{company.name}</p>
                      <p className="mt-1 text-sm text-muted">
                        Last scrape {company.last_scrape_at ? formatDateTime(company.last_scrape_at) : "not yet run"}
                      </p>
                    </div>
                    <StatusBadge status={company.health_status} />
                  </div>
                ))}
              </div>
            </Panel>
          </div>

          <Panel>
            <PanelHeader title="Recent Activity" subtitle="Scraping, review, export, and application events" />
            <div className="divide-y divide-border">
              {data.recent_activity.map((event) => (
                <div key={event.id} className="flex gap-4 px-5 py-4">
                  <span className="mt-1 grid h-8 w-8 place-items-center rounded-md bg-surface">
                    {event.level === "warning" ? <AlertTriangle className="h-4 w-4 text-warning" /> : <Activity className="h-4 w-4 text-brand" />}
                  </span>
                  <div>
                    <p className="text-sm font-semibold">{event.label}</p>
                    <p className="mt-1 text-sm text-muted">{event.detail} · {formatDateTime(event.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </>
      ) : null}
    </div>
  );
}
