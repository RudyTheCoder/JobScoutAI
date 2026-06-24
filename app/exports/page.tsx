"use client";

import { useEffect, useState } from "react";
import { Download, FilePlus } from "lucide-react";
import { apiBaseUrl, createExport, getExports } from "@/lib/api";
import type { ExportFormat, ExportRecord } from "@/lib/types";
import { formatDateTime } from "@/lib/format";
import { Button, EmptyState, ErrorPanel, LoadingPanel, Panel, PanelHeader, SelectInput, StatusBadge, TextInput } from "@/components/ui";

const defaultExportFields = "company_name,title,location,work_arrangement,employment_type,salary_text,salary_min,salary_max,currency,match_score,source_type,source_url,application_url,first_seen_at,last_seen_at";

export default function ExportsPage() {
  const [exports, setExports] = useState<ExportRecord[]>([]);
  const [format, setFormat] = useState<ExportFormat>("csv");
  const [fields, setFields] = useState(defaultExportFields);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setExports(await getExports());
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message)).finally(() => setLoading(false));
  }, []);

  async function generate() {
    await createExport({ dataset: "jobs", format, fields: fields.split(",").map((field) => field.trim()).filter(Boolean) });
    await load();
  }

  if (loading) return <LoadingPanel label="Loading exports" />;

  return (
    <div className="space-y-6">
      <div><h1 className="text-3xl font-semibold tracking-normal">Data Exports</h1><p className="mt-2 text-sm text-muted">Generate downloadable CSV, JSON, or Excel datasets from stored records.</p></div>
      {error ? <ErrorPanel message={error} /> : null}
      <Panel>
        <PanelHeader title="Create Export" subtitle="Google Sheets remains disabled unless credentials are configured" />
        <div className="grid gap-3 p-5 md:grid-cols-[180px_1fr_180px]">
          <SelectInput value={format} onChange={(event) => setFormat(event.target.value as ExportFormat)}>
            <option value="csv">CSV</option>
            <option value="json">JSON</option>
            <option value="xlsx">Excel</option>
          </SelectInput>
          <TextInput value={fields} onChange={(event) => setFields(event.target.value)} />
          <Button onClick={generate}><FilePlus className="h-4 w-4" />Generate</Button>
        </div>
      </Panel>
      <Panel>
        <PanelHeader title="Previous Exports" subtitle={`${exports.length} records`} />
        {exports.length === 0 ? <EmptyState title="No exports yet" detail="Generate one above to download a real file." /> : (
          <div className="table-scroll overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-surface text-xs uppercase text-muted"><tr><th className="px-5 py-3">Name</th><th className="px-5 py-3">Format</th><th className="px-5 py-3">Records</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Created</th><th className="px-5 py-3">Download</th></tr></thead>
              <tbody className="divide-y divide-border">
                {exports.map((item) => (
                  <tr key={item.id}><td className="px-5 py-4 font-medium">{item.name}</td><td className="px-5 py-4">{item.format}</td><td className="px-5 py-4">{item.record_count}</td><td className="px-5 py-4"><StatusBadge status={item.status} /></td><td className="px-5 py-4 text-muted">{formatDateTime(item.created_at)}</td><td className="px-5 py-4">{item.status === "completed" && item.file_path ? <a className="inline-flex items-center gap-2 text-accent hover:underline" href={`${apiBaseUrl}/api/exports/${item.id}/download`}><Download className="h-4 w-4" />Download</a> : "Unavailable"}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
