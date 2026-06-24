"use client";

import { useEffect, useState } from "react";
import { Download, Play, RefreshCcw, Square } from "lucide-react";
import { apiBaseUrl, cancelScrape, getCompanies, getScrapeLogs, getScrapeRuns, retryScrape, startScrape } from "@/lib/api";
import type { Company, ScrapeLog, ScrapeRun } from "@/lib/types";
import { formatDateTime } from "@/lib/format";
import { sourceLabel } from "@/lib/source";
import { Button, EmptyState, ErrorPanel, LoadingPanel, Panel, PanelHeader, SecondaryButton, SelectInput, StatusBadge } from "@/components/ui";

export default function ScrapingPage() {
  const [runs, setRuns] = useState<ScrapeRun[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState("");
  const [selectedRun, setSelectedRun] = useState<ScrapeRun | null>(null);
  const [logs, setLogs] = useState<ScrapeLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [runData, companyData] = await Promise.all([getScrapeRuns(), getCompanies()]);
    setRuns(runData);
    setCompanies(companyData);
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message)).finally(() => setLoading(false));
  }, []);

  async function openLogs(run: ScrapeRun) {
    setSelectedRun(run);
    setLogs(await getScrapeLogs(run.id));
  }

  if (loading) return <LoadingPanel label="Loading scrape runs" />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div><h1 className="text-3xl font-semibold tracking-normal">Scraping Jobs</h1><p className="mt-2 text-sm text-muted">Run and inspect extraction jobs without crowding overview screens.</p></div>
        <div className="flex gap-2">
          <SelectInput value={selectedCompany} onChange={(event) => setSelectedCompany(event.target.value)}>
            <option value="">First monitored company</option>
            {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
          </SelectInput>
          <Button onClick={async () => { await startScrape(selectedCompany ? Number(selectedCompany) : undefined); await load(); }}><Play className="h-4 w-4" />Run Scrape</Button>
        </div>
      </div>
      {error ? <ErrorPanel message={error} /> : null}
      <Panel>
        <PanelHeader title="Runs" subtitle="Technical logs are shown only after selecting a run" />
        {runs.length === 0 ? <EmptyState title="No scrape runs" detail="Start a scrape from this page or a company card." /> : (
          <div className="table-scroll overflow-x-auto">
            <table className="w-full min-w-[940px] text-left text-sm">
              <thead className="bg-surface text-xs uppercase text-muted"><tr><th className="px-5 py-3">Company</th><th className="px-5 py-3">Method</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Records</th><th className="px-5 py-3">Review</th><th className="px-5 py-3">Failed</th><th className="px-5 py-3">Success</th><th className="px-5 py-3">Started</th><th className="px-5 py-3">Actions</th></tr></thead>
              <tbody className="divide-y divide-border">
                {runs.map((run) => (
                  <tr key={run.id} className="hover:bg-surface/70">
                    <td className="px-5 py-4">{run.company_name ?? "All"}</td>
                    <td className="px-5 py-4">{sourceLabel(run.extraction_method)}</td>
                    <td className="px-5 py-4"><StatusBadge status={run.status} /></td>
                    <td className="px-5 py-4">{run.valid_records}/{run.records_extracted}</td>
                    <td className="px-5 py-4">{run.review_records}</td>
                    <td className="px-5 py-4">{run.failed_pages}</td>
                    <td className="px-5 py-4">{run.success_rate}%</td>
                    <td className="px-5 py-4 text-muted">{run.started_at ? formatDateTime(run.started_at) : "Queued"}</td>
                    <td className="px-5 py-4"><div className="flex gap-2"><SecondaryButton className="min-h-9 px-3" onClick={() => openLogs(run)}>Details</SecondaryButton><SecondaryButton className="min-h-9 px-3" onClick={async () => { await retryScrape(run.id); await load(); }}><RefreshCcw className="h-4 w-4" />Retry</SecondaryButton><SecondaryButton className="min-h-9 px-3" onClick={async () => { await cancelScrape(run.id); await load(); }}><Square className="h-4 w-4" />Stop</SecondaryButton><a className="inline-flex min-h-9 items-center gap-2 rounded-md border border-border px-3 py-2 font-semibold hover:bg-surface" href={`${apiBaseUrl}/api/scraping/runs/${run.id}/download`}><Download className="h-4 w-4" />CSV</a></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      {selectedRun ? (
        <Panel>
          <PanelHeader title={`Run #${selectedRun.id} Logs`} subtitle={`${sourceLabel(selectedRun.extraction_method)} · ${selectedRun.pages_processed}/${selectedRun.pages_discovered} pages processed · ${selectedRun.records_extracted} extracted · ${selectedRun.valid_records} valid · ${selectedRun.review_records} review · ${selectedRun.invalid_records} invalid · ${selectedRun.failed_pages} failed`} />
          <div className="divide-y divide-border">
            {logs.map((log) => <div key={log.id} className="px-5 py-4 text-sm"><span className="font-semibold">{log.level}</span>{log.http_status ? <span className="text-muted"> · HTTP {log.http_status}</span> : null}<span className="text-muted"> · {log.message}</span>{log.error_category ? <span className="text-muted"> · {log.error_category}</span> : null}{log.url ? <a className="ml-1 text-accent hover:underline" href={log.url} target="_blank" rel="noreferrer">{log.url}</a> : null}</div>)}
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
