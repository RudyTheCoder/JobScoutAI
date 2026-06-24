"use client";

import { useEffect, useState } from "react";
import { Play, Plus, Trash2 } from "lucide-react";
import { createCompany, deleteCompany, getCompanies, runCompanyScrape, updateCompany } from "@/lib/api";
import type { Company } from "@/lib/types";
import { formatDateTime } from "@/lib/format";
import { sourceLabel } from "@/lib/source";
import { Button, DangerButton, ErrorPanel, LoadingPanel, Panel, PanelHeader, SecondaryButton, SelectInput, StatusBadge, TextInput } from "@/components/ui";

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [form, setForm] = useState({ name: "", website: "", career_url: "", extraction_method: "fixture", source_type: "fixture" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setCompanies(await getCompanies());
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message)).finally(() => setLoading(false));
  }, []);

  async function addCompany() {
    await createCompany({ ...form, monitoring_enabled: true, scrape_frequency: "daily" });
    setForm({ name: "", website: "", career_url: "", extraction_method: "fixture", source_type: "fixture" });
    await load();
  }

  if (loading) return <LoadingPanel label="Loading companies" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-normal">Companies</h1>
        <p className="mt-2 text-sm text-muted">Configure demo fixture sources or add a permitted public career page.</p>
      </div>
      {error ? <ErrorPanel message={error} /> : null}
      <Panel>
        <PanelHeader title="Add Company" subtitle="Real career pages must be public and permitted to scrape" />
        <div className="grid gap-3 p-5 md:grid-cols-3">
          <TextInput placeholder="Company name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
          <TextInput placeholder="Website URL" value={form.website} onChange={(event) => setForm({ ...form, website: event.target.value })} />
          <TextInput placeholder="Career URL" value={form.career_url} onChange={(event) => setForm({ ...form, career_url: event.target.value })} />
          <SelectInput value={form.extraction_method} onChange={(event) => setForm({ ...form, extraction_method: event.target.value })}>
            <option value="fixture">Fixture HTML</option>
            <option value="generic_html">Generic HTML</option>
            <option value="generic">Generic selectors</option>
            <option value="playwright">JavaScript rendered</option>
            <option value="greenhouse">Greenhouse API</option>
            <option value="lever">Lever API</option>
            <option value="ashby">Ashby API</option>
          </SelectInput>
          <SelectInput value={form.source_type} onChange={(event) => setForm({ ...form, source_type: event.target.value })}>
            <option value="fixture">Fixture</option>
            <option value="generic/html">Generic HTML</option>
            <option value="greenhouse">Greenhouse</option>
            <option value="lever">Lever</option>
            <option value="ashby">Ashby</option>
          </SelectInput>
          <Button onClick={addCompany} disabled={!form.name || !form.website || !form.career_url}><Plus className="h-4 w-4" />Add Company</Button>
        </div>
      </Panel>
      <div className="grid gap-4 lg:grid-cols-2">
        {companies.map((company) => (
          <Panel key={company.id} className="p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold">{company.name}</h2>
                <p className="mt-1 text-sm text-muted">{company.career_url}</p>
              </div>
              <StatusBadge status={company.monitoring_enabled ? company.health_status : "paused"} />
            </div>
            <dl className="mt-5 grid gap-3 border-t border-border pt-4 text-sm md:grid-cols-4">
              <div><dt className="text-muted">Source</dt><dd className="mt-1 font-medium">{sourceLabel(company.source_type)}</dd></div>
              <div><dt className="text-muted">Method</dt><dd className="mt-1 font-medium">{sourceLabel(company.extraction_method)}</dd></div>
              <div><dt className="text-muted">Frequency</dt><dd className="mt-1 font-medium">{company.scrape_frequency}</dd></div>
              <div><dt className="text-muted">Last scrape</dt><dd className="mt-1 font-medium">{company.last_scrape_at ? formatDateTime(company.last_scrape_at) : "Never"}</dd></div>
            </dl>
            <div className="mt-5 flex flex-wrap gap-2">
              <Button onClick={async () => { await runCompanyScrape(company.id); await load(); }}><Play className="h-4 w-4" />Run Now</Button>
              <SecondaryButton onClick={async () => { await updateCompany(company.id, { monitoring_enabled: !company.monitoring_enabled, health_status: company.monitoring_enabled ? "paused" : "healthy" }); await load(); }}>
                {company.monitoring_enabled ? "Pause" : "Resume"}
              </SecondaryButton>
              <DangerButton onClick={async () => { if (confirm(`Delete ${company.name}?`)) { await deleteCompany(company.id); await load(); } }}><Trash2 className="h-4 w-4" />Delete</DangerButton>
            </div>
          </Panel>
        ))}
      </div>
    </div>
  );
}
